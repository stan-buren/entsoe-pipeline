# Network Topology (Pipeline-Relevant)

## Architecture

Three machines on a local network, connected through a consumer router.

```
Internet ↔ Router ↔ ASUS (Spark Master + VPN) ↔ HP + Dell (Spark Workers)
                         ↕
                  HP (SeaweedFS S3 + Iceberg + Kestra + PostgreSQL)
```

## Pipeline Ports

| Port | Machine | Service | Purpose |
|------|---------|---------|---------|
| 8333 | HP | SeaweedFS S3 API | Object storage for landing/lakehouse |
| 8181 | HP | Iceberg REST Catalog | Table metadata |
| 15002 | ASUS | Spark Connect gRPC | Client→cluster bridge |
| 7077 | ASUS | Spark Master | Worker coordination |
| 5432 | HP | PostgreSQL | Pipeline metadata database |
| 8080 | HP | Kestra Web UI | Workflow orchestration |

## VPN Routing (on ASUS)

Spark workers need internet access to call ENTSO-E APIs. Traffic routes through ASUS VPN:

```
Spark worker → ASUS → VPN tunnel → ENTSO-E API
```

Local S3 traffic (worker → SeaweedFS) stays on the LAN, bypassing VPN.

## DNS

AdGuard Home on ASUS provides network-wide DNS filtering. Workers use it for name resolution.
