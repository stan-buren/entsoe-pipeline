---
trigger: always_on
---

# As Data Engineer I implemets this desigh for our pipeline:

## jobs folder

path: `jobs/`

tree:

```bash
.
├── intermediate
│   └── ...
├── marts
│   └── ...
└── staging
    ├── ...
    └── landing
        └── ...
```

### landing zone

It's goal is only to take raw ENTSOE csv files from FMS API, and store them in `landing-zone` bucket in SeaweedFS.

### staging zone

Here we implement iseberg table format using parquet.

#### schemas

We specify schemas at `.data/iseberg_schemas_registry.json` (this is machine generated file, SSOT of schemas)

We have our custom schemas override file at `configs/` folder: `config/schema_overrides.yml`. It contains custum preferences which will be injected to `iseberg_schemas_registry.json`.

Script is here `src/entsoe_pipeline/spark/iseberg_schemas_registry_generator.py`


