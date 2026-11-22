"""Check your own drone and soil streams and run the router on them.

    make check-data DIR=my_field   # check both files, write nothing
    make load DIR=my_field         # check them, then run the three steps on them

The folder holds the two files "raw data/" holds, with the same names and fields,
one JSON object per line:

    my_field/
      droneImageMetadata.jsonl   {"event_ts": "2025-04-30T16:00:00.060Z", "plot_id": "Plot_003",
                                  "modal_tag": "vision", ...}
      soilSensorReading.jsonl    {"event_ts": "2025-04-30T16:00:00Z", "plot_id": "Plot_003",
                                  "modal_tag": "soil", "volumetric_water_content": "628 mV",
                                  "soil_ph_voltage": "1758 mV", ...}

The checks cover what makes a step crash or silently mismatch: lines that
aren't JSON or UTF-8, missing fields, timestamps without a time zone (mixed
with the sample's UTC times, fusion_router.py fails on them), soil values that
aren't a whole number of mV (or are negative, which the pipeline reads as
positive), plots that appear in only one stream, and streams whose time ranges
don't overlap. Values outside the pipeline's calibration ranges (300-700 mV for
water content, 1500-1800 mV for pH) are clipped by preprocess.py; they are
listed as notes. If any check fails, nothing is written.

`make load` runs preprocess.py, fusion_router.py and inference_client.py in
runs/<folder name>/, where "raw data" points to your folder, so "raw data/"
and the sample outputs are left alone. The results are in
runs/<folder name>/output/.
"""

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = {"vision": "droneImageMetadata.jsonl", "soil": "soilSensorReading.jsonl"}
REQUIRED = {"vision": ["event_ts", "plot_id", "modal_tag"],
            "soil": ["event_ts", "plot_id", "modal_tag", "volumetric_water_content", "soil_ph_voltage"]}
MV = re.compile(r"\s*(\d+)\s*mV\s*")
RANGES = {"volumetric_water_content": (300, 700), "soil_ph_voltage": (1500, 1800)}
STEPS = ["preprocess.py", "fusion_router.py", "inference_client.py"]
MAX_PER_FILE = 10


def parse_ts(value):
    """Parse like fusion_router.py does. Returns (datetime or None, problem or None)."""
    if not isinstance(value, str):
        return None, f"event_ts should be a string, got {type(value).__name__}"
    try:
        ts = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None, f"event_ts {value!r} is not ISO 8601"
    if ts.tzinfo is None:
        return None, f"event_ts {value!r} has no time zone (add Z or +00:00)"
    return ts, None


def check_file(path, kind):
    """Return ({plot: [first, last]}, [problems], [notes], record count) for one stream."""
    name = os.path.basename(path)
    with open(path, "rb") as fh:
        head = fh.read(100)
    if not head:
        return {}, [f"{name}: empty file"], [], 0
    if head.startswith(b"version https://git-lfs"):
        return {}, [f"{name}: Git LFS pointer, not the file"], [], 0
    plots, problems, notes, count = {}, [], [], 0
    clipped = Counter()
    with open(path, "rb") as fh:
        for n, raw in enumerate(fh, start=1):
            if len(problems) >= MAX_PER_FILE:
                problems.append(f"{name}: (stopped after {MAX_PER_FILE} problems in this file)")
                break
            if not raw.strip():
                continue
            try:
                line = raw.decode("utf-8")
            except UnicodeDecodeError:
                problems.append(f"{name} line {n}: not UTF-8")
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                problems.append(f"{name} line {n}: not valid JSON")
                continue
            if not isinstance(rec, dict):
                problems.append(f"{name} line {n}: not a JSON object")
                continue
            missing = [f for f in REQUIRED[kind] if f not in rec]
            if missing:
                problems.append(f"{name} line {n}: missing {', '.join(missing)}")
                continue
            count += 1
            if rec["modal_tag"] != kind:
                problems.append(f"{name} line {n}: modal_tag is {rec['modal_tag']!r}, expected {kind!r}")
            ts, problem = parse_ts(rec["event_ts"])
            if problem:
                problems.append(f"{name} line {n}: {problem}")
                continue
            if kind == "soil":
                for field, (low, high) in RANGES.items():
                    value = rec[field]
                    m = MV.fullmatch(value) if isinstance(value, str) else None
                    if not m:
                        problems.append(f"{name} line {n}: {field} {value!r} is not a whole number of mV "
                                        f"like \"520 mV\"")
                    elif not low <= int(m.group(1)) <= high:
                        clipped[field] += 1
            span = plots.setdefault(str(rec["plot_id"]), [ts, ts])
            span[0], span[1] = min(span[0], ts), max(span[1], ts)
    for field, k in clipped.items():
        low, high = RANGES[field]
        notes.append(f"{name}: {k} {field} value{'s' if k != 1 else ''} outside {low}-{high} mV; "
                     f"preprocess.py clips {'them' if k != 1 else 'it'} to the range")
    if count == 0 and not problems:
        problems.append(f"{name}: no records")
    return plots, problems, notes, count


