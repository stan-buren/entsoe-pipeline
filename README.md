# ENTSO-E Data Pipeline (`entsoe-pipeline`)

An enterprise-grade, high-performance data engineering pipeline designed to ingest, process, and analyze power grid transmission data from the European Network of Transmission System Operators for Electricity (ENTSO-E).

## 🚀 Architecture Overview

This pipeline is built with a focus on local portability, robust schema enforcement, and rapid batch processing. It transitions from legacy exploration code into a production pipeline:

- **Core Engine:** Apache Spark (PySpark) for heavy transformations & DuckDB for fast local analytical storage.
- **Strict Linting & Quality:** Exhaustive Ruff formatting and static checking, enforcing strict PEP-8 standards.
- **Config Management:** Centralized configuration system using YAML templates (`config_env_example/`) and active environments (`config_env/`) with automated schema validation.

## 🛠️ Tech Stack

- **Python:** `3.14`
- **Processing:** PySpark `4.0.0`, DuckDB `1.5.2`
- **Data Source:** `entsoe-py` (Official ENTSO-E API client wrapper)
- **Validation:** `PyYAML`, `pytest` (with high-performance `pytest-xdist` parallel execution)
- **Task Automation:** `just` (utility runner via `Justfile`)

## 📥 Getting Started

### 1. Initialize Configuration Templates
Generate your active configuration schemas from the public templates:
```bash
just init-config
```
*(This sets up your localized ports and database volumes without exposing credentials in Git).*

### 2. Install Project Tools & Virtual Env
Using the `uv` toolchain, bootstrap your dependencies:
```bash
uv sync --all-groups
```

### 3. Run Quality Gates & Tests
Validate workspace integrity, paths, and metadata schema compliance:
```bash
just test
```
