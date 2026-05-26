s3_compatible_port   := `uv run python -c "from entsoe_pipeline import get_ports_config; print(get_ports_config().s3_compatible)"`
iceberg_catalog_port := `uv run python -c "from entsoe_pipeline import get_ports_config; print(get_ports_config().iceberg_catalog)"`
s3_bucket            := `uv run python -c "from entsoe_pipeline import get_buckets_config; print(get_buckets_config().s3_bucket)"`
s3_table_bucket      := `uv run python -c "from entsoe_pipeline import get_buckets_config; print(get_buckets_config().s3_table_bucket)"`
aws_region           := `uv run python -c "from entsoe_pipeline import get_region_config; print(get_region_config().aws_region)"`


# Dynamically export variables so Docker Compose automatically inherits them
export S3_COMPATIBLE_PORT    := s3_compatible_port
export ICEBERG_CATALOG_PORT  := iceberg_catalog_port
export S3_BUCKET             := s3_bucket
export S3_TABLE_BUCKET       := s3_table_bucket
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
up:
    @echo "[JUST][INIT] Launching Lakehouse services"
    @echo "[JUST][INIT] S3 compatible port: {{s3_compatible_port}}"
    @echo "[JUST][INIT] Iceberg Catalog port: {{iceberg_catalog_port}}"
    docker compose --env-file .env -f docker/docker-compose.yml up -d
    @echo "[JUST][INIT] Lakehouse services are up and running"

# Stop and tear down all infrastructure containers
down:
    @echo "[JUST][INIT] Stopping Lakehouse services"
    docker compose --env-file .env -f docker/docker-compose.yml down
    @echo "[JUST][INIT] Lakehouse services stopped"

# Show logs from all running containers
logs:
    docker compose --env-file .env -f docker/docker-compose.yml logs -f


# =============================================================================
# 3. PIPELINE TESTING & INTEGRATION
# =============================================================================

# Run the test suite using pytest
test:
    @echo "[JUST][TEST] Running all unit and integration tests..."
    uv run pytest


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
