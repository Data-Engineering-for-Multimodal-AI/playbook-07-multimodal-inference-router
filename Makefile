.PHONY: setup run summary check-data load try-window try-skew try-scale smoke proto clean

# A bare `make` runs the smoke test, as it did before the uniform targets were added.
.DEFAULT_GOAL := smoke

# Uniform targets for The Playbooks. The book's commands (pip install -r requirements.txt,
# python preprocess.py, python fusion_router.py, python inference_client.py and
# python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. fused_record.proto)
# still work as printed.

# The sample data folder. Its name has a space, as in the book, so it is always quoted.
RAW_DATA := raw data

# Install the locked dependencies into .venv.
setup:
	uv sync --frozen

# Normalize the sample drone and soil data, fuse and route it, then send it to the mock inference
# client. Writes normalized/ and output/.
run: setup
	@test -f "$(RAW_DATA)/droneImageMetadata.jsonl" && test -f "$(RAW_DATA)/soilSensorReading.jsonl"
	uv run --frozen python preprocess.py
	uv run --frozen python fusion_router.py
	uv run --frozen python inference_client.py

# After make run (or make load): what was fused, the time gaps, and inference latency.
#   make summary
#   make summary RUN=runs/my_field
summary:
	uv run --frozen python scripts/summarize.py "$(RUN)"

# Your own streams: droneImageMetadata.jsonl and soilSensorReading.jsonl in DIR, in the format
# of "raw data/". check-data checks every line and writes nothing; load runs the three steps
# in runs/<folder name>/.
#   make check-data DIR=my_field
#   make load DIR=my_field
check-data: setup
	@test -n "$(DIR)" || { echo "Usage: make check-data DIR=path/to/folder"; exit 2; }
	uv run --frozen python scripts/load_streams.py --dir "$(DIR)" --check-only

load: setup
	@test -n "$(DIR)" || { echo "Usage: make load DIR=path/to/folder"; exit 2; }
	uv run --frozen python scripts/load_streams.py --dir "$(DIR)"

# Try this: three measured experiments (see README, "Try this"). They read "raw data/" and
# write nothing.
try-window: setup
	uv run --frozen python experiments/window.py

try-skew: setup
	uv run --frozen python experiments/clock_skew.py

try-scale: setup
	uv run --frozen python experiments/fusion_scale.py $(TIMES)

# End-to-end check on the sample data (CPU, no network calls after install).
smoke:
	uv sync --frozen
	uv run --frozen pytest -q tests/test_smoke.py

# Regenerate fused_record_pb2*.py after editing fused_record.proto.
proto:
	uv run --frozen python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. fused_record.proto

# Remove generated files, including the runs of make load. The sample data in "raw data/" is kept.
clean:
	rm -rf normalized output runs .pytest_cache
