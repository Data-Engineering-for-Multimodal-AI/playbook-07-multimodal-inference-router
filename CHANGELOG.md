# Changelog

## 2026.10 (2026-10-12): 2026 maintenance update

The printed version is tagged `first-edition`.

### Fixed
- The Airflow DAG runs. Tasks run with `cwd=FIELDSENSE_HOME` (default: the DAG file's real folder) instead of `python /opt/fieldsense/...`, which failed on any machine without that folder and also broke the scripts' relative paths. `BashOperator` is imported from `airflow.providers.standard.operators.bash` (Airflow 3).
- Protobuf stubs regenerated with grpcio-tools 1.81.1 (protobuf 6.33). The old stubs needed protobuf ≥ 5.29 and grpcio ≥ 1.70, while the requirements allowed much older versions.
- The mock inference client receives the serialized `FusedRecord` bytes, as the docstring describes.

### Changed
- Airflow is optional: `requirements.txt` holds only numpy, tqdm, protobuf and grpcio (pinned from `uv.lock`, Python 3.12+). Airflow is in `requirements-airflow.txt`, installed with Airflow 3.3.2's constraints file. Core pins match that file.
- `preprocess.py` and `inference_client.py` take `--seed` (default 42).
- README follows the standard playbook layout and says plainly that embeddings are random vectors and predictions come from a random mock. File names are corrected.

### Added
- `pyproject.toml`, `uv.lock`, `requirements-airflow.txt`, `.env.example`.
- `tests/test_smoke.py`, `make smoke`, `make proto`; GitHub Actions smoke test on Python 3.12/3.13 plus one Airflow DAG run.
