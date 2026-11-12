#!/usr/bin/env python3
"""Plot Fig. 2 of the paper (TCP throughput and UDP delay vs. time) from the
outputs of fig2.sh, in the same style as the original figure.

Reads (from the ns-3 root directory):
  fig2{a,b,c}_seed-2_KPIs.txt        per-interval KPIs of every flow
  fig2c_seed-2_AMPDUvalues.txt       A-MPDU size set by the dynamic algorithm
Writes:
  scratch/wifi-sweet-spot/fig2.png         panels (a), (b), (c) as in the paper
  scratch/wifi-sweet-spot/fig2c_ampdu.png  A-MPDU size of the AP in (c) (not in the paper)

Run from the ns-3 root:
  scratch/lab/.venv/bin/python scratch/wifi-sweet-spot/plot_fig2.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

# Same scales as the original figure
X_MAX_S = 120          # the paper shows the first 120 s (the runs last 180 s)
TCP_YMAX_MBPS = 70
DELAY_YMAX_S = 0.2     # larger delays are marked on the top edge

TCP_COLOR = "#ED7D31"  # orange, as in the paper
UDP_COLOR = "#5B9BD5"  # blue, as in the paper

OUT_DIR = Path("scratch/wifi-sweet-spot")
RUNS = ["fig2a", "fig2b", "fig2c"]


def read_kpis(name):
    df = pd.read_csv(f"{name}_seed-2_KPIs.txt", sep="\t")
    df.columns = ["t", "flow", "app", "port", "delay", "jitter", "rx", "lost", "thr"]
    df["delay"] = pd.to_numeric(df["delay"], errors="coerce")  # 'nan' when no packets
    df["thr"] = pd.to_numeric(df["thr"], errors="coerce")
    return df


def plot_panel(ax, df, label):
    voip = df[df["app"] == "VoIP_upload"]
    tcp = df[df["app"] == "TCP_download"].groupby("t")["thr"].sum() / 1e6

    ax.plot(tcp.index, tcp.values, color=TCP_COLOR, lw=1.2, label="Throughput TCP")
    ax.set_xlim(0, X_MAX_S)
    ax.set_ylim(0, TCP_YMAX_MBPS)
    ax.set_ylabel("Throughput [Mbps]", fontweight="bold")
    ax.set_xlabel("Simulation time [s]", fontweight="bold")
    ax.set_title("Throughput TCP and Delay UDP", fontweight="bold", fontsize=11)
    ax.grid(color="#D9D9D9", lw=0.6)
    ax.set_axisbelow(True)

    ax2 = ax.twinx()
    for i, (_, flow) in enumerate(voip.groupby("flow")):
        ax2.plot(flow["t"], flow["delay"].clip(upper=DELAY_YMAX_S), color=UDP_COLOR, lw=1.0,
                 label="delay UDP" if i == 0 else None)
        # delays above the common scale: mark them on the top edge
        over = flow[(flow["delay"] > DELAY_YMAX_S) & (flow["t"] <= X_MAX_S)]
        if not over.empty:
            ax2.plot(over["t"], [DELAY_YMAX_S] * len(over), "^", color=UDP_COLOR, ms=5, clip_on=False)
            ax2.text(0.02, 0.97,
                     f"{len(over)} delay value(s) > {DELAY_YMAX_S} s "
                     f"(max {over['delay'].max():.2f} s)",
                     transform=ax2.transAxes, ha="left", va="top", fontsize=8, color=UDP_COLOR,
                     bbox=dict(facecolor="white", edgecolor="none", alpha=0.9))
    ax2.set_ylim(0, DELAY_YMAX_S)
    ax2.set_ylabel("Delay [s]", fontweight="bold")
    ax2.yaxis.set_major_locator(mticker.MultipleLocator(0.02))

    # One legend for both axes, upper right as in the paper
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax2.legend(h1 + h2, l1 + l2, loc="upper right", fontsize=8, frameon=False)

    # Panel label below the axes: (a), (b), (c)
    ax.text(0.5, -0.3, label, transform=ax.transAxes, ha="center", va="top", fontsize=11)

    shown_voip = voip[voip["t"] <= X_MAX_S]
    print(f"{label} first {X_MAX_S} s: mean TCP {tcp[tcp.index <= X_MAX_S].mean():.1f} Mbps, "
          f"mean UDP delay {shown_voip['delay'].mean() * 1e3:.2f} ms, "
          f"max UDP delay {shown_voip['delay'].max() * 1e3:.1f} ms")


def plot_ampdu():
    path = Path("fig2c_seed-2_AMPDUvalues.txt")
    if not path.exists():
        return
    df = pd.read_csv(path, sep="\t")
    df.columns = ["t", "id", "type", "ap", "ampdu"]
    df = df[df["type"].str.strip() == "AP"]
    fig, ax = plt.subplots(figsize=(6, 2.6))
    for ap_id, ap in df.groupby("id"):
        ax.step(ap["t"], ap["ampdu"], where="post", lw=0.8, label=f"AP #{ap_id}")
    ax.set_xlim(0, X_MAX_S)
    ax.set_ylim(bottom=0)
    ax.set_xlabel("Simulation time [s]")
    ax.set_ylabel("A-MPDU [bytes]")
    ax.set_title("(c) A-MPDU size of the AP", fontsize=10)
    ax.grid(color="#D9D9D9", lw=0.6)
    fig.tight_layout()
    out = OUT_DIR / "fig2c_ampdu.png"
    fig.savefig(out, dpi=150)
    print(f"saved {out}")


def main():
    fig, axes = plt.subplots(len(RUNS), 1, figsize=(6, 13))
    for ax, name, label in zip(axes, RUNS, ["(a)", "(b)", "(c)"]):
        plot_panel(ax, read_kpis(name), label)
    fig.tight_layout(h_pad=3.0)
    out = OUT_DIR / "fig2.png"
    fig.savefig(out, dpi=150)
    print(f"saved {out}")
    plot_ampdu()


if __name__ == "__main__":
    main()
