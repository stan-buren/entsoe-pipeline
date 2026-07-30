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
kestra_web_port      := `uv run python -c "from entsoe_pipeline import get_ports_config; print(get_ports_config().kestra_web)"`
kestra_api_port      := `uv run python -c "from entsoe_pipeline import get_ports_config; print(get_ports_config().kestra_api)"`
database_port        := `uv run python -c "from entsoe_pipeline import get_ports_config; print(get_ports_config().database)"`
s3_landing_bucket    := `uv run python -c "from entsoe_pipeline import get_buckets_config; print(get_buckets_config().s3_landing_bucket)"`
s3_lakehouse_bucket  := `uv run python -c "from entsoe_pipeline import get_buckets_config; print(get_buckets_config().s3_lakehouse_bucket)"`
s3_table_bucket      := `uv run python -c "from entsoe_pipeline import get_buckets_config; print(get_buckets_config().s3_table_bucket)"`
aws_region           := `uv run python -c "from entsoe_pipeline import get_region_config; print(get_region_config().aws_region)"`
s3_compatible_volume := `uv run python -c "from entsoe_pipeline import get_volumes_config; print(get_volumes_config().s3_compatible)"`
kestra_url           := `uv run python -c "from entsoe_pipeline import get_urls_config; print(get_urls_config().kestra)"`
project_root         := `uv run python -c "from entsoe_pipeline.config.paths import PROJECT_ROOT; print(PROJECT_ROOT)"`
active_environment   := `uv run python -c "from entsoe_pipeline import get_env_config; print(get_env_config().environment_name)"`


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
export KESTRA_WEB_PORT       := kestra_web_port
export KESTRA_API_PORT       := kestra_api_port
export DATABASE_PORT         := database_port
export S3_LANDING_BUCKET     := s3_landing_bucket
export S3_LAKEHOUSE_BUCKET   := s3_lakehouse_bucket
export S3_TABLE_BUCKET       := s3_table_bucket
export AWS_REGION            := aws_region
export AWS_DEFAULT_REGION    := aws_region
export S3_COMPATIBLE_VOLUME  := s3_compatible_volume
export KESTRA_URL            := kestra_url
export PROJECT_ROOT          := project_root
export ACTIVE_ENVIRONMENT    := active_environment




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

# Start only the local Lakehouse storage service (SeaweedFS)
lakehouse-up:
    @echo "[JUST][INIT] Launching Lakehouse storage (SeaweedFS)..."
    @echo "[JUST][INIT] S3 compatible port: {{s3_compatible_port}}"
    @echo "[JUST][INIT] Iceberg Catalog port: {{iceberg_catalog_port}}"
    docker compose --env-file .env -f docker/docker-compose.yml up -d seaweedfs
    @echo "[JUST][INIT] Lakehouse storage is up and running"

# Stop only the local Lakehouse storage container
lakehouse-down:
    @echo "[JUST][INIT] Stopping Lakehouse storage..."
    docker compose --env-file .env -f docker/docker-compose.yml stop seaweedfs
    docker compose --env-file .env -f docker/docker-compose.yml rm -f seaweedfs
    @echo "[JUST][INIT] Lakehouse storage stopped and container removed"

# Run the readiness checks to ensure local SeaweedFS is active and writable
lakehouse-test:
    @echo "[JUST][TEST] Checking if local Lakehouse storage is ready..."
    uv run pytest tests/jobs/test_seaweedfs_ready.py -v --no-cov

# Show logs for the local Lakehouse storage
lakehouse-logs:
    docker compose --env-file .env -f docker/docker-compose.yml logs -f seaweedfs

# Create S3 Table Bucket, regular S3 buckets, and Iceberg namespace
lakehouse-init-buckets:
    @echo "[JUST][LAKEHOUSE] Initializing S3 buckets and Iceberg catalog..."
    uv run python src/entsoe_pipeline/lakehouse/create_buckets.py
    @echo "[JUST][LAKEHOUSE] Lakehouse initialization complete."


# =============================================================================
# 3. METADATA DATABASE INFRASTRUCTURE (Docker Compose)
# =============================================================================

# Start only the local FMS metadata database service
database-up:
    @echo "[JUST][INIT] Launching ENTSO-E Metadata database..."
    @echo "[JUST][INIT] Database port: {{database_port}}"
    docker compose --env-file .env -f docker/docker-compose.yml up -d entsoe_postgres
    @echo "[JUST][INIT] Metadata database is up and running"

# Stop only the local FMS metadata database container
database-down:
    @echo "[JUST][INIT] Stopping ENTSO-E Metadata database..."
    docker compose --env-file .env -f docker/docker-compose.yml stop entsoe_postgres
    docker compose --env-file .env -f docker/docker-compose.yml rm -f entsoe_postgres
    @echo "[JUST][INIT] Metadata database stopped and container removed"

