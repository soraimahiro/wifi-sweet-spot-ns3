#!/usr/bin/env python3
"""Run single-AP aggregation policies with paired mobility runs on Linux."""

import argparse
from concurrent.futures import ThreadPoolExecutor, FIRST_COMPLETED, wait
import csv
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time


TARGET = "wifi-central-controlled-aggregation_v199"
COMMON = dict(
    numberVoIPupload=1, numberVoIPdownload=0, numberTCPupload=0,
    numberTCPdownload=1, numberVideoDownload=0, TcpVariant="TcpNewReno",
    TcpPayloadSize=1448, nodeMobility=2, constantSpeed=1,
    number_of_APs=1, number_of_APs_per_row=1, distance_between_APs=50,
    distanceToBorder=25, arpAliveTimeout=1.0, rateModel="Ideal",
    numChannels=16, version80211=1, channelWidth=20, wifiModel=1,
    errorRateModel=0, propagationLossModel=2, topology=2, powerLevel=-3,
    prioritiesEnabled=0, RtsCtsThreshold=0, maxAmpduSize=65535,
    timeMonitorKPIs=0.25, latencyBudget=0.004, stepAdjustAmpdu=3000,
    aggregationDisableAlgorithm=0, studyMetrics=1, writeMobility=1,
    enablePcap=0, generateHistograms=0, verboseLevel=0, printSeconds=10,
    outputFileName="study", outputFileSurname="run",
)
POLICIES = {"off": None, "max": None, "geometric": 3, "linear": 5, "four-delay": 6}


def run_numbers(value):
    try:
        result = set()
        for item in value.split(","):
            first, _, last = item.partition("-")
            result.update(range(int(first), int(last or first) + 1))
        if not result or min(result) < 1:
            raise ValueError
        return sorted(result)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Use positive run numbers, e.g. 2 or 1-10") from error


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n")
    temporary.replace(path)


def completed_run(path):
    return (path / "result.json").is_file()


def run_one(binary, output, policy, rng_run, duration):
    method = POLICIES[policy]
    options = dict(COMMON, simulationTime=duration,
                   rateAPsWithAMPDUenabled=int(policy != "off"),
                   aggregationDynamicAlgorithm=int(method is not None))
    if method is not None:
        options["methodAdjustAmpdu"] = method
    command = [str(binary), *(f"--{key}={value}" for key, value in options.items())]
    env = dict(os.environ, NS_GLOBAL_VALUE=f"RngRun={rng_run};RngSeed=1")
    name = f"run-{rng_run:03d}-{policy}"
    attempt = Path(tempfile.mkdtemp(prefix=f".{name}-", dir=output))
    started = time.monotonic()
    with (attempt / "simulator.log").open("w") as log:
        status = subprocess.run(command, cwd=attempt, env=env, stdout=log,
                                stderr=subprocess.STDOUT).returncode
    if status != 0:
        raise RuntimeError(f"{name} exited with {status}: {attempt / 'simulator.log'}")
    with (attempt / "study_run_study.csv").open(newline="") as data:
        metrics, = csv.DictReader(data)
    sent, received, on_time = (int(metrics[key]) for key in
                               ("voice_sent", "voice_received", "voice_on_time"))
    if not (0 <= on_time <= received <= sent and sent > 0):
        raise RuntimeError(f"Invalid packet counts: {attempt}")
    if not int(metrics["ap_data_ppdus"]) or (policy == "off" and int(metrics["ap_aggregates"])):
        raise RuntimeError(f"Unexpected AP transmission counts: {attempt}")
    if method in (5, 6):
        with (attempt / "study_run_decisions.csv").open(newline="") as data:
            decisions = list(csv.DictReader(data))
        if not decisions or all(row["reason"] == "missing" for row in decisions):
            raise RuntimeError(f"No usable controller observations: {attempt}")
        metrics["trend_holds"] = sum(row["reason"] == "trend_hold" for row in decisions)
    else:
        metrics["trend_holds"] = ""
    result = dict(policy=policy, rng_run=rng_run, wall_seconds=round(time.monotonic() - started, 2),
                  **metrics, voice_loss_pct=100 * (sent - received) / sent,
                  voice_deadline_miss_pct=100 * (sent - on_time) / sent,
                  mobility_sha256=digest(attempt / "study_run-mobility.txt"))
    write_json(attempt / "result.json", result)
    attempt.rename(output / name)
    return result


