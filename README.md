# Playbook 07: Route drone and soil streams to real-time inference
**How to build a real-time multimodal inference router.** Chapter 7 of [*Data Engineering for Multimodal AI*](https://oreil.ly/data-engineering-multimodal) (O'Reilly, 2026), pages 256–267.

Drone images and soil sensors report on different clocks, but a decision to spray or irrigate has to use both within seconds. In this repo, we explore this with FieldSense, a fictional precision agriculture company. Follow along to align the two streams by event time, route each record to the right inference path, fall back when it falls behind, and log latency and drift, all on a laptop.

**The problem.** Two streams with different clocks have to be matched in time and acted on within a latency budget, even when one of them falls behind.

**What you'll work with.** You'll align records by event time in windows, decide per record between immediate and batched inference, fall back when queues grow, and log latency, queue depth and drift.

> Following the book? Its commands are in [Run it the way the book does](#run-it-the-way-the-book-does) and still work as printed. Want the code exactly as printed? Use the `first-edition` tag. This branch is the 2026 maintenance update; see [Differences from the printed book](#differences-from-the-printed-book).

## Run it

You need [uv](https://docs.astral.sh/uv/) and `make`. No Docker, no Git LFS, no API keys. Or open the repo in a GitHub Codespace, where both are ready. On Windows without `make`, use a Codespace or the book's steps below.

**1. Get the code.** About 1 MB.

```bash
git clone https://github.com/Data-Engineering-for-Multimodal-AI/playbook-07-multimodal-inference-router.git
cd playbook-07-multimodal-inference-router
```

**2. Run the router.** Installs the locked dependencies (`uv sync`), then runs the book's three steps: `python preprocess.py` normalizes the soil readings and makes a stand-in embedding for each drone frame, `python fusion_router.py` matches frames and soil readings by event time, and `python inference_client.py` sends the matched records to the mock inference client. On a Mac this took 24 s from a fresh clone, 13 s of it the mock's simulated latency.

```bash
make run
```

You should see:

```
Processed 1000 vision records and saved to normalized/vision_embeddings.jsonl
Processed 957 soil records and saved to normalized/soil_vectors.jsonl
...
Records successfully fused: 201 (20.1%)
Records routed to vision-only: 799 (79.9%)
...
Results written to output/inference_results.jsonl
```

**3. Look at what came out.** Reads the three output files and summarizes them: how many frames found a soil reading, how far apart in time, per plot, and the inference latency.

```bash
make summary
```

```
Drone frames: 1000. Fused with soil: 201 (20.1%). Vision-only: 799.
Gap between a frame and its soil reading: median 179 ms, max 500 ms.

Per plot:
  Plot_001     35 fused   163 vision-only
  ...
Inference (mock): 201 requests, latency p50 63 ms, p95 104 ms, max 163 ms, total 13.3 s.
```

Four out of five frames go to the vision-only queue, and nothing reads that queue: `inference_client.py` only sends the fused records. The latencies come from the mock, which sleeps 20 to 100 ms and returns a random action. To see one record, open `output/inference_queue_per_event.jsonl`; each line carries the frame's plot, time, embedding, the soil values and `fusion_gap_ms`.

**4. Clean up.**

```bash
make clean
```

This deletes `normalized/`, `output/`, `runs/` (from [Use your own data](#use-your-own-data)) and the test cache. The sample data in `raw data/` stays.

## How much time do you have?

| Time | What to do |
|---|---|
| 15 minutes | [Run it](#run-it), steps 1 to 3. On a Mac, step 2 took 24 s. |
| 1 hour | The three [Try this](#try-this) experiments (each under 2 minutes on a Mac), then the [optional Airflow run](#optional-run-with-airflow). |
| 1 day | [Use your own data](#use-your-own-data) with your own streams, and work through [Before production](#before-production). |

## Try this

Each experiment changes one thing and measures the effect. They read `raw data/`, use the pipeline's own parsing and fusion code (`fuse_and_route_data` in `fusion_router.py`), and write nothing. The numbers below are from a Mac on 2026-11-21.

**1. How wide should the fusion window be?** The router pairs a frame with the closest soil reading for its plot within 500 ms. This runs the same fusion with windows from 100 ms to 10 s.

```bash
make try-window
```

```
1000 drone frames, 957 soil readings over 5 plots; each plot gets a soil reading every 4 s (median).

  window  fused fused % vision-only median gap  max gap
   100 ms     69    6.9%         931      42 ms    99 ms
   250 ms    104   10.4%         896      67 ms   237 ms
   500 ms    201   20.1%         799     179 ms   500 ms  <- the pipeline
  1000 ms    340   34.0%         660     450 ms  1000 ms
  2500 ms    654   65.4%         346     980 ms  2498 ms
  5000 ms    883   88.3%         117    1451 ms  4973 ms
 10000 ms    990   99.0%          10    1608 ms  9982 ms
```

Each plot's sensor reports about every 4 s, so a 500 ms window can only catch the frames that happen to land near a reading. A 5 s window fuses 88% of the frames, with soil data at most 5 s old. Whether that is fresh enough depends on how fast soil moisture changes, which is a question for the field, not the code. Change `WINDOWS` in `experiments/window.py` and run it again.

**2. What if the soil sensors' clocks are off?** Fusion trusts each record's `event_ts`. This shifts every soil timestamp by a fixed offset, as a sensor clock running ahead or behind would, and counts how many frames are now paired with a different soil reading than with correct clocks.

```bash
make try-skew
```

```
soil clock offset  fused fused %  same match as offset 0 different reading
            +0 ms    201   20.1%                     201                 0
          +100 ms    191   19.1%                     163                28
          +250 ms    192   19.2%                     149                43
          +500 ms    181   18.1%                     103                78
         +1000 ms    162   16.2%                       1               161
         +2000 ms    189   18.9%                       0               189
          -500 ms    187   18.7%                      97                90
```

The fused share stays between 16% and 20% whatever the offset, so the router's own statistics don't show the problem. At 1 s of skew, 161 of the 162 fused records carry a soil reading the frame wasn't taken next to. Watch the distribution of `fusion_gap_ms` per sensor, and sync the clocks. Change `OFFSETS` and run it again.

**3. How does fusion time grow with the streams?** `fuse_and_route_data` compares every frame with every soil reading of its plot. This repeats the sample streams 1, 4 and 16 times (later in time, so each copy matches the same way) and times the pipeline's fusion against a version that looks up the nearest reading by binary search in each plot's sorted readings. Both return the same matches.

```bash
make try-scale
```

```
copies  frames soil readings  fused fusion_router.py binary search
     1   1,000           957    201            0.17s        0.002s
     4   4,000         3,828    804            1.81s        0.007s
    16  16,000        15,312  3,216           63.69s        0.581s
```

Sixteen copies are about 2 hours of drone frames; the pipeline's fusion took a minute on them, against well under a second for the binary search. The work grows with the square of the stream length. The Mac was busy, so times varied between runs (another run took 30.6 s for 16 copies); in CI (ubuntu-latest, Python 3.13) 16 copies took 13.15 s against 0.017 s. Pass other sizes with `make try-scale TIMES="1 2 8"`.

## Use your own data

Put your two streams in a folder, with the same file names and fields as `raw data/`, one JSON object per line:

```
my_field/
  droneImageMetadata.jsonl   {"event_ts": "2025-04-30T16:00:00.060000Z", "plot_id": "Plot_003", "modal_tag": "vision", ...}
  soilSensorReading.jsonl    {"event_ts": "2025-04-30T16:00:00Z", "plot_id": "Plot_003", "modal_tag": "soil",
                              "volumetric_water_content": "628 mV", "soil_ph_voltage": "1758 mV", ...}
```

`event_ts` is ISO 8601 with a time zone (`Z` or `+00:00`). The soil values are whole numbers of millivolts.

Check it first. This reads every line and writes nothing:

```bash
make check-data DIR=my_field
```

It reports every line a step would crash on or misread. On a test folder with mistakes in it:

```
my_field: 199 drone frames, 199 soil readings
  note: soilSensorReading.jsonl: 1 volumetric_water_content value outside 300-700 mV; preprocess.py clips it to the range
  note: plot Plot_009: soil readings but no drone frames; they are never used

6 problem(s):
  droneImageMetadata.jsonl line 3: missing plot_id
  droneImageMetadata.jsonl line 5: modal_tag is 'image', expected 'vision'
  soilSensorReading.jsonl line 4: volumetric_water_content '-15 mV' is not a whole number of mV like "520 mV"
  soilSensorReading.jsonl line 6: soil_ph_voltage '1.7 V' is not a whole number of mV like "520 mV"
  soilSensorReading.jsonl line 8: event_ts '2025-04-30 16:00:07' has no time zone (add Z or +00:00)
  soilSensorReading.jsonl line 14: not valid JSON

Fix these lines and run again. Nothing was written.
```

Two of these would pass `preprocess.py` without an error and give wrong values: it reads `-15 mV` as 15 mV and `1.7 V` as 1 mV. The checker also catches lines that aren't UTF-8, empty files, Git LFS pointers, and two streams that don't overlap in time. When everything passes, run the router on your folder and summarize it:

```bash
make load DIR=my_field
make summary RUN=runs/my_field
```

```
Saved 37 fused records to output/inference_queue_per_event.jsonl
...
Results: runs/my_field/output/
Drone frames: 200. Fused with soil: 37 (18.5%). Vision-only: 163.
Gap between a frame and its soil reading: median 352 ms, max 489 ms.
```

`make load` runs the three steps in `runs/<folder name>/`, where `raw data` points to your folder, so the sample data and its outputs are left alone. It took 5 s for 200 frames on a Mac.

## What you end up with

A router that aligns your drone and soil streams by event time, a checker for both streams, and measurements of how the window, clock skew and stream length change what gets fused.

Skills you'll practice:
- Normalizing sensor readings into a shared format
- Aligning two streams by event time within a window
- Routing records to a fused path or a fallback path
- Serializing records with Protobuf for an inference service
- Validating stream records before they reach the pipeline
- Measuring alignment and latency before changing the design

## Before production

This playbook runs on 8 minutes of synthetic data with a mock model. Before you run something like it for real:

1. **Serve the fallback queue.** `fusion_router.py` writes 799 of the 1,000 frames to `inference_queue_vision_only.jsonl`, and nothing reads it: only fused records reach `inference_client.py`. Send vision-only records to a vision-only model, and count them. *Chapter 7, "Inference Routing" (page 224).*
2. **Size the window from the sensors.** Soil readings arrive about every 4 s per plot, so the 500 ms window fuses 20% of frames; 5 s fuses 88% ([Try this 1](#try-this)). The router also matches readings from after the frame, which in a live stream means waiting for them. Decide how old a reading may be, and whether to wait. *Chapter 7, "Event-Time Alignment" (page 218); Chapter 7, "Windowed Fusion" (page 224).*
3. **Watch the clocks.** With the soil clocks 1 s off, the fused share barely moves (16% against 20%), but 161 of 162 fused records get the wrong reading ([Try this 2](#try-this)). Track `fusion_gap_ms` per sensor over time, and sync the device clocks. *Chapter 7, "Drift Types, Detection, and Engineering Response" (page 229).*
4. **Make fusion scale with the stream.** `fuse_and_route_data` compares every frame with every reading of its plot: 63.7 s for 16 copies of the sample against 0.58 s with a sorted lookup ([Try this 3](#try-this)). A streaming join keeps only the recent readings per plot in state. *Chapter 7, "Tuning the Pipeline for Production" (page 227).*
5. **Stream instead of batch.** Each step reads a whole file and writes a whole file, and inference sends one request at a time: 201 requests took 13.3 s against the mock. A live router needs a queue between steps, a limit on how far it can fall behind, and a fallback when it does. *Chapter 7, "Back-Pressure Control" (page 225).*
6. **Validate readings where they enter.** `preprocess.py` takes the first run of digits in a value, so `-15 mV` becomes 15 and `1.7 V` becomes 1, then clips both to the calibration range without a message. `make check-data` catches these on files; check at ingestion too. *Chapter 7, "Modality-Specific Preprocessing" (page 223); Chapter 4, "Validation, Transformation, Observability, and Annotation Across Modalities" (page 119).*
7. **Replace the mocks.** The embeddings are random vectors and the inference client returns a random action, so the actions and confidences say nothing. `PredictionRequest` and `PredictionResponse` in `fused_record.proto` are not used yet; a real service would take them over gRPC. *Chapter 10, "The Inference Framework: Modal Contracts" (page 372).*

## What it costs

| Where you run it | Cost |
|---|---|
| Your machine | $0. Everything runs locally: no API keys, no paid services. About 100 MB of disk, most of it the Python environment. |
| A GitHub Codespace (2 cores, 8 GB, the default size; the repo asks for nothing larger) | Estimated $0.18 per hour at GitHub's list price (November 2026). A free personal account includes 120 core-hours a month, about 60 hours on this machine. In CI, `make run` took 13 s in a freshly built devcontainer. |

## How it works

This playbook delivers a locally executable prototype. Each section of the chapter pairs it with a real-world translation explaining how the same logic scales in production.

The pipeline has three steps, plus optional orchestration:

1. **Preprocessing** (`preprocess.py`) extracts volumetric water content and pH from soil telemetry (mV readings) and normalizes them. It also simulates a 256-dimensional embedding per drone frame. The embeddings are **random vectors** standing in for a vision model such as MobileNet; no images are included.
2. **Fusion and routing** (`fusion_router.py`) matches each drone frame to the closest soil reading for the same `plot_id` within 500 ms of event time. Matched records go to the inference queue; unmatched ones go to a vision-only fallback queue.
3. **Inference** (`inference_client.py`) builds a `FusedRecord` Protobuf message (`fused_record.proto`), serializes it, and sends it to a **mock** client. The mock simulates 20–100 ms of server latency and returns a **random** action and confidence that don't depend on the input. Each result logs the action, confidence, entropy and latency.
4. **Orchestration (optional)**: the Airflow DAG `fieldsense_inference_dag.py` runs the three steps in order.

Runs on a laptop CPU in under a minute. No GPU or cloud account required.

## Run it the way the book does

These are the book's commands (pages 256–267), as printed apart from the fixes in [Differences from the printed book](#differences-from-the-printed-book). `make run` runs the same three scripts.

With pip:

```bash
pip install -r requirements.txt     # Python 3.12 or newer
python preprocess.py
python fusion_router.py
python inference_client.py
```

The book's `python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. fused_record.proto` (page 264) also works; it regenerates the stubs, which are already committed.

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
| Protobuf stubs regenerated (`make proto`); `grpcio-tools` pinned in `requirements.txt` | Match the pinned protobuf and grpcio; the protoc command needs `grpcio-tools` | 264 |
| The mock client receives serialized bytes (`SerializeToString()`) | Matches what the text describes | n/a |
| README file names corrected: the data folder is `raw data/` (with a space) and the soil file is `soilSensorReading.jsonl` | The old README and the book listed `raw-data/` and `soilSensorReadings.jsonl` | 257 |

Notes on the chapter text:
- The header contract names the key `field_id` (p. 221). The code and the rest of the chapter use `plot_id`.
- The chapter introduction mentions a frame every 33 ms (p. 217). The sample data and pipeline run at about 2 Hz (a frame about every 500 ms), with soil readings at 1 Hz.

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
scripts/summarize.py         # make summary
scripts/load_streams.py      # make check-data / make load: your own streams
experiments/                 # make try-window, try-skew, try-scale
runs/                        # Created by make load
tests/test_smoke.py          # make smoke
tests/test_own_data.py       # Checks for scripts/load_streams.py
```

If this playbook helped you, a star helps other readers find it.

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