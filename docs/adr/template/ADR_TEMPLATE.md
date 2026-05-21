# ADR-[ADR #]: [Concise Decision Title]

## Metadata

**Status:** [Proposed | Accepted | Rejected | Deprecated | Superseded by ADR-XXXX]
**Version/Date:** vX.Y / YYYY-MM-DD

## Title

[Full, Descriptive Title of the Decision]

## Description

[1–2 sentence executive summary]

## Context
<!-- 
This section describes the "why" behind the decision. 
- What is the problem or need being addressed?
- What is the current state of the architecture?
- What are the technical, business, or operational forces influencing this decision?
- Include data, metrics, or analysis that supports the need for this change.
-->
[Problem, pipelines, constraints, data growth metrics, prior architectural decisions]

## Decision Drivers

- [Driver 1]
- [Driver 2]
- [Regulatory/Policy] (e.g., EU AI Act, internal policies)

## Alternatives

- A: [desc] — Pros / Cons
- B: [desc] — Pros / Cons
- C: [desc] — Pros / Cons

### Decision Framework

<!-- 
Use a weighted scoring matrix to provide a quantitative justification for the decision. Adjust criteria and weights based on project priorities.
-->

| Model / Option         | [Criterion 1 (e.g., Solution Leverage)] (Weight: X%) | [Criterion 2 (e.g., Application Value)] (Weight: Y%) | [Criterion 3 (e.g., Maintenance)] (Weight: Z%) | [Criterion 4 (e.g., Adaptability)] (Weight: W%) | Total Score | Decision      |
| ---------------------- | ---------------------------------------------------- | ---------------------------------------------------- | ---------------------------------------------- | ----------------------------------------------- | ----------- | ------------- |
| **[Chosen Solution]**  | [Score]                                              | [Score]                                              | [Score]                                        | [Score]                                         | **[Score]** | ✅ **Selected** |
| [Alternative Option A] | [Score]                                              | [Score]                                              | [Score]                                        | [Score]                                         | [Score]     | Rejected      |
| [Alternative Option B] | [Score]                                              | [Score]                                              | [Score]                                        | [Score]                                         | [Score]     | Rejected      |

## Decision

<!-- 
State the decision clearly and unambiguously. This should be a direct statement of the chosen path.
-->
We will adopt **[Chosen Solution]** to address [the problem]. This involves using **[Specific Library/Pattern/Component]** configured with **[Key Parameters]**. This decision supersedes **[any previous ADRs or decisions, if applicable]**.

## High-Level Architecture

[Mermaid Diagram or textual description of the architecture]

## Related Requirements

<!-- 
This section outlines the specific requirements this ADR addresses. Be brief and clear.
-->

### Functional Requirements

- **FR-1:** [The system must be able to...]
- **FR-2:** [Users must have the ability to...]

### Non-Functional Requirements

- **NFR-1:** **(Data Reliability)** [The solution must prevent partial writes and ensure transactional integrity (ACID).]
- **NFR-2:** **(Maintainability)** [The config must be fully separated from PySpark script logic.]
- **NFR-3:** **(Extensibility)** [Schema migrations must occur without rebuilding the target tables.]

### Performance Requirements

- **PR-1:** [Throughput must handle at least X records/sec during peak ingestion periods.]
- **PR-2:** [Spark executor memory utilization must not exceed X GB per node under standard workload.]

### Integration Requirements

- **IR-1:** [The system must natively connect to the target catalog (e.g., Iceberg REST, Hive, Glue).]
- **IR-2:** [All Spark dependencies (JARs) must resolve dynamically via package management without manual cluster installation.]

## Related Decisions

<!-- 
Link to other ADRs that are connected to this one. This helps in understanding the broader architectural context.
-->
- **ADR-[XXX]** ([Title of related ADR]): [Briefly explain the relationship, e.g., "This decision builds upon the core architecture defined in ADR-XXX."]
- **ADR-[YYY]** ([Title of related ADR]): [e.g., "The component chosen here will be configured via the `Settings` singleton established in ADR-YYY."]

## Design

<!-- 
This is the "how" section. Provide enough detail for another engineer to understand and implement the decision.
-->

### Architecture Overview

<!-- Use a Mermaid diagram to visualize the new pipeline architecture, data transformations, or catalog mapping. -->

### Implementation Details

<!-- 
Provide code snippets to illustrate the implementation. Show "before" and "after" if it helps clarify the change. Be specific about file paths and function names. Keep concise here with enough detail to implement the code in full correctly per the ADR. Full file should aim for ~600 lines max so keep that in mind.
-->
**In `src/entsoe/folder_name/script_name.py`:**