def report(output):
    rows = [json.loads(path.read_text()) for path in sorted(output.glob("run-*/result.json"))]
    if not rows:
        return
    with (output / "results.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    by_run = {(row["rng_run"], row["policy"]): row for row in rows}
    mismatches = []
    with (output / "paired.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("rng_run", "four_delay_minus_linear_tcp_mbps",
                         "four_delay_minus_linear_miss_percentage_points"))
        for rng_run in sorted({row["rng_run"] for row in rows}):
            mobility = {row["mobility_sha256"] for row in rows if row["rng_run"] == rng_run}
            if len(mobility) > 1:
                mismatches.append(f"RngRun {rng_run}: policies produced different mobility traces")
                continue
            if all((rng_run, policy) in by_run for policy in ("linear", "four-delay")):
                linear, history = (by_run[rng_run, policy] for policy in ("linear", "four-delay"))
                writer.writerow((rng_run, float(history["tcp_mbps"]) - float(linear["tcp_mbps"]),
                                 history["voice_deadline_miss_pct"] - linear["voice_deadline_miss_pct"]))
    return mismatches


def run_study(args, output):
    binary = args.binary or (
        args.ns3 / "build" / "scratch" / "wifi-sweet-spot" / "cc" /
        f"ns3.48-{TARGET}-optimized")
    binary = binary.resolve()
    if not os.access(binary, os.X_OK):
        raise SystemExit(f"Build the optimized target first or pass --binary. Missing: {binary}")
    config = dict(binary_sha256=digest(binary), simulator="ns-3.48", rng_seed=1,
                  common=COMMON, duration=args.seconds, policies=POLICIES)
    manifest = output / "experiment.json"
    if manifest.exists() and json.loads(manifest.read_text()) != config:
        raise SystemExit("This output directory belongs to a different build or configuration.")
    write_json(manifest, config)
    jobs = [(policy, rng_run) for rng_run in args.runs for policy in args.policies]
    pending = [(p, r) for p, r in jobs if not completed_run(output / f"run-{r:03d}-{p}")]
    done = len(jobs) - len(pending)
    failures = []
    started = time.monotonic()
    durations = []
    recent_message = ""
    print(f"{done}/{len(jobs)} complete, {len(pending)} pending, {args.workers} worker(s)", flush=True)
    with ThreadPoolExecutor(max_workers=args.workers) as workers:
        queued = iter(pending)
        futures = {}

        def start_next():
            job = next(queued, None)
            if job is not None:
                policy, rng_run = job
                futures[workers.submit(run_one, binary, output, policy, rng_run, args.seconds)] = job

        for _ in range(args.workers):
            start_next()
        while futures:
            finished, _ = wait(futures, timeout=5, return_when=FIRST_COMPLETED)
            for job in finished:
                policy, rng_run = futures.pop(job)
                try:
                    result = job.result()
                    durations.append(result["wall_seconds"])
                    done += 1
                    recent_message = (f"{done}/{len(jobs)} complete: run {rng_run} "
                                      f"{policy} ({result['wall_seconds']:.1f} s)")
                    print(recent_message, flush=True)
                except Exception as error:
                    recent_message = str(error)
                    failures.append(recent_message)
                    print(recent_message, flush=True)
                start_next()
            eta = (sum(durations) / len(durations) * (len(jobs) - done - len(failures)) / args.workers
                   if durations else None)
            active = [f"run {r} {p}" for future, (p, r) in futures.items() if future.running()]
            write_json(output / "progress.json", dict(
                state="running", completed=done, total=len(jobs), failures=failures,
                active=active, last=recent_message, remaining_seconds=eta,
                elapsed_seconds=round(time.monotonic() - started, 1)))
    for failure in report(output) or ():
        failures.append(failure)
        print(failure, flush=True)
    write_json(output / "progress.json", dict(
        state="failed" if failures else "complete", completed=done, total=len(jobs),
        failures=failures, active=[], remaining_seconds=0 if not failures else None,
        elapsed_seconds=round(time.monotonic() - started, 1)))
    return bool(failures)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ns3", type=Path, default=Path.cwd(), help="ns-3.48 root")
    parser.add_argument("--binary", type=Path, help="Override the optimized simulator executable")
    parser.add_argument("--output", type=Path, required=True, help="Results directory")
    parser.add_argument("--runs", type=run_numbers, default=run_numbers("1-10"))
    parser.add_argument("--policies", nargs="+", choices=tuple(POLICIES),
                        default=tuple(POLICIES), help="Policies to run (default: all five)")
    parser.add_argument("--seconds", type=int, default=180)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--status", action="store_true", help="Show progress without starting a batch")
    args = parser.parse_args()
    args.policies = tuple(dict.fromkeys(args.policies))
    output = args.output.resolve()
    if args.status:
        progress = output / "progress.json"
        print(progress.read_text() if progress.exists() else "No progress recorded.", end="\n")
        for log in sorted(output.glob(".run-*/simulator.log")):
            with log.open() as handle:
                last_tick = next((line.strip() for line in reversed(handle.readlines())
                                  if line.strip()), "")
            if last_tick:
                print(f"{log.parent.name}: {last_tick}")
        return 0
    if args.seconds < 2 or args.workers < 1:
        parser.error("--seconds must be at least 2 and --workers at least 1")
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("A batch is already using this output directory.")
        return run_study(args, output)


if __name__ == "__main__":
    raise SystemExit(main())
