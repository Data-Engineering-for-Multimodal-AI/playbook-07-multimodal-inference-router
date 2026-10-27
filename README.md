# Building a Real-Time Multimodal Inference Router

**Chapter 7 playbook** from *Data Engineering for Multimodal AI* (O'Reilly, 2026), pages 260–271 (Early Release page numbers; they may differ in the final print).
Book: https://oreil.ly/data-engineering-multimodal

> Want the code exactly as printed? Use the `first-edition` tag. This branch is the 2026 maintenance update; see [Differences from the printed book](#differences-from-the-printed-book).

## What you'll build

This project implements a real-time multimodal inference router for precision agriculture, as described in Chapter 7. The pipeline ingests asynchronous data from drone-mounted cameras and soil sensors, performs windowed temporal fusion, routes records to inference modes, and logs observability signals for drift detection and retraining.

This playbook delivers a locally executable prototype. Each section of the chapter pairs it with a real-world translation explaining how the same logic scales in production.

The pipeline has three steps, plus optional orchestration:

1. **Preprocessing** (`preprocess.py`) extracts volumetric water content and pH from soil telemetry (mV readings) and normalizes them. It also simulates a 256-dimensional embedding per drone frame. The embeddings are **random vectors** standing in for a vision model such as MobileNet; no images are included.
2. **Fusion and routing** (`fusion_router.py`) matches each drone frame to the closest soil reading for the same `plot_id` within 500 ms of event time. Matched records go to the inference queue; unmatched ones go to a vision-only fallback queue.
3. **Inference** (`inference_client.py`) builds a `FusedRecord` Protobuf message (`fused_record.proto`), serializes it, and sends it to a **mock** client. The mock simulates 20–100 ms of server latency and returns a **random** action and confidence that don't depend on the input. Each result logs the action, confidence, entropy and latency.
4. **Orchestration (optional)**: the Airflow DAG `fieldsense_inference_dag.py` runs the three steps in order.

Runs on a laptop CPU in under a minute. No GPU or cloud account required.

## Quick start

With pip:

```bash
pip install -r requirements.txt     # Python 3.12 or newer
python preprocess.py
python fusion_router.py
python inference_client.py
```

The book's `python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. fused_record.proto` (page 268) also works; it regenerates the stubs, which are already committed.

Using [uv](https://docs.astral.sh/uv/) instead:

```bash
uv sync
uv run python preprocess.py
uv run python fusion_router.py
uv run python inference_client.py
```

`preprocess.py` and `inference_client.py` accept `--seed` (default 42), so results repeat between runs.

Run the end-to-end check (about 30 seconds): `make smoke`

### Optional: run with Airflow

Airflow is a separate install, made with Airflow's official constraints file (use `constraints-3.13.txt` on Python 3.13):

```bash
pip install -r requirements-airflow.txt \
  --constraint https://raw.githubusercontent.com/apache/airflow/constraints-3.3.2/constraints-3.12.txt
```

Make the DAG visible to Airflow, then trigger it from the UI or CLI:

```bash
ln -s "$PWD/fieldsense_inference_dag.py" "$AIRFLOW_HOME/dags/"   # or your DAGs folder
airflow dags test fieldsense_inference_router                    # one local run
```

Tasks run from the folder that holds the scripts (`FIELDSENSE_HOME`). It defaults to the DAG file's real location, so a symlink works. If you copy the DAG file instead, or deploy it (for example to `/opt/fieldsense`), set `FIELDSENSE_HOME` to that folder.

With uv: `uv sync --extra airflow`.

## Tested on

| Date | OS | Python | Key libraries |
|---|---|---|---|
| 2026-10-12 | macOS 26.5.1 (arm64) | 3.12.15, 3.13.16 | numpy 2.5.3, protobuf 6.33.6, grpcio 1.83.1, tqdm 4.70.1; optional apache-airflow 3.3.2 (providers-standard 1.19.0) |
| CI, on every push | ubuntu-latest | 3.12, 3.13 | same, from `uv.lock`; the Airflow DAG runs once on 3.12 |

## Differences from the printed book

| What changed | Why | Book page |
|---|---|---|
| `requirements.txt` no longer includes Airflow; it's now in `requirements-airflow.txt`, installed with Airflow's constraints file | The book promises a laptop run; Airflow added 134 packages (~323 MB) that the three steps don't use | n/a (first-edition repository) |
| Python 3.12+ (was 3.8+); versions pinned | Current releases; the old stubs failed with the older protobuf and grpcio that the requirements allowed | n/a (first-edition repository) |
| The DAG runs locally: tasks run from `FIELDSENSE_HOME` instead of `python /opt/fieldsense/...`, and import `BashOperator` from `airflow.providers.standard` | In the first edition, the DAG failed: `/opt/fieldsense` doesn't exist, and the scripts' relative paths broke in Airflow's temp working directory | n/a (first-edition DAG) |
| `--seed` (default 42) on `preprocess.py` and `inference_client.py` | Embeddings and mock predictions changed on every run | n/a |
| Protobuf stubs regenerated (`make proto`); `grpcio-tools` pinned in `requirements.txt` | Match the pinned protobuf and grpcio; the protoc command needs `grpcio-tools` | 268 |
| The mock client receives serialized bytes (`SerializeToString()`) | Matches what the text describes | n/a |
| README file names corrected: the data folder is `raw data/` (with a space) and the soil file is `soilSensorReading.jsonl` | The old README and the book listed `raw-data/` and `soilSensorReadings.jsonl` | 261 |

Notes on the chapter text:
- The header contract names the key `field_id` (p. 225). The code and the rest of the chapter use `plot_id`.
- The chapter introduction mentions a frame every 33 ms (p. 221). The sample data and pipeline run at about 2 Hz (a frame about every 500 ms), with soil readings at 1 Hz.

This section is the record of changes since printing. Full list: [CHANGELOG.md](CHANGELOG.md).

## Data and licenses

| Path | Records | What |
|---|---|---|
| `raw data/droneImageMetadata.jsonl` | 1000 | Drone frame metadata: event time, plot, file name, camera ISO, shutter speed. 5 plots, about 2 Hz over 8m19s. No image files |
| `raw data/soilSensorReading.jsonl` | 957 | Soil sensor readings in mV (volumetric water content, pH voltage). 5 plots, 1 Hz over 16m39s |

Both are synthetic sample data generated by the author for this playbook. License: MIT, the same as the code.

## Expected output

From a fresh clone on 2026-10-12, macOS 26.5.1 arm64, Python 3.12.15, using `pip install -r requirements.txt` (progress bars omitted). This is the output of this version; it may differ from the output printed in the book, and that's okay.

```
$ python preprocess.py
Starting preprocessing of sensor data...
Processed 1000 vision records and saved to normalized/vision_embeddings.jsonl
Processed 957 soil records and saved to normalized/soil_vectors.jsonl
Preprocessing complete!

Note: The output files are saved in the local 'normalized' folder.
In a production environment, these would go to '/mnt/data/normalized/' as specified in the requirements.
```

```
$ python fusion_router.py
Starting event-time fusion and inference routing...
Loading vision data from normalized/vision_embeddings.jsonl...
Loaded 1000 vision records
Loading soil data from normalized/soil_vectors.jsonl...
Loaded 957 soil records
Performing windowed event-time fusion and routing...
Saved 201 fused records to output/inference_queue_per_event.jsonl
Saved 799 vision-only records to output/inference_queue_vision_only.jsonl

Fusion and routing complete!

Fusion statistics:
Total records processed: 1000
Records successfully fused: 201 (20.1%)
Records routed to vision-only: 799 (79.9%)
```

```
$ python inference_client.py
Initializing mock inference client...
Processing 201 fused records...
Results written to output/inference_results.jsonl
```

First line of `output/inference_results.jsonl` (with the default seed; `latency_ms` is measured and varies):

```json
{"plot_id": "Plot_003", "event_ts": "2025-04-30T16:00:00.060000Z", "action": "spray", "confidence": 0.3550697001441001, "entropy": 0.6449302998558999, "latency_ms": 76.35498046875, "server_latency_ms": 71.1541438766307}
```

Across the 201 results: fertilize 37, harvest 46, irrigate 40, monitor 42, spray 36; mean confidence 0.487. These come from the random mock, not a model.

## Project structure

```
preprocess.py                # Normalizes raw drone and soil sensor data
fusion_router.py             # Event-time windowed fusion and routing
inference_client.py          # Serializes fused records, simulates gRPC inference
fused_record.proto           # Protobuf schema (FusedRecord; PredictionRequest/Response are not used yet)
fused_record_pb2*.py         # Generated from the .proto (make proto)
fieldsense_inference_dag.py  # Optional Airflow DAG orchestrating the pipeline
raw data/                    # Sample input (droneImageMetadata.jsonl, soilSensorReading.jsonl)
normalized/                  # Created by preprocess.py
output/                      # Created by fusion_router.py and inference_client.py
tests/test_smoke.py          # make smoke
```

## License

MIT License

Copyright (c) 2025-2026  
*Data Engineering for Multimodal AI*

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE. 