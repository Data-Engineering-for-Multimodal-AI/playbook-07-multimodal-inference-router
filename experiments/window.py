"""Try this 1: how wide should the fusion window be? (make try-window)

fusion_router.py matches each drone frame with the closest soil reading for the
same plot within MAX_FUSION_GAP_MS (500 ms) of event time; frames with no match
go to the vision-only queue. This runs the same fusion with other windows and
reports how many frames get soil data and how old that soil reading can be.

Change WINDOWS and run it again.
"""

import statistics

import common

WINDOWS = [100, 250, 500, 1000, 2500, 5000, 10000]


def main():
    vision, soil = common.load_streams()
    plots = sorted({r["plot_id"] for r in soil})
    gaps = {p: [(b["event_ts_dt"] - a["event_ts_dt"]).total_seconds()
                for a, b in zip([r for r in soil if r["plot_id"] == p], [r for r in soil if r["plot_id"] == p][1:])]
            for p in plots}
    every = statistics.median(g for p in plots for g in gaps[p])
    print(f"{len(vision)} drone frames, {len(soil)} soil readings over {len(plots)} plots; "
          f"each plot gets a soil reading every {every:.0f} s (median).\n")
    print(f"{'window':>8} {'fused':>6} {'fused %':>7} {'vision-only':>11} {'median gap':>10} {'max gap':>8}")
    for w in WINDOWS:
        fused, alone = common.fuse(vision, soil, w)
        g = [r["fusion_gap_ms"] for r in fused]
        med = f"{statistics.median(g):.0f} ms" if g else "-"
        top = f"{max(g):.0f} ms" if g else "-"
        mark = "  <- the pipeline" if w == 500 else ""
        print(f"{w:6} ms {len(fused):6} {len(fused) / len(vision):7.1%} {len(alone):11} {med:>10} {top:>8}{mark}")


if __name__ == "__main__":
    main()
