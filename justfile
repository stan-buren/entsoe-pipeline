# =============================================================================
# DYNAMIC CONFIGURATION EXTRACTION & INHERITANCE
# =============================================================================
# In Justfile, variable assignment using backticks (:= `command`) runs the command 
# in a subshell at load time and stores its stdout as a variable.
#
# Here, we bootstrap our centralized Python config loader via `uv run` to parse
# active YAML configuration files (which are our Single Source of Truth for configs).
# This avoids hardcoding network ports, storage buckets, and AWS regions in multiple places.
s3_compatible_port   := `uv run python -c "from entsoe_pipeline import get_ports_config; print(get_ports_config().s3_compatible)"`
iceberg_catalog_port := `uv run python -c "from entsoe_pipeline import get_ports_config; print(get_ports_config().iceberg_catalog)"`
master_http_port     := `uv run python -c "from entsoe_pipeline import get_ports_config; print(get_ports_config().master_http)"`
master_grpc_port     := `uv run python -c "from entsoe_pipeline import get_ports_config; print(get_ports_config().master_grpc)"`
volume_http_port     := `uv run python -c "from entsoe_pipeline import get_ports_config; print(get_ports_config().volume_http)"`
filer_http_port      := `uv run python -c "from entsoe_pipeline import get_ports_config; print(get_ports_config().filer_http)"`
filer_grpc_port      := `uv run python -c "from entsoe_pipeline import get_ports_config; print(get_ports_config().filer_grpc)"`
s3_landing_bucket    := `uv run python -c "from entsoe_pipeline import get_buckets_config; print(get_buckets_config().s3_landing_bucket)"`
s3_lakehouse_bucket  := `uv run python -c "from entsoe_pipeline import get_buckets_config; print(get_buckets_config().s3_lakehouse_bucket)"`
aws_region           := `uv run python -c "from entsoe_pipeline import get_region_config; print(get_region_config().aws_region)"`


# Export the parsed values as environment variables to the parent environment.
# Because Docker Compose automatically inherits host environment variables,
# this export ensures that any compose/docker command executed by Just recipes
# will dynamically read the configured ports, buckets, and regions without
# relying on hardcoded `.env` files in git.
export S3_COMPATIBLE_PORT    := s3_compatible_port
export ICEBERG_CATALOG_PORT  := iceberg_catalog_port
export MASTER_HTTP_PORT      := master_http_port
export MASTER_GRPC_PORT      := master_grpc_port
export VOLUME_HTTP_PORT      := volume_http_port
export FILER_HTTP_PORT       := filer_http_port
export FILER_GRPC_PORT       := filer_grpc_port
export S3_LANDING_BUCKET     := s3_landing_bucket
export S3_LAKEHOUSE_BUCKET   := s3_lakehouse_bucket
export AWS_REGION            := aws_region
export AWS_DEFAULT_REGION    := aws_region



# =============================================================================
# 1. GENERAL HELPERS & UTILITIES
# =============================================================================

# Show available commands in the project
default:
    @just --list

