.PHONY: setup run smoke proto clean

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

# End-to-end check on the sample data (CPU, no network calls after install).
smoke:
	uv sync --frozen
	uv run --frozen pytest -q tests/test_smoke.py

# Regenerate fused_record_pb2*.py after editing fused_record.proto.
proto:
	uv run --frozen python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. fused_record.proto

# Remove generated files. The sample data in "raw data/" is kept.
clean:
	rm -rf normalized output .pytest_cache