def scan(folder):
    """Check both files. Returns ({kind: count}, [problems], [notes])."""
    problems, notes, counts, plots = [], [], {}, {}
    for kind, name in FILES.items():
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            problems.append(f"{name}: missing (both {FILES['vision']} and {FILES['soil']} are needed)")
            continue
        plots[kind], found, extra, counts[kind] = check_file(path, kind)
        problems += found
        notes += extra
    if len(plots) < 2:
        return counts, problems, notes
    vision, soil = plots["vision"], plots["soil"]
    for p in sorted(set(vision) - set(soil)):
        notes.append(f"plot {p}: drone frames but no soil readings; all its frames go to vision-only")
    for p in sorted(set(soil) - set(vision)):
        notes.append(f"plot {p}: soil readings but no drone frames; they are never used")
    shared = set(vision) & set(soil)
    if not shared:
        problems.append("no plot_id appears in both files, so nothing can be fused")
    else:
        v0, v1 = min(vision[p][0] for p in shared), max(vision[p][1] for p in shared)
        s0, s1 = min(soil[p][0] for p in shared), max(soil[p][1] for p in shared)
        if v1 < s0 or s1 < v0:
            problems.append(f"the streams don't overlap in time (drone {v0.isoformat()} to {v1.isoformat()}, "
                            f"soil {s0.isoformat()} to {s1.isoformat()}), so nothing can be fused; "
                            f"check the clocks and time zones")
    return counts, problems, notes


def main():
    p = argparse.ArgumentParser(description="Check drone and soil streams and run the router on them.")
    p.add_argument("--dir", required=True, help=f"folder with {FILES['vision']} and {FILES['soil']}")
    p.add_argument("--check-only", action="store_true", help="check the files and write nothing")
    args = p.parse_args()
    folder = os.path.abspath(args.dir)
    if not os.path.isdir(folder):
        sys.exit(f"No such folder: {args.dir}")

    counts, problems, notes = scan(folder)
    print(f"{args.dir}: {counts.get('vision', 0)} drone frames, {counts.get('soil', 0)} soil readings")
    for line in notes:
        print(f"  note: {line}")
    if problems:
        print(f"\n{len(problems)} problem(s):")
        for line in problems:
            print(f"  {line}")
        sys.exit("\nFix these lines and run again. Nothing was written.")
    print("All records passed the checks.", flush=True)
    if args.check_only:
        return

    run_dir = os.path.join(ROOT, "runs", os.path.basename(folder.rstrip(os.sep)))
    if os.path.realpath(folder) == os.path.realpath(os.path.join(ROOT, "raw data")):
        sys.exit("That is the sample data; use make run for it.")
    shutil.rmtree(run_dir, ignore_errors=True)
    os.makedirs(run_dir)
    os.symlink(folder, os.path.join(run_dir, "raw data"))
    for step in STEPS:
        print(f"\n$ python {step}   (in {os.path.relpath(run_dir, ROOT)}/)", flush=True)
        result = subprocess.run([sys.executable, os.path.join(ROOT, step)], cwd=run_dir)
        if result.returncode:
            sys.exit(f"{step} failed (exit {result.returncode}).")
    print(f"\nResults: {os.path.relpath(run_dir, ROOT)}/output/")


if __name__ == "__main__":
    main()
