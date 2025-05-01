# Building a Real-Time Multimodal Inference Router

This project implements a real-time multimodal inference router for precision agriculture, as described in Chapter 7 of *Data Engineering for Multimodal AI* (2025). The pipeline ingests asynchronous data from drone-mounted cameras and soil sensors, performs windowed temporal fusion, routes records to inference modes, and logs observability signals for drift detection and retraining.

## Project Overview and Usage Notes

This playbook delivers a high-fidelity, locally executable prototype of a real-time multimodal inference router. While the implementation is optimized for development and simulation, each section includes an accompanying real-world translation explaining how the same logic would scale across production-grade systems. You are encouraged to treat this project as a working reference architecture, and to study the translation notes in each step to understand how these components deploy in enterprise settings.

## Estimated Time Required

This is a lightweight project suitable for laptops or dev containers. On a standard machine:

- Setup: ~5 minutes (including installing dependencies)
- Full pipeline execution (preprocessing → fusion → inference): ~30 seconds to 1 minute
- No GPU or cloud account required

## Project Structure

```
preprocess.py                # Normalizes raw drone and soil sensor data
fusion_router.py             # Performs event-time windowed fusion and routing
inference_client.py          # Serializes fused records, simulates gRPC inference
fused_record.proto           # Protobuf schema for fused records and prediction responses
fieldsense_inference_dag.py  # Airflow DAG orchestrating the pipeline
raw-data/                    # Raw input files (droneImageMetadata.jsonl, soilSensorReadings.jsonl)
normalized/                  # Preprocessed sensor and image embedding data
output/                      # Fused records, vision-only queue, and inference results
```

## Prerequisites

To run the project locally, you'll need:

- Python 3.8 or newer
- pip or conda (for dependency management)
- [Apache Airflow](https://airflow.apache.org/) (optional, for DAG orchestration)
- numpy, tqdm, grpcio, protobuf, grpcio-tools

Install dependencies using:

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install numpy tqdm grpcio grpcio-tools protobuf
```

## Pipeline Overview

The inference router performs three stages:

1. **Preprocessing**: Extracts and normalizes volumetric water content and pH from soil telemetry, and simulates 256-dimensional embeddings for drone images.

2. **Fusion and Routing**: Performs windowed event-time fusion between vision and soil streams, routes matched records to an inference queue and unmatched ones to a fallback path.

3. **Inference Simulation**: Serializes fused records into Protobuf messages, simulates prediction latency, entropy, and action decisions, and logs observability data including confidence scores and total latency.

4. **DAG Orchestration**: The Airflow DAG formalizes task dependencies and enables scheduled or triggered execution of the full pipeline.

## Running the Project

To execute the full pipeline manually:

```bash
python preprocess.py
python fusion_router.py
python inference_client.py
```

To run the pipeline via Airflow:
- Place `fieldsense_inference_dag.py` in your Airflow DAGs directory
- Use the Airflow UI or CLI to trigger execution
- Logs and task states will be visible via the Airflow webserver

## License

MIT License

Copyright (c) 2025  
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