# Initialize active config files from templates. Stops immediately if 'config_env' directory exists.
init-config:
    @if [ -d "config_env" ]; then \
        echo "[JUST][ERROR] 'config_env/' directory already exists! Stopping initialization to protect your local files."; \
        exit 1; \
    fi
    @echo "[JUST][INIT] 'config_env/' directory not found. Initializing config files from templates..."
    @mkdir -p config_env
    @cp config_env_example/*.yml config_env/
    @echo "[JUST][INIT] Configuration initialized successfully!"


# =============================================================================
# 2. LOCAL LAKEHOUSE INFRASTRUCTURE (Docker Compose)
# =============================================================================

# Start the local Lakehouse services in the background
lakehouse-up:
    @echo "[JUST][INIT] Launching Lakehouse services"
    @echo "[JUST][INIT] S3 compatible port: {{s3_compatible_port}}"
    @echo "[JUST][INIT] Iceberg Catalog port: {{iceberg_catalog_port}}"
    docker compose --env-file .env -f docker/docker-compose.yml up -d
    @echo "[JUST][INIT] Lakehouse services are up and running"

# Stop and tear down all infrastructure containers
lakehouse-down:
    @echo "[JUST][INIT] Stopping Lakehouse services"
    docker compose --env-file .env -f docker/docker-compose.yml down
    @echo "[JUST][INIT] Lakehouse services stopped"

# Run the readiness checks to ensure local SeaweedFS is active and writable
lakehouse-test:
    @echo "[JUST][TEST] Checking if local Lakehouse storage is ready..."
    uv run pytest tests/jobs/test_seaweedfs_ready.py -v --no-cov

# Show logs from all running containers
lakehouse-logs:
    docker compose --env-file .env -f docker/docker-compose.yml logs -f


# =============================================================================
# 3. PIPELINE TESTING & INTEGRATION
# =============================================================================

# Run the test suite using pytest
test:
    @echo "[JUST][TEST] Running all unit and integration tests..."
    uv run pytest

# Scan the repository filesystem for vulnerabilities and secrets using Trivy, skipping large raw data
trivy:
    @echo "[JUST][SECURITY] Scanning repository for vulnerabilities and secrets..."
    trivy fs --skip-dirs .data .

# Run Ruff code quality checks and analysis
ruff-check:
    @echo "[JUST][LINT] Running Ruff code analysis..."
    uv run ruff check

# Run Ruff auto-formatting and auto-fixes
ruff-fix:
    @echo "[JUST][LINT] Applying automatic fixes and formatting with Ruff..."
    uv run ruff format
    uv run ruff check --fix --unsafe-fixes

# Run ruamel.yaml via pre-commit to auto-format all YAML configuration files
yamlfmt:
    @echo "[JUST][LINT] Formatting YAML configuration files with ruamel.yaml..."
    uv run pre-commit run yaml-format --all-files


# Run static type checking using ty
ty:
    @echo "[JUST][TYPE] Running static type analysis with ty..."
    uv run ty check src tests jobs

# Run linting, type checking, and tests
lint: ruff-check ty yamlfmt

# Run security checks
security: trivy

# Run all checks (linting, security, types, tests)
all-checks: lint security test


# =============================================================================
# 4. FMS REMOTE METADATA HARVESTING
# =============================================================================

# Crawl remote ENTSO-E platforms (IOP & PROD) and regenerate overview.yml
fms-overview:
    @echo "[JUST][METADATA] Crawling remote FMS directory structures and regenerating overview.yml..."
    uv run python src/entsoe_pipeline/fms_metadata/overview_ingest.py


# =============================================================================
# 5. PLATFORM ENVIRONMENT SWITCHERS
# =============================================================================

# Switch the active environment in environment config to Production (PROD)
use-prod:
    @uv run python -m entsoe_pipeline.config.switch_env PROD

# Switch the active environment in environment config to Interoperability/Test (IOP)
use-iop:
    @uv run python -m entsoe_pipeline.config.switch_env IOP

# Short aliases for quick platform switches
alias prod := use-prod
alias iop  := use-iop
alias dev  := use-iop


# =============================================================================
# 6. EXTERNAL TECHNICAL DOCUMENTATION SCAPERS
# =============================================================================

# Compile the PySpark SQL API documentation pages into a single Markdown megadoc
spark-docs:
    @echo "[JUST][DOCS] Scraping and compiling PySpark SQL documentation..."
    uv run --group notebooks python notebooks/.learning_scripts/etl_spark_documentation.py

# Compile the latest Apache Iceberg stable documentation into a single Markdown megadoc
iceberg-docs:
    @echo "[JUST][DOCS] Scraping and compiling Apache Iceberg documentation..."
    uv run --group notebooks python notebooks/.learning_scripts/etl_iceberg_documentation.py

# Compile the SeaweedFS wiki documentation pages into a single Markdown megadoc
seaweed-docs:
    @echo "[JUST][DOCS] Scraping and compiling SeaweedFS documentation..."
    uv run --group notebooks python notebooks/.learning_scripts/etl_seaweedfs_documentation.py


# =============================================================================
# 7. PHYSICAL METADATA CATALOG INGESTION
# =============================================================================

# Ingest all active physical metadata catalogs under TP_export (balancing, load, market, operations, transmission, outages, generation, etc.)
ingest-tp-export:
    @echo "[JUST][METADATA] Ingesting all active domains under TP_export..."
    uv run python src/entsoe_pipeline/fms_metadata/ingestion/balancing_ingest.py
    uv run python src/entsoe_pipeline/fms_metadata/ingestion/generation_ingest.py
    uv run python src/entsoe_pipeline/fms_metadata/ingestion/load_ingest.py
    uv run python src/entsoe_pipeline/fms_metadata/ingestion/market_ingest.py
    uv run python src/entsoe_pipeline/fms_metadata/ingestion/operations_ingest.py
    uv run python src/entsoe_pipeline/fms_metadata/ingestion/other_market_information_ingest.py
    uv run python src/entsoe_pipeline/fms_metadata/ingestion/outages_ingest.py
    uv run python src/entsoe_pipeline/fms_metadata/ingestion/transmission_ingest.py

# Ingest all historical publications archives under TP_Legacy_Publications
ingest-tp-legacy:
    @echo "[JUST][METADATA] Ingesting all historical legacy archives..."
    uv run python src/entsoe_pipeline/fms_metadata/ingestion/legacy_ingest.py

