"""
End-to-end smoke test: run the three printed steps on the sample data.

CPU only, no network, about 30 seconds (the mock client sleeps 20-100 ms per record).
Run with `make smoke`.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STEPS = ["preprocess.py", "fusion_router.py", "inference_client.py"]


def run_pipeline():
    outputs = {}
    for script in STEPS:
        result = subprocess.run(
            [sys.executable, script], cwd=ROOT, capture_output=True, text=True, timeout=300,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        outputs[script] = result.stdout
    return outputs


def read_jsonl(relative_path):
    with open(ROOT / relative_path) as f:
        return [json.loads(line) for line in f if line.strip()]


@pytest.fixture(scope="module")
def first_run():
    return run_pipeline()


def test_preprocess_counts(first_run):
    out = first_run["preprocess.py"]
    assert "Processed 1000 vision records" in out
    assert "Processed 957 soil records" in out
    vision = read_jsonl("normalized/vision_embeddings.jsonl")
    assert len(vision[0]["embedding"]) == 256
    soil = read_jsonl("normalized/soil_vectors.jsonl")
    assert all(0.0 <= r["vwc"] <= 1.0 and 5.5 <= r["ph"] <= 7.5 for r in soil)


def test_fusion_counts(first_run):
    out = first_run["fusion_router.py"]
    assert "Records successfully fused: 201 (20.1%)" in out
    assert "Records routed to vision-only: 799 (79.9%)" in out
    fused = read_jsonl("output/inference_queue_per_event.jsonl")
    assert all(r["fusion_gap_ms"] <= 500 for r in fused)


def test_inference_results(first_run):
    results = read_jsonl("output/inference_results.jsonl")
    assert len(results) == 201
    assert all("error" not in r for r in results)
    assert {r["action"] for r in results} <= {"spray", "irrigate", "fertilize", "monitor", "harvest"}


def test_protobuf_round_trip(first_run):
    sys.path.insert(0, str(ROOT))
    import fused_record_pb2 as pb2
    from inference_client import record_to_proto

    record = read_jsonl("output/inference_queue_per_event.jsonl")[0]
    decoded = pb2.FusedRecord.FromString(record_to_proto(record).SerializeToString())
    assert decoded.plot_id == record["plot_id"]
    assert len(decoded.embedding) == 256


def test_seeded_runs_repeat(first_run):
    def snapshot():
        fused = (ROOT / "output/inference_queue_per_event.jsonl").read_text()
        results = [(r["plot_id"], r["event_ts"], r["action"], r["confidence"])
                   for r in read_jsonl("output/inference_results.jsonl")]
        return fused, results

    before = snapshot()
    run_pipeline()
    assert snapshot() == before


def test_dag_parses_if_airflow_installed():
    pytest.importorskip("airflow")
    sys.path.insert(0, str(ROOT))
    import fieldsense_inference_dag as dag_module

    tasks = {t.task_id: t for t in dag_module.dag.tasks}
    assert list(tasks) == ["preprocess_data", "fuse_and_route", "run_inference"]
    assert all(t.cwd == str(ROOT) for t in tasks.values())