# Show logs for the local FMS metadata database
database-logs:
    docker compose --env-file .env -f docker/docker-compose.yml logs -f entsoe_postgres


# =============================================================================
# 4. KESTRA ORCHESTRATION INFRASTRUCTURE (Docker Compose)
# =============================================================================

# Start only Kestra and its metadata database in the background
kestra-up:
    @echo "[JUST][INIT] Launching Kestra orchestration..."
    @echo "[JUST][INIT] Kestra Web UI port: {{kestra_web_port}}"
    @echo "[JUST][INIT] Kestra API port: {{kestra_api_port}}"
    docker compose --env-file .env -f docker/docker-compose.yml up -d kestra_postgres kestra
    @echo "[JUST][INIT] Kestra orchestration services are up and running"

# Stop and remove Kestra orchestration containers
kestra-down:
    @echo "[JUST][INIT] Stopping Kestra orchestration..."
    docker compose --env-file .env -f docker/docker-compose.yml stop kestra_postgres kestra
    docker compose --env-file .env -f docker/docker-compose.yml rm -f kestra_postgres kestra
    @echo "[JUST][INIT] Kestra orchestration services stopped and containers removed"

# Show logs for Kestra orchestration services
kestra-logs:
    docker compose --env-file .env -f docker/docker-compose.yml logs -f kestra_postgres kestra


# =============================================================================
# 5. GENERAL INFRASTRUCTURE MANAGEMENT (Docker Compose)
# =============================================================================

# Start all local infrastructure services (SeaweedFS + Kestra + Postgres)
infra-up:
    @echo "[JUST][INIT] Launching all infrastructure services..."
    @echo "[JUST][INIT] S3 compatible port: {{s3_compatible_port}}"
    @echo "[JUST][INIT] Iceberg Catalog port: {{iceberg_catalog_port}}"
    @echo "[JUST][INIT] Kestra Web UI port: {{kestra_web_port}}"
    @echo "[JUST][INIT] Kestra API port: {{kestra_api_port}}"
    @echo "[JUST][INIT] Database port: {{database_port}}"
    docker compose --env-file .env -f docker/docker-compose.yml up -d
    @echo "[JUST][INIT] All infrastructure services are up and running"

# Stop and tear down all local infrastructure containers
infra-down:
    @echo "[JUST][INIT] Tearing down all infrastructure services..."
    docker compose --env-file .env -f docker/docker-compose.yml down
    @echo "[JUST][INIT] All infrastructure services stopped"

# Show logs for all running infrastructure containers
infra-logs:
    docker compose --env-file .env -f docker/docker-compose.yml logs -f


# =============================================================================
# 6. DOCKER IMAGE MANAGEMENT
# =============================================================================

# Build the pipeline Docker image locally
docker-build:
    @echo "[JUST][DOCKER] Building pipeline Docker image..."
    docker build --progress=plain -f docker/Dockerfile -t entsoe-pipeline:latest .


# =============================================================================
# 7. PIPELINE TESTING & INTEGRATION
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
# 8. FMS METADATA REFRESH
# =============================================================================

# Crawl remote ENTSO-E platforms (IOP & PROD) and regenerate overview.yml
fms-overview:
    @echo "[JUST][METADATA] Crawling remote FMS directory structures and regenerating overview.yml..."
    uv run python src/entsoe_pipeline/fms_metadata/ingestion/overview_ingest.py

# Build the landing bucket schema contract in database
fms-folder-schema:
    @echo "[JUST][METADATA] Building landing bucket schema contract in database table landing_folders_schema..."
    uv run python src/entsoe_pipeline/fms_metadata/ingestion/landing_bucket_schema.py

# Generate the active domains configuration checklist config/domains/my_entsoe_domains.yml
my-entsoe-domains:
    @echo "[JUST][METADATA] Generating active domains configuration checklist..."
    uv run python src/entsoe_pipeline/fms_metadata/ingestion/my_entsoe_domains.py

