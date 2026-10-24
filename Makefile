.PHONY: smoke proto

# End-to-end check on the sample data (CPU, no network calls after install).
smoke:
	uv sync --frozen
	uv run --frozen pytest -q tests/test_smoke.py

# Regenerate fused_record_pb2*.py after editing fused_record.proto.
proto:
	uv run --frozen python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. fused_record.proto
