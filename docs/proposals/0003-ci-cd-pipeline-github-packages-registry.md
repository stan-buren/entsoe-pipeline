# PROPOSAL-0003: CI/CD Pipeline with GitHub Packages Docker Registry

## Metadata

* **Author:** Stanislav Burundukov
* **Status:** Draft
* **Created Date:** 2026-06-29
* **Target Timeline:** Post-Landing Zone Stabilization

---

## Summary

Introduce a GitHub Actions CI/CD pipeline that automatically builds the `entsoe-pipeline` Docker image on every merge to `main` and publishes it to the GitHub Container Registry (ghcr.io). This eliminates the manual `docker build` step from the developer workflow and ensures Kestra orchestration always consumes a verified, tested image.

## Motivation

Currently, developers must manually run `just docker-build` before running any Kestra-orchestrated job. This creates two problems:

1. **Human error**: A developer may forget to rebuild after code changes, causing Kestra to run a stale image with outdated logic or missing bug fixes.
2. **No verification gate**: The Docker image is built locally without running the test suite first, meaning broken code can silently end up in a running pipeline.

With a CI/CD pipeline tied to GitHub Packages, the image is only published after all tests pass. Kestra can then pull the latest verified image automatically using `pullPolicy: ALWAYS`, making the entire deploy process hands-free.

## Proposed Design

### Flow

```
git push main
    ↓
GitHub Actions CI Runner
    ├── 1. just test               ← unit + integration tests
    ├── 2. docker build            ← builds entsoe-pipeline:latest
    ├── 3. docker push             ← pushes to ghcr.io/org/entsoe-pipeline
    └── 4. tag with git SHA        ← immutable version tag
         e.g. ghcr.io/.../entsoe-pipeline:abc1234
              ghcr.io/.../entsoe-pipeline:latest
```

### GitHub Actions Workflow

```yaml
# .github/workflows/ci.yml
name: Build & Publish Docker Image

on:
  push:
    branches: [main]

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      packages: write
      contents: read

    steps:
      - uses: actions/checkout@v4

      - name: Run tests
        run: just test

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          context: .
          file: docker/Dockerfile
          push: true
          tags: |
            ghcr.io/${{ github.repository_owner }}/entsoe-pipeline:latest
            ghcr.io/${{ github.repository_owner }}/entsoe-pipeline:${{ github.sha }}
```

### Kestra DAG Change

All DAG files in `dags/` would switch `pullPolicy` from `NEVER` to `ALWAYS` and update the image name:

```yaml
variables:
  docker_image: ghcr.io/org/entsoe-pipeline:latest

taskRunner:
  type: io.kestra.plugin.scripts.runner.docker.Docker
  pullPolicy: ALWAYS   # was: NEVER
```

### docker-compose.yml Change

The `entsoe-pipeline` service image reference would be updated from a local tag to the registry path:

```yaml
image: ghcr.io/org/entsoe-pipeline:latest
```

## Metrics & Observability (S3 Storage Health)

- **GitHub Actions build logs**: Every CI run produces a build log accessible from the GitHub Actions tab. Failed builds block the merge and are visible to all contributors.
- **Image digest pinning**: Each published image gets an immutable SHA digest (e.g. `sha256:abc123`). Kestra logs will show which digest was pulled, enabling exact reproducibility of any past pipeline run.
- **Build duration tracking**: GitHub Actions provides per-step timing. We should alert if the Docker build step exceeds 10 minutes, which would indicate bloated dependencies.

## Open Questions / Risks

- **Private vs public registry**: If the GitHub repository is private, `ghcr.io` images are private by default. The Kestra server will need a `GITHUB_TOKEN` secret injected as a Docker registry credential to pull the image. This needs to be configured in `docker-compose.yml` or as a Kestra plugin credential.
- **Cache strategy**: `docker build` in CI is slow without layer caching. We should evaluate `--cache-from ghcr.io/.../entsoe-pipeline:latest` or GitHub Actions cache backend to keep build times under 3 minutes.
- **`just` availability in CI**: The GitHub Actions runner needs `just` installed. We should add a setup step (`cargo install just`) or inline the commands directly in the workflow to avoid the dependency.
