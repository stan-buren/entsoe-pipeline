---
trigger: always_on
---

# We use SSOT for configs in our project

## RULES:

* Never hardcode any configs in a scripts.

* DO NOT use .env for enviroment variables. ONLY for secrets (see .env example here `.env.example`)

## Where configs lives even if not in .env? In this folders:

### `config/`

### `config_env/`

## How do we load configs to enviroments? (Docker, just, uv run):

> all this logic lives here: `src/entsoe_pipeline/config/`

### Checking/adding a new config workflow:

1. write or check config at `src/entsoe_pipeline/config/core/`

2. import that config to `src/entsoe_pipeline/config/config_loader.py`.

3. If you've updated file at `src/entsoe_pipeline/config/core/` simply update its function (and its docstring) at `src/entsoe_pipeline/config/config_loader.py`.

4. If you've wrote a new .py script at `src/entsoe_pipeline/config/core/` add new function (and new docstring) at `src/entsoe_pipeline/config/config_loader.py`.

5. Now you can add this variables to `justfile/` (for example: `s3_compatible_port   := `uv run python -c "from entsoe_pipeline import get_ports_config; print(get_ports_config().s3_compatible)"`` and `export S3_COMPATIBLE_PORT    := s3_compatible_port`.

6. Or load them directly to python scripts (for example `from entsoe_pipeline.config.config_loader import FmsPublicationSchema`)


## Read this to understand a full picture:

### `docs/adr/ADR-001-centralized-yaml-configuration.md`


## FAQ

1. .env — secrets only. Buckets — in config_env/bucket.yml → justfile exports → Docker Compose inherits. Therefore, Docker Compose doesn't directly see the variables.