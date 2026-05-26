# Python Module Architecture & Refactoring Guide
*(In accordance with the Google Python Style Guide)*

This guide outlines the architectural design rules for structuring imports, organizing class hierarchies, using modern type annotations, and managing internal visibility. 

---

## 1. Postponed Evaluation of Annotations
Always place the postponed type annotations import at the absolute top of the module if it uses type hints. This enables forward references to classes before they are defined and saves memory by treating annotations as string literals at runtime.

```python
from __future__ import annotations
```

---

## 2. Imports Formatting and Grouping
*(Ref: Section 3.13)*

Imports must always be placed at the top of the file, immediately after the module docstring. They must be grouped from most generic to least generic, separated by a single blank line. Within each group, imports must be sorted **lexicographically (alphabetically)** by their module path.

### The Four Groups
1. `from __future__` imports.
2. Standard library imports.
3. Third-party package imports.
4. Internal repository sub-package imports.

### Formatting Rules
* **Separate Lines**: Each imported package or module must be placed on its own line (except for standard collections or typing helpers).
* **Absolute Imports Only**: Do not use relative imports; always import using the full module path.

```python
# Yes: Beautifully ordered, grouped, and lexicographically sorted
from __future__ import annotations

from dataclasses import dataclass
from functools import cache
import os
from typing import Optional

from dotenv import load_dotenv
import yaml

from my_project.core.paths import CONFIG_DIR
from my_project.core.paths import ENV_FILE
```

```python
# No: Mixed groups, multiple imports on a single line, relative imports
import os, sys
from .paths import CONFIG_DIR
from yaml import safe_load
from __future__ import annotations
```

---

## 3. Class Organization & Domain Grouping
*(Ref: Section 3.16.2)*

Place related classes and functions together in the same module. Unlike other languages (like Java), Python modules should represent cohesive domain areas rather than wrapping exactly one class.

### Recommended Visual Layout
To maximize readability, structure your module using distinct chapters separated by clear visual markers:

1. **Module Docstring**: Outlining purpose and usage.
2. **Imports Block**: Standardized and grouped.
3. **Core Dataclasses & Helpers**: Lower-level parameters, settings, or dataclasses.
4. **Master Config / Core Class**: Integrates component structures.
5. **Infrastructure / Storage Classes**: Auxiliary data systems.
6. **Public API (Accessors)**: Highly visible, decorated entry points (e.g. `@cache` getters).

```python
# =============================================================================
# 1. CORE DATA STRUCTURES & COMPONENT SCHEMAS
# =============================================================================

@dataclass(frozen=True)
class DatabaseCredentials:
    host: str
    port: int


# =============================================================================
# 2. MASTER ORCHESTRATOR / DOMAIN ROOT
# =============================================================================

@dataclass(frozen=True)
class AppConfig:
    db: DatabaseCredentials
    active_env: str


# =============================================================================
# 3. PUBLIC ACCESSORS & ENTRY POINTS
# =============================================================================

@cache
def get_app_config() -> AppConfig:
    """Loads and returns the cached AppConfig singleton."""
    return AppConfig._from_yaml()
```

---

## 4. Internal and Private Names
*(Ref: Sections 3.15, 3.16.2, 3.16.4)*

Python uses visual conventions to designate accessibility. Prepending a single underscore (`_`) signals that an attribute, method, or helper is internal and should not be accessed outside the module or class.

### Visibility Naming Table

| Element | Public | Internal (Protected) |
| :--- | :--- | :--- |
| **Modules** | `my_module.py` | `_my_module.py` |
| **Classes** | `class CoreEngine:` | `class _HelperEngine:` |
| **Methods** | `def load_data(self):` | `def _parse_yaml(cls):` |
| **Global Constants**| `MAX_LIMIT = 100` | `_DEFAULT_PORT = 8080` |
| **Variables** | `user_id = 12` | `_cache_ref = None` |

* **Single Underscore (`_`)**: Highly encouraged for all internal APIs.
* **Double Underscore (`__`)**: Avoid double underscores (dunder) for private member access, as it triggers name-mangling which complicates debugging and testing.

