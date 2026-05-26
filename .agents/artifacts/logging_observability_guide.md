# Python Logging and Observability Guide
*(In accordance with Enterprise Data Engineering Best Practices)*

This guide establishes the architectural standards for operational logging, structured output formats, exception handling, and custom error hierarchies within the ENTSO-E data pipeline.

---

## 1. The Dual Nature of Logging in Data Engineering

In data platforms, "logging" refers to two distinct but equally critical concepts:

1.  **Operational / Application Logging**: Emitted by software components (Python, Spark, Airflow) describing *runtime system behaviors, successes, and errors*.
2.  **Commit / Write-Ahead Logging (WAL)**: An append-only structural data log used by transactional databases (PostgreSQL) and distributed event streams (Apache Kafka) for *durability, transactional guarantees, and real-time CDC (Change Data Capture)*.

*This guide strictly covers **Operational/Application Logging** standards.*

---

## 2. Exceptions vs. Loggers: Control Flow vs. Observability

A common anti-pattern is using exceptions to handle observability, or logs to handle control flow. They must be decoupled:

*   **Exceptions (`raise ValueError`)**: Used strictly for **Control Flow**. If a fatal state is reached (e.g., missing API credentials, unreadable configuration), you *must* halt execution immediately. Exceptions stop the engine when it is unsafe to proceed.
*   **Loggers (`logger.error`)**: Used strictly for **Observability (Audit Trails)**. Loggers record chronological sequences. If a fatal crash occurs, loggers capture the system state, inputs, and stack trace before the process terminates. If a non-fatal error occurs (e.g., one malformed row out of a million), we catch the exception and log a warning/error *to prevent silent failures* while allowing the pipeline to proceed.

---

## 3. The Hierarchy of Severity Levels

Operational logs must be categorized into standard logging levels to enable efficient filtering, querying, and operational paging (alerting):

| Level | Severity | Production Use Case | Operational Impact |
| :--- | :--- | :--- | :--- |
| **`DEBUG`** | Low | Fine-grained, verbose variables or query details for active testing. | Disabled in PROD to prevent disk bloat. |
| **`INFO`** | Normal | High-level milestones: task starting/finishing, records processed count, storage commits. | Retained for chronological audit trails. |
| **`WARNING`** | Moderate | Recoverable glitches: API retries, deprecated configurations, or minor data quality warnings. | Monitored to identify future risks. |
| **`ERROR`** | High | Serious operation failure: single task failure, row validation drop, but overall pipeline runs. | Triggers non-blocking system warnings. |
| **`CRITICAL`** | Fatal | Pipeline crash, data store unreachable, fatal authentication failure. | Triggers immediate paging alerts to on-call engineers. |

---

## 4. Operational Best Practices (The Rules)

### Rule A: The Scoped Logger Pattern (Never Hijack Root)
Do **not** configure the global root logger (`logging.basicConfig`) inside libraries or pipelines. Configuring the root logger attaches your handlers and formats to third-party modules. This results in connection pools (like `urllib3`, `boto3`, `requests`) dumping hundreds of verbose debug lines into your console, creating massive log pollution.

Instead, always obtain a logger scoped to your package namespace (`entsoe_pipeline`) and configure it locally, setting `logger.propagate = False`:

```python
# GOOD: Scoped and isolated configuration
logger = logging.getLogger("entsoe_pipeline")
logger.setLevel(logging.INFO)
logger.propagate = False
```

```python
# BAD: Hijacks all imported libraries
logging.basicConfig(level=logging.INFO)
```

---

### Rule B: The Golden Rule of String Interpolation (No f-strings in Logs!)
Never construct your log strings using Python f-strings or manual concatenations inside log arguments. Always pass variable arguments as subsequent parameters using `%` placeholder format strings:

```python
# YES: Highly efficient, template-preserving
logger.info("Successfully ingested %d records from dataset %s", records_count, dataset_name)
```

```python
# NO: Expensive, makes template matching impossible
logger.info(f"Successfully ingested {records_count} records from dataset {dataset_name}")
```

#### Why is this critical?
1.  **CPU & Memory Efficiency**: f-strings are evaluated by Python *before* the logger is called. If your log level is set to `WARNING`, and you emit an `INFO` log with a heavy f-string, Python still spends CPU cycles constructing that string only for the logger to immediately discard it. Passing arguments separately guarantees the string is *only* evaluated if the severity level warrants output.
2.  **Centralized Template Grouping**: Centralized log search tools (Elasticsearch, Grafana Loki) collect raw, unexpanded pattern strings (like `"Successfully ingested %d records..."`) as unique fields. This allows automated log analyzers to instantly group billions of unique logs into a single queryable chart template regardless of dynamic numeric values.

---

### Rule C: Structured JSON Logging in Containerized Pods
For local development, plain text logs are acceptable. However, for production cloud environments running containerized pipelines (Docker, Kubernetes), logs must be output as single-line JSON structures directly to **Standard Output (`stdout`)**:

*   **Stdout Streaming**: Container engines natively scrape standard output streams. Local file logging on ephemeral disks will cause immediate data loss upon container termination or crashes.
*   **JSON Serialization**: Structured JSON logs turn every log entry into a queryable database document. Rather than writing complex, fragile regex parsers, search engines can instantly parse keys:

```json
{"timestamp": "2026-05-26 14:08:45", "logger": "entsoe_pipeline.api.ls_fms", "level": "INFO", "message": "Successfully fetched 76 remote folders", "dataset": "Balancing"}
```

---

### Rule D: Capturing Stack Trace Forensic Evidence (`logger.exception`)
Whenever catching a fatal or serious exception in a `try/except` block, always record it using the `.exception()` method rather than standard `.error()`:

```python
# YES: Automatically attaches the full stack traceback
try:
    client.connect()
except requests.RequestException as e:
    logger.exception("Keycloak OAuth2 token retrieval failed: %s", e)
    raise EntsoeConnectionError(f"API token error: {e}") from e
```

`logger.exception` automatically grabs `sys.exc_info` and formats the entire traceback, recording the exact line numbers and intermediate variables, making forensic debugging effortless.

---

### Rule E: Custom Exceptions Hierarchy
Never let raw, generic standard exceptions (like `ValueError` or `RuntimeError`) bubble up unmapped. Define localized, typed custom exceptions inside `exceptions.py` that inherit from a central base class (`EntsoePipelineError`):

*   **EntsoePipelineError**: Central operational base.
*   **EntsoeConfigurationError**: Mapped for missing env credentials, invalid YAML formats.
*   **EntsoeConnectionError**: Network timeouts, token auth rejections.
*   **EntsoeApiError**: Unexpected JSON payloads or remote endpoint status errors.
*   **EntsoeDataValidationError**: Non-conforming schema shapes, malformed headers.

This allows orchestrators (Airflow, Pytest fixtures) to easily implement selective retry policies or fail gracefully when catching specific network domains without crashing on configuration bugs.
