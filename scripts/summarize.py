"""Summarize a run of the router: what was fused, how far apart, and how long inference took.

    make summary                    # the sample run (output/)
    make summary RUN=runs/my_field  # a run of make load

Reads the files the three steps write; changes nothing.
"""

import json
import os
import statistics
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(path):
    with open(path) as fh:
        return [json.loads(line) for line in fh if line.strip()]


def pct(values, q):
    values = sorted(values)
    return values[min(len(values) - 1, int(round(q / 100 * (len(values) - 1))))]


def main():
    base = os.path.join(ROOT, sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else "")
    out = os.path.join(base, "output")
    try:
        fused = read(os.path.join(out, "inference_queue_per_event.jsonl"))
        alone = read(os.path.join(out, "inference_queue_vision_only.jsonl"))
        results = read(os.path.join(out, "inference_results.jsonl"))
    except FileNotFoundError as e:
        sys.exit(f"{e.filename} not found. Run make run (or make load DIR=...) first.")

    total = len(fused) + len(alone)
    print(f"Drone frames: {total}. Fused with soil: {len(fused)} ({len(fused) / total:.1%}). "
          f"Vision-only: {len(alone)}.")
    if fused:
        gaps = [r["fusion_gap_ms"] for r in fused]
        print(f"Gap between a frame and its soil reading: median {statistics.median(gaps):.0f} ms, "
              f"max {max(gaps):.0f} ms.")
    print("\nPer plot:")
    plots = sorted({r["plot_id"] for r in fused + alone})
    for p in plots:
        f = sum(r["plot_id"] == p for r in fused)
        a = sum(r["plot_id"] == p for r in alone)
        print(f"  {p:10} {f:4} fused  {a:4} vision-only")
    if results:
        lat = [r["latency_ms"] for r in results]
        print(f"\nInference (mock): {len(results)} requests, latency p50 {pct(lat, 50):.0f} ms, "
              f"p95 {pct(lat, 95):.0f} ms, max {max(lat):.0f} ms, total {sum(lat) / 1000:.1f} s.")
        actions = Counter(r["action"] for r in results)
        print("Actions: " + ", ".join(f"{k} {v}" for k, v in sorted(actions.items()))
              + " (random: the mock ignores its input).")


if __name__ == "__main__":
    main()
