---
trigger: model_decision
description: When we are deciding how to write a new code logic. Or speaking about new scripts.
---

# We respect architecture rules:

## Single Responsibility Principle (SRP)

- **One Reason to Change**: Every module, class, or function must have one, and only one, reason to change. Decouple components that handle different domains.
- **Decouple Client from Action**: Connection and session modules (e.g., `client.py` for Keycloak authentication, credentials resolution, and session management) must never handle data actions such as paginating directory lists or downloading files.
- **Stateless Operations**: Operational actions (e.g., `operations.py` for paginated directory listing) must be designed as stateless functions that accept an authenticated client instance rather than managing the client session lifecycle themselves.

## Separation of Concerns (SoC)

- **Strict Layered Boundaries**: Organize the codebase into clearly decoupled architectural layers:
  1. **Configuration & Environment**: Declares endpoints, constants, and credentials (e.g., `paths.py`, `config_loader.py`).
  2. **API & Transport**: Encapsulates network operations, retry mechanisms (`tenacity`), serialization, and raw HTTP structures (e.g., `api/`).
  3. **ETL & Orchestration (Jobs)**: Glues operational APIs together to perform business orchestration (e.g., `overview_ingest.py`, `ingest_fms_data.py`). High-level jobs must never contain raw HTTP requests.
- **Facade Pattern for Sub-Packages**: Hide internal directory complexity. Packages must expose a clean, flat public API inside their `__init__.py`. External scripts must always import from the package root rather than importing directly from nested internal modules.

## Single Source of Truth (SSOT)

- **Zero Configuration Drift**: Every path, remote target, and credentials map must have a single unique definition.
- **Path Registry**: All filesystem operations must import path constants from `paths.py` (the project's paths SSOT). Ad-hoc calculations or inline hardcoded strings for file locations are strictly prohibited.

## ACID
