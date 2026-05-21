s3_compatible_port   := `uv run python -c "from entsoe_pipeline.config.config_loader import PortsConfig; print(PortsConfig.from_yaml().s3_compatible)"`
iceberg_catalog_port := `uv run python -c "from entsoe_pipeline.config.config_loader import PortsConfig; print(PortsConfig.from_yaml().iceberg_catalog)"`


# Dynamically export variables so Docker Compose automatically inherits them
export S3_COMPATIBLE_PORT    := s3_compatible_port
export ICEBERG_CATALOG_PORT := iceberg_catalog_port

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



# Start the local Lakehouse services in the background
up:
    @echo "[JUST][INIT] Launching Lakehouse services"
    @echo "[JUST][INIT] S3 compatible port: {{s3_compatible_port}}"
    @echo "[JUST][INIT] Iceberg Catalog port: {{iceberg_catalog_port}}"
    docker compose -f docker/docker-compose.yml up -d
    @echo "[JUST][INIT] Lakehouse services are up and running"

# Stop and tear down all infrastructure containers
down:
    @echo "[JUST][INIT] Stopping Lakehouse services"
    docker compose -f docker/docker-compose.yml down
    @echo "[JUST][INIT] Lakehouse services stopped"

# Show logs from all running containers
logs:
    docker compose -f docker/docker-compose.yml logs -f

# Run the test suite using pytest
test:
    @echo "[JUST][TEST] Running all unit and integration tests..."
    uv run pytest
