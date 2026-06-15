## Key idea behind the project

I have built a repository that breaks down the complex business logic of the ENTSO-E Transparency Platform with clear explanations, and provides a ready-to-use YAML-driven tool to upload FMS files to S3-compatible storage (local like SeaweedFS or cloud like AWS S3).

## What for?

In short: **to jump-start your own development on the ENTSO-E transparency platform.**

I want to build a repository that helps newcomers get off the ground quickly. A place to help developers navigate the complexities of the ENTSO-E platform by first defining and building modern data products (a pipeline in this case).

## Why the ENTSO-E Transparency Platform?

The ENTSO-E Transparency Platform is the digital twin of the world's largest interconnected electrical grid. Operating under the strict legal mandate of EU Regulation 543/2013, the platform obliges 40 Transmission System Operators (TSOs) across 36 European countries, as well as power plant owners and exchanges, to publish fundamental market and system data.

For analysts, data engineers, and traders, this platform is essential for understanding the European electricity market.

------

## Where to start your exploration?

### To begin with the ENTSO-E Transparency Platform:

1. **See available domains:** 
   Check [fms_metadata/overview.yml](fms_metadata/overview.yml) 
2. **Understand business logic:** 
   Check [fms_metadata/business_context_catalog/entsoe_domains_overview_detailed.yml](fms_metadata/business_context_catalog/entsoe_domains_overview_detailed.yml)
3. **See the folder structure of the ENTSO-E FMS:** 
   Check [fms_metadata/overview_tree.yml](fms_metadata/overview_tree.yml)
4. **See each file's metadata** (like file sizes, checksums, last update time, etc.): 
   Check the `fms_metadata/physical_catalog/` folder.

   *Folder structure:*
   ```bash
   .
   ├── iop
   │   ├── TP_export
   │   │   ├── Balancing.yml
   │   │   ├── Generation.yml
   │   │   ├── Load.yml
   │   │   ├── Market.yml
   │   │   ├── Operations.yml
   │   │   ├── OtherMarketInformation.yml
   │   │   ├── Outages.yml
   │   │   └── Transmission.yml
   │   └── TP_Legacy_Publications
   │       ├── R1_Archives_CSV_XML.yml
   │       ├── R2_Archives.yml
   │       └── R3_Archives.yml
   └── prod
       ├── TP_export
       │   ├── Balancing.yml
       │   ├── Generation.yml
       │   ├── Load.yml
       │   ├── Market.yml
       │   ├── Operations.yml
       │   ├── OtherMarketInformation.yml
       │   ├── Outages.yml
       │   └── Transmission.yml
       └── TP_Legacy_Publications
           ├── R1_Archives_CSV_XML.yml
           ├── R2_Archives.yml
           └── R3_Archives.yml
   ```

5. **Other helpful files:**
   - [fms_metadata/overview_tree.yml](fms_metadata/overview_tree.yml) - FMS folder structure.
   - [docs/reports/fms_metadata_report.md](docs/reports/fms_metadata_report.md) - Human-readable analytical summary of the ENTSO-E File Management System (FMS).
   - [config/entsoe_api_limits.yml](config/entsoe_api_limits.yml) - ENTSO-E API limits.
   - [config/entsoe_fms_folder_schema.yml](config/entsoe_fms_folder_schema.yml) - ENTSO-E FMS folder paths.

### To understand repo structure and tools:

1. **See helpful commands:** Check the [justfile](justfile).
2. **See the source folder:** Browse the `src/entsoe_pipeline/` directory.

   *Folder structure:*
   ```bash
   .
   └── entsoe_pipeline
       ├── api
       │   └── ...
       ├── config
       │   └── ...
       ├── fms_metadata
       │   └── ...
       ├── io
       │   └── ...
       ├── lakehouse
       │   └── ...
       ├── logger
       │   └── ...
       ├── notebooklm
       │   └── ...
       ├── spark
       │   └── ...
       └── vendor_patches
           └── ...
   ```

3. **See configuration folder:** Browse the `config_env_example/` directory.
   > ### NOTE: This folder uses a specific configuration pattern.
   > Please read [ADR-001-centralized-yaml-configuration.md](docs/adr/ADR-001-centralized-yaml-configuration.md) if you are confused by it.

   *Folder structure:*
   ```bash
   .
   ├── bucket.yml
   ├── enviroment.yml
   ├── hosts.yml
   ├── my_entsoe_domains.yml
   ├── notebooklm.yml
   ├── ports.yml
   ├── region.yml
   └── volumes.yml
   ```

4. **See jobs folder:** Browse the `jobs/` directory (already has one job!).

   *Folder structure:*
   ```bash
   ├── intermediate
   ├── marts
   └── staging
       └── landing
           └── ingest_my_entsoe_domains.py
   ```

5. **Explore other developer tools:**
   - Test folder: `tests/`
   - Pre-commit configuration: `.pre-commit-config.yaml`
   - Lint rules: `ruff.toml`
   - Environment variables template: `.env.example`
   - Build definitions: `pyproject.toml`

### A special word about paths:
> Please read [ADR-002-centralized-path-ssot-configuration.md](docs/adr/ADR-002-centralized-path-ssot-configuration.md).

In short, relative path mappings are declared in the single source of truth file: `config/paths.yml`. 

They are dynamically loaded at runtime, so you can import them as absolute `Path` objects directly from the library:

```python
from entsoe_pipeline import PROJECT_ROOT, DATA_DIR, CONFIG_DIR
```

### A special word about config loading:
> Please read [ADR-003-config-loader-public-interface-design.md](docs/adr/ADR-003-config-loader-public-interface-design.md).

