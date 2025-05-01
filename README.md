# FieldSense Multimodal Inference Router

A real-time multimodal inference pipeline for precision agriculture that processes and fuses drone imagery with soil telemetry data to make field-level decisions.

## Project Overview

FieldSense is a multimodal AI system for precision agriculture that ingests asynchronous data streams from drones (image frames) and soil probes (telemetry), aligns them using event-time fusion, and routes the processed data to an inference service for timely agricultural recommendations.

## Pipeline Architecture

The inference router performs three main stages:

### 1. Preprocessing

- **Drone Imagery**: Simulates 256-dimensional embeddings for drone images
- **Soil Telemetry**: Normalizes volumetric water content from mV to [0.0, 1.0] scale and converts soil pH voltage from mV to pH scale (5.5-7.5)
- **Metadata Preservation**: Maintains essential metadata like timestamps and plot identifiers

### 2. Fusion and Routing

- **Windowed Event-Time Fusion**: Joins records from different sensors when they share the same plot_id and their timestamps are within ±500ms
- **Fusion Gap Tracking**: Computes the time difference between matched records for quality assessment
- **Dual-Path Routing**:
  - Fused records (sensor fusion < 500ms) → inference_queue_per_event
  - Vision-only records (no matching soil data) → inference_queue_vision_only

### 3. Inference Simulation

- **Protocol Buffer Serialization**: Converts fused records to a standardized message format
- **Mock Inference Service**: Simulates prediction latency, confidence scores, and agricultural actions
- **Observability**: Logs comprehensive metrics including total latency, server latency, and prediction entropy

### 4. DAG Orchestration

- **Airflow Integration**: Formalizes task dependencies using Apache Airflow
- **Pipeline Automation**: Enables scheduled or manually triggered execution
- **Maintainable Workflow**: Clearly defined stages with proper dependency management

## Pipeline Data Flow

```
Raw Data → Preprocessing → Fusion & Routing → Inference → Results
  ↓             ↓               ↓                ↓           ↓
Drone Images   Normalized    Event-Time       Protocol     Action
Soil Readings    Data          Matching       Buffers    Recommendations
```

## Project Structure

- `preprocess.py`: Normalizes drone image metadata and soil sensor readings
- `fusion_router.py`: Performs event-time aligned fusion and routing
- `inference_client.py`: Serializes records and handles inference requests
- `fused_record.proto`: Protocol Buffer schema for serialization
- `fieldsense_inference_dag.py`: Airflow DAG for workflow orchestration

## Usage

### Prerequisites

- Python 3.8+
- Apache Airflow 3.0.0+
- Protocol Buffers compiler (protoc)

### Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/fieldsense-inference-router.git
   cd fieldsense-inference-router
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Generate Python bindings from Protocol Buffer schema:
   ```
   protoc -I. --python_out=. fused_record.proto
   ```

### Running the Pipeline

#### Using Airflow

1. Copy the DAG file to your Airflow DAGs directory:
   ```
   cp fieldsense_inference_dag.py ~/airflow/dags/
   ```

2. Trigger the DAG via Airflow UI or CLI:
   ```
   airflow dags trigger fieldsense_inference_router
   ```

#### Manual Execution

Run each component separately:

```
python preprocess.py
python fusion_router.py
python inference_client.py
```

## License

MIT License

Copyright (c) 2025 Data Engineering for Multimodal AI

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