# =============================================================================
# 9. PLATFORM ENVIRONMENT SWITCHERS
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
# 10. EXTERNAL TECHNICAL DOCUMENTATION SCAPERS
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
# 11. PHYSICAL METADATA CATALOG INGESTION
# =============================================================================
# Depreciated - changed to PostgeSQL.
# # Ingest all active physical metadata catalogs under TP_export for the active environment (balancing, load, market, operations, transmission, outages, generation, etc.)
# ingest-tp-export:
#     @echo "[JUST][METADATA] Ingesting all active domains under TP_export..."
#     uv run python src/entsoe_pipeline/fms_metadata/ingestion/balancing_ingest.py
#     uv run python src/entsoe_pipeline/fms_metadata/ingestion/generation_ingest.py
#     uv run python src/entsoe_pipeline/fms_metadata/ingestion/load_ingest.py
#     uv run python src/entsoe_pipeline/fms_metadata/ingestion/market_ingest.py
#     uv run python src/entsoe_pipeline/fms_metadata/ingestion/operations_ingest.py
#     uv run python src/entsoe_pipeline/fms_metadata/ingestion/other_market_information_ingest.py
#     uv run python src/entsoe_pipeline/fms_metadata/ingestion/outages_ingest.py
#     uv run python src/entsoe_pipeline/fms_metadata/ingestion/transmission_ingest.py

# # Ingest all historical publications archives under TP_Legacy_Publications for the active environment
# ingest-tp-legacy:
#     @echo "[JUST][METADATA] Ingesting all historical legacy archives..."
#     uv run python src/entsoe_pipeline/fms_metadata/ingestion/legacy_ingest.py

# # Ingest active domains under TP_export using IOP environment
# iop-ingest-tp-export: use-iop ingest-tp-export

# # Ingest historical archives under TP_Legacy_Publications using IOP environment
# iop-ingest-tp-legacy: use-iop ingest-tp-legacy

# # Ingest active domains under TP_export using PROD environment
# prod-ingest-tp-export: use-prod ingest-tp-export

# # Ingest historical archives under TP_Legacy_Publications using PROD environment
# prod-ingest-tp-legacy: use-prod ingest-tp-legacy


# =============================================================================
# 12. DATA INGESTION JOBS (S3 landing zone syncing)
# =============================================================================

# Ingest active domains datasets to landing zone for the active environment
ingest-active-domains:
    @echo "[JUST][INGEST] Starting active ENTSO-E domains ingestion job..."
    @echo "[JUST][INGEST] Step 1/2: Running Ingestion Preparation Job..."
    uv run python jobs/landing/prepare_landing_ingestion.py
    @echo "[JUST][INGEST] Step 2/2: Syncing active domains from FTP to S3 Landing Zone..."
    uv run python jobs/landing/ingest_my_entsoe_domains.py

# Refresh global FMS metadata catalog incrementally (or fully via flags="--full-scan")
refresh-fms-metadata flags="":
    @echo "[JUST][REFRESH] Starting global FMS metadata refresh job..."
    @echo "[JUST][REFRESH] Step 1/3: Preparing metadata..."
    uv run python jobs/refresh_fms_metadata.py --phase prepare {{ flags }}
    @echo "[JUST][REFRESH] Step 2/3: Crawling active environment ({{active_environment}})..."
    uv run python jobs/refresh_fms_metadata.py --phase crawl --env {{active_environment}} {{ flags }}
    @echo "[JUST][REFRESH] Step 3/3: Finalizing catalog..."
    uv run python jobs/refresh_fms_metadata.py --phase finalize {{ flags }}

# Ingest raw files from landing zone S3 bucket into Apache Iceberg staging tables
ingest-landing-to-lakehouse:
    @echo "[JUST][LAKEHOUSE] Starting landing zone to Iceberg lakehouse ingestion job..."
    uv run python jobs/staging/ingest_landing_csv_to_lakehouse.py



# =============================================================================
# 13. CLEAR DEVELOPER LEARNING STUFF
# =============================================================================

clean-stan-buren-learning-stuff:
    @echo "[JUST][CLEAN] Cleaning developer learning stuff..."
    rm -rf docs/knowledge/* 
    rm -rf notebooks/*

remove-agents-folder:
    @echo "[JUST][CLEAN] Removing agents instructions folder..."
    rm -rf .agents/*


# =============================================================================
# 14. ICEBERG SCHEMAS REGISTRY GENERATION
# =============================================================================

# Infer schemas from landing zone samples and generate the Iceberg schemas registry JSON
generate-schemas:
    @echo "[JUST][SCHEMAS] Inferring schemas and generating registry..."
    uv run python src/entsoe_pipeline/lakehouse/iseberg_schemas_registry_generator.py


# =============================================================================
# 15. SPARK CLUSTER MANAGEMENT (Ansible)
# =============================================================================

# Deploy configs and start the Spark cluster
cluster-start:
    ansible-playbook -i infra/ansible/inventory.local.yml infra/ansible/playbook.yml

# Stop the Spark cluster (workers will disconnect automatically)
cluster-stop:
    ansible-playbook -i infra/ansible/inventory.local.yml infra/ansible/playbook.yml --tags stop

# Restart the Spark cluster
cluster-restart:
    ansible-playbook -i infra/ansible/inventory.local.yml infra/ansible/playbook.yml --tags restart

