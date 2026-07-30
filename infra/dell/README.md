# Dell — Spark Worker

**Role:** Spark executor in the ENTSO-E pipeline cluster.

## Purpose in This Project

Dell contributes 4 CPU cores and 4 GB RAM to the Spark standalone cluster. It executes distributed data processing tasks scheduled by the Spark Master (ASUS). That's it — no other Dell services are part of this pipeline.

## Pipeline Services

| Service | Type | Purpose |
|---------|------|---------|
| `spark-worker` | systemd | Spark executor, 4 cores, 4 GB RAM |

## S3 Data Access

Dell workers read/write S3 data from SeaweedFS (HP) over the local network. S3A credentials are configured on the Spark Connect Server (ASUS) and inherited by all workers.

## Managed by Ansible

```bash
ansible-playbook -i inventory.yml playbook.yml --limit dell
```
