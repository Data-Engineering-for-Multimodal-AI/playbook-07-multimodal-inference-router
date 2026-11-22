"""Try this 3: how does fusion time grow with the streams? (make try-scale)

fuse_and_route_data compares each drone frame with every soil reading of its
plot, so the work grows with frames x readings. This repeats the sample
streams 1 to TIMES times (each copy moved later in time, so the matches stay
the same) and times the pipeline's fusion against a version that binary-searches
each plot's sorted readings for the nearest one. Both must return the same matches.

Change TIMES (or pass them: make try-scale TIMES="1 2 4") and run it again.
"""

import bisect
import datetime
import sys
import time

import common

TIMES = [int(t) for t in sys.argv[1:]] or [1, 4, 16]


def repeat(records, n, span):
    out = []
    for k in range(n):
        for r in records:
            r = dict(r)
            r["event_ts_dt"] = r["event_ts_dt"] + k * span
            r["event_ts"] = r["event_ts_dt"].isoformat()
            out.append(r)
    return out


def fuse_bisect(vision, soil, window_ms=500):
    by_plot = {}
    for r in soil:
        by_plot.setdefault(r["plot_id"], []).append(r)
    times = {p: [r["event_ts_dt"] for r in rs] for p, rs in by_plot.items()}
    fused, alone = [], []
    for v in vision:
        rs, ts = by_plot.get(v["plot_id"]), times.get(v["plot_id"])
        best = None
        if rs:
            i = bisect.bisect_left(ts, v["event_ts_dt"])
            for j in (i - 1, i):
                if 0 <= j < len(rs):
                    gap = abs((v["event_ts_dt"] - ts[j]).total_seconds()) * 1000
                    if gap <= window_ms and (best is None or gap < best[0]):
                        best = (gap, rs[j])
        if best:
            fused.append({"plot_id": v["plot_id"], "event_ts": v["event_ts"], "vwc": best[1]["vwc"],
                          "ph": best[1]["ph"], "fusion_gap_ms": best[0]})
        else:
            alone.append(v)
    return fused, alone


def main():
    vision, soil = common.load_streams()
    span = max(vision[-1]["event_ts_dt"], soil[-1]["event_ts_dt"]) - vision[0]["event_ts_dt"] \
        + datetime.timedelta(minutes=1)
    print(f"{'copies':>6} {'frames':>7} {'soil readings':>13} {'fused':>6} "
          f"{'fusion_router.py':>16} {'binary search':>13}")
    for n in TIMES:
        v, s = repeat(vision, n, span), repeat(soil, n, span)
        start = time.perf_counter()
        fused, _ = common.fuse(v, s)
        a = time.perf_counter() - start
        start = time.perf_counter()
        fused_b, _ = fuse_bisect(v, s)
        b = time.perf_counter() - start
        key = lambda r: (r["plot_id"], r["event_ts"], r["vwc"], r["ph"])  # noqa: E731
        assert sorted(map(key, fused)) == sorted(map(key, fused_b)), "the two fusions disagree"
        print(f"{n:6} {len(v):7,} {len(s):13,} {len(fused):6,} {a:15.2f}s {b:12.3f}s")


if __name__ == "__main__":
    main()
