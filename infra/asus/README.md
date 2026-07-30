# ASUS — Compute Node

**Role:** Network gateway + Spark cluster master for the ENTSO-E pipeline.

## Purpose in This Project

ASUS hosts the Spark standalone cluster (Master + Connect Server) that coordinates distributed data processing across HP and Dell workers. It also routes outbound internet traffic through a VPN, which Spark workers rely on to access ENTSO-E APIs.

## Pipeline Services

| Service | Type | Purpose |
|---------|------|---------|
| `spark-master` | systemd | Spark standalone cluster master |
| `spark-connect` | systemd | Spark Connect gRPC server |

## Supporting Infrastructure

| Service | Type | Purpose |
|---------|------|---------|
| VPN client | systemd | Routes outbound traffic (Spark needs this for ENTSO-E API access) |
| `nginx` | systemd | Reverse proxy for external access to pipeline services |
| AdGuard Home | binary | DNS filtering for the local network |
| `unbound` | systemd | Recursive DNS resolver |

## Spark

Deployed by Ansible from templates:
- `/opt/spark/conf/spark-defaults.conf` — S3A credentials, Iceberg extensions
- `/etc/systemd/system/spark-connect.service` — Connect Server startup with full classpath

Worker nodes (HP, Dell) register with the master and inherit cluster configuration.

## Network Role

```
Internet ↔ ASUS (VPN) ↔ HP + Dell workers
```

Outbound traffic from Spark workers (ENTSO-E API calls) routes through ASUS VPN.

## Managed by Ansible

```bash
ansible-playbook -i inventory.yml playbook.yml --limit asus
```