```python
# Brief comment explaining the code snippet
from some_library import ChosenComponent
from project.core import Settings

def setup_new_component():
    """This function initializes and configures the chosen component."""
    component = ChosenComponent(
        parameter=Settings.some_value,
        another_parameter=True
    )
    return component
```

### Configuration

<!-- Detail any new configuration files, environment profiles, or connection strings. -->
**In `config/config_folder/config_file.yaml` or `.env`:**

```env
# New environment variable for the component
COMPONENT_API_KEY="your-key-here"
COMPONENT_TIMEOUT=60
```

or

```yaml
# New yaml config for the component
spark:
  executor:
    memory: "2g"
    cores: 2
  catalog:
    uri: "http://localhost:8181"
```

## Testing

<!-- 
Describe the strategy for testing this new architecture. Include code snippets for tests where appropriate. Keep as skeleton code to give enough detail/comments to implement the tests but do not write the full test suites here. Make sure to mention the `pytest` framework, mock dependencies, and the async/await patterns.  Full file should aim for ~600 lines max so keep that in mind.
-->
**In `tests/test_component.py`:**

```python
import pytest
from project.component import new_functionality

@pytest.mark.asyncio
async def test_component_performance():
    """Verify that the new component meets performance requirements."""
    # Test setup
    start_time = time.monotonic()
    result = await new_functionality("test input")
    duration = time.monotonic() - start_time
    
    # Assertions
    assert result is not None
    assert duration < 0.05 # 50ms latency target

def test_configuration_toggle():
    """Verify that a feature can be toggled via settings."""
    # Test logic
    pass
```

## Consequences

<!-- 
Analyze the results and impact of the decision.
-->

### Positive Outcomes

- [e.g., "Reduces storage costs by 40% through optimized Parquet partitioning and Z-Ordering."]
- [e.g., "Improves data freshness by enabling near real-time ingestion via streaming sources."]
- [e.g., "Standardizes data quality checks by integrating automated Great Expectations suites into the pipeline."]
- [e.g., "Simplifies multi-environment deployments by abstracting catalog connections via environment-specific profiles."]
- [e.g., "Reduces technical debt by eliminating manual schema evolution scripts in favor of native Iceberg capabilities."]

### Negative Consequences / Trade-offs

- [e.g., "Increases S3 API operation costs due to high frequency of file commits in small-batch streams."]
- [e.g., "Requires specialized knowledge of Delta/Iceberg internals for troubleshooting performance regressions."]
- [e.g., "Introduces strict schema enforcement, which may break downstream jobs if upstream changes are not backward compatible."]
- [e.g., "Conflicts with legacy Hive Metastore locking mechanisms, requiring transition to REST catalog."]
- [e.g., "Higher initial implementation complexity compared to static CSV-based loading."]

### Ongoing Maintenance & Considerations

- [e.g., "Schedule automated maintenance tasks (expire_snapshots, rewrite_data_files) to optimize storage footprint."]
- [e.g., "Monitor partition pruning efficiency in Spark UI to prevent full table scans."]
- [e.g., "Audit catalog connection secrets rotation frequency."]
- [e.g., "Track ingestion lag metrics in Grafana; alert if latency exceeds SLA."]
- [e.g., "Ensure data lineage tags are updated in the Data Catalog during schema changes."]

### Dependencies

- **Infrastructure**: [e.g., `AWS Glue Data Catalog`, `SeaweedFS`.]
- **Data Frameworks**: [e.g., `Apache Iceberg >= 1.4.0`, `PySpark >= 4.0.0`.]
- **Removed**: [e.g., `AWS Athena` manual DDL scripts (replaced by automated schema evolution).]

## References

- [e.g., Apache Iceberg Documentation](https://iceberg.apache.org/) - Detailed specifications for table maintenance and schema evolution
- [e.g., Spark Performance Tuning Guide](https://spark.apache.org/docs/latest/tuning.html) - Best practices for cluster memory and executor management
- [e.g., Data Mesh Principles](https://martinfowler.com/articles/data-mesh-principles.html) - Foundational patterns for decentralized data ownership used in this design
- [e.g., Parquet File Format Specifications](https://parquet.apache.org/) - Technical insights into file-level performance optimization
- [e.g., ADR-002: Bronze/Silver/Gold Architecture](docs/adrs/ADR-002-data-layering.md) - Dependency relationship regarding data lifecycle management

## Changelog

- **[Version #] ([YYYY-MM-DD])**: [Description of the change. e.g., "Initial accepted version."]
- **[Version #] ([YYYY-MM-DD])**: [e.g., "Updated code snippets to align with ADR-XXX's refactoring. Added performance benchmark results."]
