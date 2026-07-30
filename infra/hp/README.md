# HP — Workstation + Pipeline Services

**Role:** Development machine + core pipeline infrastructure.

## Purpose in This Project

HP runs the foundational storage and orchestration layer of the ENTSO-E pipeline: SeaweedFS (S3 + Iceberg REST Catalog), Kestra workflow orchestrator, PostgreSQL metadata database, and a Spark Worker. OpenClaw Gateway is the AI agent that assists with development.

## Pipeline Services

| Service | Type | Purpose |
|---------|------|---------|
| `spark-worker` | systemd | Spark executor (6 cores, 10 GB) |
| `seaweedfs` | Docker | S3-compatible object storage + Iceberg REST Catalog |
| `kestra` | Docker | Workflow orchestrator for pipeline jobs |
| `kestra_postgres` | Docker | Kestra metadata database |
| `entsoe_postgres` | Docker | ENTSO-E metadata database (landing files, ingestion logs) |
| `openclaw` | systemd (user) | AI agent gateway for development |

## SeaweedFS

Single-node deployment providing:
- **S3 API** — object storage for landing zone and lakehouse buckets
- **Iceberg REST Catalog** — table metadata and namespace management

## Spark Worker

Connects to Spark Master (ASUS). 6 cores, 10 GB RAM.

## Managed by Ansible

```bash
ansible-playbook -i inventory.yml playbook.yml --limit hp
```
