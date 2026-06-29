---
trigger: always_on
---

# ENTSO-E Metadata Pipeline Software Architecture

This document describes the layering, folder structure, and Clean Architecture principles of the ENTSO-E metadata pipeline codebase.

## 1. Directory Structure

```bash
.
├── config/                # Centralized global configurations & schemas overrides
├── config_env/            # Environment-specific configuration files (active)
├── config_env_example/    # Templates/Examples for environment configs
├── dags/                  # Kestra workflow definitions (Highest orchestration level)
├── jobs/                  # Job scripts coordinating workflows (Staging, Landing, Marts)
├── tests/                 # Unit, integration, and pre-commit test suites
└── src/
    └── entsoe_pipeline/   # Main python library package (Source)
        ├── api/           # FMS client connections & rate limiting
        ├── config/        # Typed config loader adapters & interfaces (Ports/Adapters)
        ├── fms_metadata/  # FTP Metadata Crawler and catalog generation
        ├── io/            # S3 I/O operations and landing synchronization
        ├── lakehouse/     # Silver/Staging ETL and Iceberg writes
        ├── logger/        # Unified logger configs, facades, and exceptions
        ├── spark/         # PySpark session builder configurations
        └── vendor_patches/# Workarounds for external libraries (e.g. entsoe-py)
```

## 2. Hierarchical Levels & Dependencies

To prevent circular imports, code coupling, and maintain clean separation of concerns, the codebase is structured into five distinct levels:

### Level 0: Declarative Configurations (System Settings Bootstrap)
- **Location:** [config/](file:///home/donald_trump/developer/entsoe-pipeline/config/) (global settings) and [config_env/](file:///home/donald_trump/developer/entsoe-pipeline/config_env/) (environment-specific overrides).
- **Description:** Centralized, human-readable YAML configurations defining core pipeline parameters, business logic rules, and environments. This acts as the Single Source of Truth (SSOT), preventing configuration values from being hardcoded anywhere in the scripts (consistent with ADR-001).
- **Roles & Scope:**
  - `config/`: Configurations identical across all environments (e.g., API limits, classification mapping templates, schema overrides).
  - `config_env/`: Environment-specific definitions (e.g., active S3 buckets, current downloading domains, rate limit constraints).
  - **Rule:** This layer is loaded at pipeline bootstrap. The configs are parsed and validated by the `config/` library module, then injected down the hierarchy into Core modules, Adapters, and Jobs.

### Level 1: Core Modules (Inside - Domain Core)
- **Location:** Any directory named `core/` inside a library module (e.g., `src/entsoe_pipeline/config/core/`, `src/entsoe_pipeline/lakehouse/core/`).
- **Description:** Contains pure domain logic, immutable dataclasses, mathematical/string operations, and Spark DataFrame transformations.
- **Rule:** Core modules know nothing about the outside world. They must **never** import from high-level adapters, config loaders, external storage connectors, or orchestration layers. All dependencies must be injected via arguments (Dependency Inversion).

### Level 2: Source Package (Inside/Outside - Ports & Adapters)
- **Location:** The `src/entsoe_pipeline/` modules outside of `core/` subdirectories.
- **Description:** Implement ports (interfaces) and adapters to external systems (S3 client initialization, FTP client, logging observability facades).
- **Sub-package Roles:**
  - `config/`: Foundations. Loads static configuration singletons from files. Low-level source dependency.
  - `logger/`: System-wide logging and exceptions. Highly decoupled, can be imported globally.
  - `preflight/`: Diagnostic tests executed at job startup. They check credentials and endpoints, failing the job fast if the environment is misconfigured.
  - `api/`: Raw API connections (crawlers and client throttle wrappers). Completely independent, doesn't import other domains.
  - `io/`: Manages S3 client reads, writes, and FTP sync processes.
  - `spark/`: Shared SparkSession configuration and JAR dependency resolution. Does **not** execute jobs.
  - `vendor_patches/`: Temporary patches for third-party libraries (e.g., `entsoe-py`). These will be removed once corresponding upstream PRs are merged.

### Level 3: Job Scripts (Outside - Application Executors)
- **Location:** The `jobs/` directory (e.g. `jobs/staging/landing/`, `jobs/staging/lakehouse/`).
- **Description:** Executable scripts containing `main()` entrypoints. They orchestrate high-level flows by calling libraries, configuring logs, and injecting preflight diagnostic tests. They contain zero path-parsing, grouping, or data-transformation calculations.

### Level 4: Orchestration DAGs (Highest level - Workflow Scheduling)
- **Location:** The `dags/` directory.
- **Description:** Declarative Kestra workflows defining cron triggers, job schedules, task order, and environment switches.

## 3. Quality Gate (Source Import Checks)

We strictly enforce clean imports and code organization standards using the automated test suite `tests/test_source_imports.py`.

### Import Rules:
1. **No mid-file imports:** All imports must be declared at the module level (the very top of the file). Local imports inside functions are prohibited as they mask circular import anti-patterns.
2. **Whitelisting:** Genuine mid-file exceptions (such as lazy-loading heavy Spark/boto3 libraries or raising custom exceptions) must be explicitly whitelisted in `ALLOWED_MID_FILE_IMPORTS`.