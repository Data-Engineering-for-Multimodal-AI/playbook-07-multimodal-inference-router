"""Shared helpers for the Try this experiments: the sample streams, read from
"raw data/" with the pipeline's own parsing, and the pipeline's own fusion
function (fusion_router.fuse_and_route_data). Writes nothing."""

import contextlib
import datetime
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_cwd = os.getcwd()
os.chdir(ROOT)  # both modules create their output folders relative to the working directory
import fusion_router  # noqa: E402
import preprocess  # noqa: E402
os.chdir(_cwd)

RAW = os.path.join(ROOT, "raw data")


def parse_ts(value):
    return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_streams():
    """(vision, soil) records as fuse_and_route_data expects them, without the
    random embeddings (they don't affect matching)."""
    vision, soil = [], []
    with open(os.path.join(RAW, "droneImageMetadata.jsonl")) as fh:
        for line in fh:
            r = json.loads(line)
            vision.append({"event_ts": r["event_ts"], "plot_id": r["plot_id"], "embedding": [],
                           "event_ts_dt": parse_ts(r["event_ts"])})
    with open(os.path.join(RAW, "soilSensorReading.jsonl")) as fh:
        for line in fh:
            r = json.loads(line)
            soil.append({"event_ts": r["event_ts"], "plot_id": r["plot_id"],
                         "vwc": preprocess.normalize_volumetric_water_content(
                             preprocess.extract_numeric_value(r["volumetric_water_content"])),
                         "ph": preprocess.convert_voltage_to_ph(
                             preprocess.extract_numeric_value(r["soil_ph_voltage"])),
                         "event_ts_dt": parse_ts(r["event_ts"])})
    vision.sort(key=lambda r: r["event_ts_dt"])
    soil.sort(key=lambda r: r["event_ts_dt"])
    return vision, soil


def fuse(vision, soil, window_ms=None):
    """Run the pipeline's fusion with another window; restores the setting afterwards."""
    saved = fusion_router.MAX_FUSION_GAP_MS
    if window_ms is not None:
        fusion_router.MAX_FUSION_GAP_MS = window_ms
    try:
        with contextlib.redirect_stderr(io.StringIO()):  # tqdm progress bar
            return fusion_router.fuse_and_route_data(vision, soil)
    finally:
        fusion_router.MAX_FUSION_GAP_MS = saved