```python
# Yes: Clean internal methods
class ConfigLoader:
    
    @classmethod
    def _parse_yaml(cls) -> dict:
        """Internal helper to safely read disk parameters."""
        pass
```

---

## 5. Documenting Complex Return Types in Public Interfaces
*(Ref: Section 3.8.3)*

When a public API accessor or function returns a complex data structure (such as nested dataclasses or specialized instances), the type annotation alone (`-> PipelineConfig`) does not fully convey the schema to the developer. 

To create self-documenting APIs that instantly pop up with full structure in IDE auto-completion/hover tooltips, map the internal fields of the returned objects directly within the `Returns:` docstring block.

### Key Rules
* **Describe Semantics**: Detail the semantic meaning of every returned attribute.
* **Nested Indentation**: Use hierarchical bulleted sub-lists (indented with 4 spaces) to clearly document nested structures (like sub-dataclasses).
* **Language Consistency**: Ensure all comments and docstring parameters are written in English.

### Formatting Example

```python
@cache
def get_config() -> PipelineConfig:
    """Loads and returns the cached PipelineConfig singleton.

    Returns:
        PipelineConfig: The active loaded pipeline configuration, containing:
            - active_environment (str): The name of the active environment (e.g., 'PROD').
            - env_config (EntsoeEnvConfig): Environment credentials and settings:
                - environment_name (str): Active environment identifier.
                - base_url (str): REST or FMS API entry point URL.
                - token_url (str): Keycloak token acquisition URL.
                - token (Optional[str]): Active API token if injected.
            - limits (RateLimitsConfig): Configured rate limits:
                - standard_api_requests_per_minute (int): Standard API call limit.
                - ban_duration_seconds (int): Penalty cooldown time on limit violations.
    """
    return PipelineConfig._from_yaml()
```

---

## 6. Composed Master Configuration & Delegation Pattern
*(Ref: Section 3.15)*

To prevent redundant disk I/O, simplify testing, and maintain a clean Developer Experience (DX), use a composed master configuration design paired with delegated getter functions for granular sub-configurations.

### Core Architectural Rules

1. **The Composed Master Config (The SSOT)**:
   * Design a single master `PipelineConfig` dataclass that houses all sub-configuration dataclasses (`buckets`, `region`, `ports`) as attributes.
   * Provide exactly **one** public entry point getter decorated with `@cache` (`get_config()`), which loads and parses the entire configuration hierarchy in a single pass.
   * This master getter acts as our Single Source of Truth (SSOT) and cache boundary.

2. **Caller Flexibility & Granular Slicing**:
   * **Direct Master Config Import**: When a service or orchestrator requires access to multiple areas of the pipeline, importing the master config `get_config()` is clean and highly recommended.
   * **Targeted Sub-Config Getters**: If a small component, utility, or worker script only requires a tiny slice of the configuration (e.g. only bucket settings or only port bindings) and importing the entire master config feels overly heavy or violates the *Interface Segregation Principle*, we expose dedicated accessors (like `get_buckets_config()`, `get_ports_config()`).
   * **Zero Overhead Delegation**: These targeted getters do **not** define their own file parsing or `@cache` logic. They simply delegate directly to the master `get_config()` and return the requested sub-property. This ensures we parse the files exactly once, cache the resulting instances, yet offer lightweight, focused endpoints for the rest of the application.

3. **Testing Advantages**:
   * In unit and integration tests, you only ever need to mock a single cached getter (`get_config()`) to swap out any part of the configuration system, avoiding multiple separate patches.

### Implementation Blueprint

```python
# The Master Config (cached singleton)
@cache
def get_config() -> PipelineConfig:
    """Loads and returns the cached PipelineConfig singleton."""
    return PipelineConfig._from_yaml()

# Granular Delegators (no direct caching, delegates to Master Config)
def get_buckets_config() -> BucketsConfig:
    """Loads and returns the cached BucketsConfig singleton.
    
    This allows downstream clients who only need bucket configuration to import
    a lightweight getter without handling the entire PipelineConfig object.
    """
    return get_config().buckets

def get_ports_config() -> PortsConfig:
    """Loads and returns the cached PortsConfig singleton.
    
    Exposed specifically for network-bound tasks that only care about port values.
    """
    return get_config().ports
```


