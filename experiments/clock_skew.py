"""Try this 2: what if the soil sensors' clocks are off? (make try-skew)

Fusion trusts each record's event_ts. A sensor clock that runs ahead or behind
moves every reading by the same offset, and the pipeline can't tell. This
shifts every soil timestamp by OFFSETS and runs the pipeline's fusion (500 ms
window): how many frames still find soil data, and how many of those matches
pair the frame with a different soil reading than with correct clocks.

Change OFFSETS and run it again.
"""

import datetime

import common

OFFSETS = [0, 100, 250, 500, 1000, 2000, -500]


def shifted(soil, ms):
    out = []
    for r in soil:
        r = dict(r)
        r["event_ts_dt"] = r["event_ts_dt"] + datetime.timedelta(milliseconds=ms)
        out.append(r)
    return out


def main():
    vision, soil = common.load_streams()
    base, _ = common.fuse(vision, soil)
    truth = {(r["plot_id"], r["event_ts"]): (r["vwc"], r["ph"]) for r in base}
    print(f"{'soil clock offset':>17} {'fused':>6} {'fused %':>7} {'same match as offset 0':>23} {'different reading':>17}")
    for ms in OFFSETS:
        fused, _ = common.fuse(vision, shifted(soil, ms))
        got = {(r["plot_id"], r["event_ts"]): (r["vwc"], r["ph"]) for r in fused}
        same = sum(1 for k, v in got.items() if truth.get(k) == v)
        print(f"{ms:+14} ms {len(fused):6} {len(fused) / len(vision):7.1%} {same:23} {len(got) - same:17}")


if __name__ == "__main__":
    main()
