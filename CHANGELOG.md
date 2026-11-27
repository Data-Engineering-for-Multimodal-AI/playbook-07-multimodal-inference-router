# Changelog

## v1.1.0 (2026-11-26)

Nothing the book shows has changed.

### Added
- `make summary` summarizes a run: fused and vision-only frames, time gaps per plot, and inference
  latency (`scripts/summarize.py`).
- `make check-data DIR=...` and `make load DIR=...`: check your own drone and soil streams (the
  format of `raw data/`) and run the three steps on them in `runs/<folder name>/`
  (`scripts/load_streams.py`). Tests in `tests/test_own_data.py`.
- Three measured experiments: `make try-window`, `make try-skew`, `make try-scale` (`experiments/`).
- README: numbered Run it steps, time tiers, Try this, Use your own data, What you end up with,
  Before production, What it costs.
- CI: runs the Run it steps with checks on their output, the three experiments, the own-data
  tests, and prints the time to first output in a clean devcontainer.
- `make setup`, `make run` and `make clean`. `make run` runs `preprocess.py`, `fusion_router.py`
  and `inference_client.py` on the sample data in `raw data/`. `make smoke` and `make proto` are
  unchanged.
- `.devcontainer/` so the repo opens in GitHub Codespaces with dependencies installed.
- CI: a weekly scheduled run, a `make run` step, and a job that builds the devcontainer and runs
  `make run` inside it.
- `DATA_SOURCES.md`: the datasets and models this playbook uses, with their licenses and citations.
- `make run` writes `.playbook-done` when it passes (ignored by git). `make card` in the
  organization's `.github` repository reads these files and draws a completion card.

### Changed
- README: "What you'll build" is now "How it works"; "Quick start" is now "Run it the way the
  book does", with its content unchanged. The first-edition note points to it.
- `make clean` also deletes `runs/`, the output of `make load`.
- README opening: a title that says what you'll do, three sentences on why, the example and what you'll do, then the data engineering problem and what you'll work with.
- Book page numbers now match the printed book (they were Early Release page numbers).
- README: a header image (light and dark), badges for CI, Python, license and Codespaces, a diagram at
  the top of "How it works", and a footer that links the book, all playbooks, and the previous and
  next playbook.
- README: a Troubleshooting section with three common problems and their fixes.
- Dependencies: security patch releases (setuptools 84.0.0 to 84.1.0).

## 2026.10.1 (2026-10-27)

Checked against the book (Early Release, pages 260–271).

### Fixed
- The book's `python -m grpc_tools.protoc ...` (page 268) failed after `pip install -r
  requirements.txt`: the 2026.10 update had moved `grpcio-tools` to the development dependencies. It
  is back in `requirements.txt` (1.81.1, the version the stubs were generated with). CI runs it and
  checks the stubs come out unchanged.

### Changed
- README: page numbers; the protoc command; book pages in the differences table.

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