In short, all configuration settings (ports, hosts, rate limits, storage buckets) are managed through a centralized config loader. You can import typed config accessors directly from the library:

```python
from entsoe_pipeline import get_config, get_ports_config, get_hosts_config
```

------

## Getting started...

Just a little bit before you jump-start your own developer journey on the ENTSO-E Transparency Platform.

You may want to do the following:

1. **Create an account:** Get your own ENTSO-E Transparency Platform [account](https://transparency.entsoe.eu/), if you don't have one.
2. **Add credentials:** Since this project does not support API authorization yet, you are requested only to fill out your account email and password in the `.env` file.
   > **NOTE:** There are two types of ENTSO-E Transparency Platform accounts:
   > - [PROD](https://transparency.entsoe.eu/) - Production environment (regular use)
   > - [IOP](https://iop-transparency.entsoe.eu/) - Integration-of-Production environment (testing purposes)
   >
   > I strongly recommend using an **IOP** account for development and testing before pulling real data from PROD. Note that the IOP folder structure != PROD folder structure. More about that in:
   > - `fms_metadata/physical_catalog/iop/`
   > - `fms_metadata/physical_catalog/prod/`
3. **Set up S3:** Fill out your S3-compatible storage credentials in the `.env` file.
4. **Docker compose:** You may also want to check the `docker/docker-compose.yml` file to adapt it to your needs.
5. **Config schemas:** To begin working with configuration files, run `just init-config` (more details in the [justfile](justfile)) and fill out the files. They have rich metadata and comments, so you won't get lost.
6. **Local Storage (Optional):** Run `just lakehouse-up` and `just lakehouse-test` to set up your local SeaweedFS.
7. **Clean up (Optional):** Delete the learning artifacts by running `just clean-stan-buren-learning-stuff` and `just remove-agents-folder`.

------

## Refreshing metadata

### To update metadata files, do the following:

1. Run `just fms-overview` to generate [overview.yml](fms_metadata/overview.yml).
2. Run `just fms-tree` to generate [overview_tree.yml](fms_metadata/overview_tree.yml).
3. Run `just fms-physical-catalog` to generate the files under `fms_metadata/physical_catalog/`.
   > **NOTE:** This command generates the full folder structure of the ENTSO-E File Management System for both `iop` and `prod`. It may take up to 40 minutes to update all the data.
   > 
   > You may find these commands useful to update only one of them:
   ```bash
   # Ingest active domains under TP_export using IOP environment
   just iop-ingest-tp-export

   # Ingest historical archives under TP_Legacy_Publications using IOP environment
   just iop-ingest-tp-legacy

   # Ingest active domains under TP_export using PROD environment
   just prod-ingest-tp-export

   # Ingest historical archives under TP_Legacy_Publications using PROD environment
   just prod-ingest-tp-legacy
   ```

### API Request Summary

| Direction (Folder) | Environment (IOP) | Environment (PROD) | Description / Specifics |
| :--- | :---: | :---: | :--- |
| **TP_export** | **85** | **83** | Active incremental domain exports. Requests are made selectively across active directories. |
| **TP_Legacy_Publications** | **1228** | **1478** | Historical archives. Contains deeply nested folders for past years, requiring a recursive traversal of the directory tree. |
| **Total by Environment** | **1313** | **1561** | **Total: 2874 API requests** |

4. Run `just fms-folder-schema` to generate [fms_folder_schema.yml](config/entsoe_fms_folder_schema.yml).
5. Run `just my-entsoe-domains` to generate [my_entsoe_domains.yml](config/domains/my_entsoe_domains_example.yml).

------

## **Optional** switching environment (IOP/PROD):

1. Run `just iop` to switch to the IOP environment.
2. Run `just prod` to switch to the PROD environment.

This will change the `active_environment` variable in [`enviroment.yml`](config_env_example/enviroment.yml).

------

## Start ingestion

To start ingestion, run the ingestion job for the active environment:
```bash
just ingest-active-domains
```

Alternatively, you can run the ingestion job for a specific environment directly:
```bash
# Ingest active domains datasets to landing zone using IOP
just iop-ingest-active-domains

# Ingest active domains datasets to landing zone using PROD
just prod-ingest-active-domains
```

------

## Useful links:

> If you're not familiar with the ENTSO-E Transparency Platform itself - [link](https://transparency.entsoe.eu/).

> ENTSO-E File Library (FMS) and how bulk CSV extracts work - [link](https://transparencyplatform.zendesk.com/hc/en-us/articles/35960137882129-File-Library-Guide).

> Official business logic, definitions, and calculation rules for each data item - [link](https://eepublicdownloads.entsoe.eu/clean-documents/Transparency/MoP_Ref2_DDD_v3r4.pdf).

> Energy Identification Codes (EIC) used to identify bidding zones and market participants - [link](https://www.entsoe.eu/data/energy-identification-codes-eic/).

> RESTful API parameters and official Postman documentation - [link](https://documenter.getpostman.com/view/7009892/2s93JtP3F6).

> `entsoe-py` (the most popular Python client for the ENTSO-E API) - [link](https://github.com/EnergieID/entsoe-py).

------

## Epilogue:
This is an educational project. I did it for learning purposes and I'm proud of it. I hope you will enjoy working with it as much as I enjoyed creating it.

And I hope this will save you many hours trying to figure out ENTSO-E FMS folder structure :)

**Bonus:** here is my [NotebookLLM](https://notebooklm.google.com/notebook/62e20fb1-788f-4adc-a266-28228f8df0e9) where I explore ENTSO-E FMS folder structure using AI. It may be useful for you too
