"""Checks for the "Use your own data" loader (scripts/load_streams.py). Writes only to tmp_path."""

import json
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "raw data")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from load_streams import scan  # noqa: E402

DRONE, SOIL = "droneImageMetadata.jsonl", "soilSensorReading.jsonl"


@pytest.fixture
def folder(tmp_path):
    for name in (DRONE, SOIL):
        with open(os.path.join(RAW, name)) as src:
            lines = src.readlines()[:100]
        (tmp_path / name).write_text("".join(lines))
    return tmp_path


def edit(path, line_no, change):
    lines = path.read_text().splitlines()
    rec = json.loads(lines[line_no - 1])
    change(rec)
    lines[line_no - 1] = json.dumps(rec)
    path.write_text("\n".join(lines) + "\n")


def test_sample_data_passes():
    counts, problems, notes = scan(RAW)
    assert problems == [] and notes == []
    assert counts == {"vision": 1000, "soil": 957}


def test_good_folder(folder):
    counts, problems, _ = scan(str(folder))
    assert problems == []
    assert counts == {"vision": 100, "soil": 100}


def test_missing_file(folder):
    (folder / SOIL).unlink()
    _, problems, _ = scan(str(folder))
    assert len(problems) == 1 and problems[0].startswith(f"{SOIL}: missing")


@pytest.mark.parametrize("name,change,expected", [
    (DRONE, lambda r: r.pop("plot_id"), "missing plot_id"),
    (DRONE, lambda r: r.update(modal_tag="image"), "modal_tag is 'image'"),
    (DRONE, lambda r: r.update(event_ts="yesterday"), "is not ISO 8601"),
    (SOIL, lambda r: r.update(event_ts="2025-04-30T16:00:03"), "has no time zone"),
    (SOIL, lambda r: r.update(volumetric_water_content="-15 mV"), "is not a whole number of mV"),
    (SOIL, lambda r: r.update(soil_ph_voltage="1.7 V"), "is not a whole number of mV"),
    (SOIL, lambda r: r.update(soil_ph_voltage=1700), "is not a whole number of mV"),
])
def test_bad_records(folder, name, change, expected):
    edit(folder / name, 3, change)
    _, problems, _ = scan(str(folder))
    assert len(problems) == 1 and expected in problems[0], problems
    assert problems[0].startswith(f"{name} line 3:")


@pytest.mark.parametrize("content,expected", [
    (b'{"event_ts": "2025', "not valid JSON"),
    (b"\xff\xfe{}", "not UTF-8"),
    (b"[1, 2]", "not a JSON object"),
])
def test_unreadable_lines(folder, content, expected):
    with open(folder / DRONE, "ab") as fh:
        fh.write(content + b"\n")
    _, problems, _ = scan(str(folder))
    assert len(problems) == 1 and expected in problems[0], problems


def test_lfs_pointer_and_empty(folder):
    (folder / DRONE).write_bytes(b"version https://git-lfs.github.com/spec/v1\n")
    (folder / SOIL).write_bytes(b"")
    _, problems, _ = scan(str(folder))
    assert any("Git LFS pointer" in p for p in problems) and any("empty file" in p for p in problems)


def test_out_of_range_is_a_note(folder):
    edit(folder / SOIL, 3, lambda r: r.update(volumetric_water_content="850 mV"))
    _, problems, notes = scan(str(folder))
    assert problems == []
    assert any("1 volumetric_water_content value outside 300-700 mV" in n for n in notes)


def test_plot_in_one_stream_is_a_note(folder):
    edit(folder / SOIL, 3, lambda r: r.update(plot_id="Plot_009"))
    _, problems, notes = scan(str(folder))
    assert problems == []
    assert any("plot Plot_009: soil readings but no drone frames" in n for n in notes)


def test_streams_that_dont_overlap(folder):
    path = folder / SOIL
    lines = [json.loads(line) for line in path.read_text().splitlines()]
    for rec in lines:
        rec["event_ts"] = rec["event_ts"].replace("2025-04-30", "2024-04-30")
    path.write_text("".join(json.dumps(r) + "\n" for r in lines))
    _, problems, _ = scan(str(folder))
    assert len(problems) == 1 and "don't overlap in time" in problems[0]


def test_load_runs_in_its_own_folder(folder, tmp_path):
    work = tmp_path / "repo"
    shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns(".venv", ".git", "runs", "output", "normalized"))
    result = subprocess.run([sys.executable, str(work / "scripts" / "load_streams.py"), "--dir", str(folder)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    out = work / "runs" / folder.name / "output"
    assert len((out / "inference_results.jsonl").read_text().splitlines()) > 0
    assert not (work / "output").exists() and not (work / "normalized").exists()
