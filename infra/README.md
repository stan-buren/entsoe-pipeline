# 🏗️ Infrastructure

## Architecture

Three machines on a local network. Only pipeline-relevant services shown.

```
                    Internet
                       │
                  ┌────▼────┐
                  │  Router  │
                  └──┬───┬──┘
                     │   │
       ┌─────────────┘   └─────────────┐
       │                               │
┌──────▼──────┐              ┌─────────▼─────────┐
│  HP (admin) │              │  ASUS (compute)   │
│             │              │                   │
│ SeaweedFS   │              │ Spark Master      │
│ S3 + Iceberg│◄─────────────│ Spark Connect     │
│ Kestra      │   gRPC       │ VPN Gateway       │
│ PostgreSQL  │              │ nginx             │
│ Spark Worker│              │ AdGuard DNS       │
└──────┬──────┘              └────────┬──────────┘
       │                              │
       │        ┌────────────┐        │
       └────────┤ DELL (work)├────────┘
                │            │
                │ Spark      │
                │ Worker     │
                └────────────┘
```

## Design — Zero Duplication

Ansible does NOT store its own copy of configs. At runtime, it calls the Python SSOT:

```
config_env/*.yml ──┐
                   ├──► PipelineConfig (Python) ──► export_config.py ──► Ansible vars
.env ──────────────┘
```

Same pattern as `justfile` — one source of truth, queried at runtime. No `.local.yml`, no vault, no duplication.

## Quick Start

```bash
pip install ansible

# 1. Edit inventory.yml — set ansible_host for each machine
# 2. Ensure config_env/*.yml and .env are configured (your real values)

# 3. Dry-run
ansible-playbook -i infra/ansible/inventory.yml infra/ansible/playbook.yml --check

# 4. Deploy
ansible-playbook -i infra/ansible/inventory.yml infra/ansible/playbook.yml
```

## Files

| What | Where | Git |
|------|-------|-----|
| Public config (ports, hosts, buckets) | `config_env/*.yml` | gitignored |
| Public config templates | `config_env_example/*.yml` | ✅ committed |
| Secrets (S3 keys, API tokens) | `.env` | gitignored |
| Secrets template | `.env.example` | ✅ committed |
| Spark packages, extensions | `group_vars/all.yml` | ✅ committed |
| Ansible playbook + templates | `playbook.yml`, `templates/` | ✅ committed |
| Machine docs | `{asus,hp,dell}/README.md` | ✅ committed |
| Network topology | `network/topology.md` | ✅ committed |

## Network

See [network/topology.md](network/topology.md) for pipeline ports and VPN routing.
