# Wi-Fi A-MPDU delay history study

Compares a four-delay controller with the symmetric linear rule from [Finding the Sweet Spot for Frame Aggregation in 802.11 WLANs](https://doi.org/10.1109/LCOMM.2020.3044231). The scenario uses the [authors’ released launcher settings](https://github.com/wifi-sweet-spot/ns3) on ns-3.48. The paper used ns-3.30.1, Random Waypoint at 1.5 m/s with 2 s pauses, and voice priority.

## Build

Run on Linux. On Windows use WSL 2 or a Linux VM. On macOS or other hosts use a Linux VM for this workflow. The batch runner depends on Unix file locking.

Install [ns-3.48 source](https://www.nsnam.org/releases/), Python 3.10+, CMake 3.25+, GCC 11.1+ or Clang 17+, and Make or Ninja. On Ubuntu 24.04, the build tools are available as `g++ cmake make python3`. Use Git to clone or an archive extractor to unpack the source.

Replace these paths with the locations of the experiment checkout and ns-3.48 source. Keep builds and results on the Linux filesystem under WSL.

```bash
REPO="$HOME/src/wifi-sweet-spot-ns3"
NS3="$HOME/src/ns-3.48"
cd "$NS3"
ln -sT "$REPO" scratch/wifi-sweet-spot  # once per ns-3 tree
./ns3 configure --build-profile=optimized
./ns3 build wifi-central-controlled-aggregation_v199 -j 4
```

## Run

Use the Linux environment where you built the simulator. This can be a Linux
host, a Linux VM, or WSL 2. From any directory, replace the three example paths
with paths visible in that environment:

```bash
REPO="/path/to/wifi-sweet-spot-ns3"
NS3="/path/to/ns-3.48"
OUT="/path/to/results/wifi-delay-pair-60s"
python3 "$REPO/run_delay_study.py" --ns3 "$NS3" --output "$OUT" \
  --policies linear four-delay --runs 1-5 --seconds 60 --workers 2

# Check progress from another terminal using the same REPO and OUT paths.
python3 "$REPO/run_delay_study.py" --output "$OUT" --status
```

Use `--runs 2` first to time one pair. Repeat the same command to resume. Use a fresh output directory when changing the duration or build. For the full comparison, use `--runs 1-10 --seconds 180` (20 simulations). Omit `--policies` for all five policies (50 simulations). Use `--binary` to select a different ns-3 executable.

A WSL debug benchmark with two workers gives rough estimates of **1 hour** for the short pair study, **6 hours** for the full pair study, or **18 hours** for all five policies at 180 s. Time a pilot on your build for a local estimate.

## Experiment parameters

| Setting | Value |
|---|---|
| Topology | One AP centred in a 50 × 50 m area, one TCP client and one voice client. Servers behind a router. CSMA at 100 Gbit/s and 6.56 µs; point-to-point at 10 Gbit/s and 1 ms; ARP alive timeout 1 s. |
| Mobility | Uniform initial positions. 2D Random Walk at 1 m/s with 5 s direction intervals and reflective boundaries. RNG seed 1, paired by `RngRun`. |
| Radio | 802.11ac, 5 GHz channel 36, 20 MHz, −3 dBm, short guard interval off. SpectrumWifiPhy, MultiModelSpectrumChannel, Friis Spectrum, NIST error model, Ideal rate control. RTS/CTS threshold 0 B, explicit voice priority off. |
| Workload | Unlimited TCP NewReno download, 1,448 B segment payload, 1,500 B MTU. UDP voice upload, 32 B payload (60 B IPv4 packet) every 20 ms. |
| Timing | Receivers start at 0 s, senders at 1 s. Simulation ends at 1 s plus the configured traffic duration (180 s by default). |
| Control | Mean voice delay every 250 ms, starting at 1.25 s. Budget 4 ms. Dynamic cap starts at 65,535 B and is bounded to 1,600–65,535 B. Updates apply to the AP and associated TCP station. Voice station aggregation is disabled. |

| Policy | Cap rule |
|---|---|
| `linear` | Matched baseline (method 5). Uses the latest delay to decide whether to change the cap. |
| `four-delay` | History controller (method 6). Uses the last four delay measurements to decide whether to allow an increase. |
| `off` | AP cap 0 B. |
| `max` | Fixed cap 65,535 B. |
| `geometric` | Released Figure 2c launcher. Double below budget, multiply by 0.618 otherwise. |

## Four-delay controller protocol

1. **Measure.** Every 250 ms, FlowMonitor computes the mean one-way delay of voice packets received in the completed interval. With several voice flows on an AP, the controller takes the highest available flow mean. The experiment has one voice flow.
2. **Update history.** Each AP retains its four most recent consecutive valid delay measurements. If no voice delay is available, hold the cap and clear that AP's history. Keep the current cap as the base for the next step.
3. **Decide.** A latest delay above 4 ms triggers an immediate 3,000 B decrease. Hold at exactly 4 ms. Below 4 ms, hold until four consecutive samples are available. Once the window is full, calculate the warning score:

   ```text
   d0, d1, d2, d3 = four delay measurements, oldest first, in ms
   slope = (-3*d0 - d1 + d2 + 3*d3) / 10   # fitted change per 250 ms
   score = d3 + max(0, slope)
   ```

   Hold if the score is at least 4 ms. Otherwise, increase by 3,000 B. For example, delays of 2.0, 2.5, 3.0, and 3.5 ms give a slope of +0.5 ms per interval and a score of 4.0 ms, so the controller holds.

4. **Apply.** Clamp the new cap to 1,600–65,535 B and apply it to the AP and associated TCP station when it changes. The next interval measures the response. The cap sets an upper limit on a transmission’s aggregate size. Packet availability and link constraints determine the size actually sent.

`linear` shares the same startup, missing-data, and step rules. After startup it increases whenever the latest delay is below budget. This isolates the effect of the trend check. The warning score uses delay history alone, and the 4 ms control threshold applies to interval means. The experiment evaluates individual packet deadline misses separately.

## Results

- `progress.json`: completed and active jobs, failures, and estimated time remaining.
- `results.csv`: one row per trial with TCP throughput (received IP bytes), voice delay, jitter, loss, deadline misses, and actual AP aggregate size and airtime. Late and undelivered voice packets count as 4 ms deadline misses.
- `paired.csv`: four-delay minus linear throughput and deadline-miss percentage points for each matching mobility trace.
- `experiment.json` and run directories: build hash, settings, raw simulator, mobility and KPI logs, and decisions for the matched policies.

For plots, install `pandas` and `matplotlib` in your Python environment, then run:

```bash
python3 "$REPO/plot_fig2.py" --study-dir "$OUT" --run 2
```
