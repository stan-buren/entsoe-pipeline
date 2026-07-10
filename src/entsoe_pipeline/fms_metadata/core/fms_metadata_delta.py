# Copyright 2026 Stanislav Burundukov
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import time

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import pandas as pd

from sqlalchemy import create_engine, func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from entsoe_pipeline import EntsoePipelineError, get_classifier_config
from entsoe_pipeline.api.client import create_fms_client
from entsoe_pipeline.api.ls_fms import list_folder_raw_items
from entsoe_pipeline.db import build_metadata, get_db_url
from entsoe_pipeline.fms_metadata.utils.crawler import crawl_metadata_folder
from entsoe_pipeline.fms_metadata.utils.overview_parser import get_domain_folders

logger = logging.getLogger("entsoe_pipeline.fms_metadata.core.fms_metadata_delta")


def parse_log_timestamp(val: Any) -> datetime | None:
    """Safely parses FMS log timestamp into UTC datetime."""
    if pd.isna(val) or not isinstance(val, str):
        return None
    try:
        # Expected log format: DD-MM-YYYY HH:MM:SS
        return datetime.strptime(val.strip(), "%d-%m-%Y %H:%M:%S").replace(tzinfo=UTC)
    except Exception:
        try:
            return pd.to_datetime(val.strip()).to_pydatetime().replace(tzinfo=UTC)
        except Exception:
            return None


def parse_db_timestamp(val: Any) -> datetime | None:
    """Safely parses DB ISO timestamp into UTC datetime.

    Uses stdlib datetime.fromisoformat() (Python 3.11+ supports Z suffix natively)
    instead of pd.to_datetime() to avoid ~67s overhead when called 74k times in a loop.
    """
    if not val or not isinstance(val, str):
        return None
    try:
        # Python 3.11+ fromisoformat() handles both Z and +00:00 suffixes natively.
        return datetime.fromisoformat(val)
    except ValueError:
        return None


def strip_extension(filename: str) -> str:
    """Strips standard file extensions to facilitate base name matching."""
    for ext in (".zip", ".csv", ".xml", ".xlsx"):
        if filename.lower().endswith(ext):
            return filename[: -len(ext)]
    return filename


def resolve_exact_fms_folder(folder_name: str, file_name: str) -> str:
    """Resolves the leaf folder path for recursive FMS directories like Offered Transfer Capacities.

    For flat folders, returns folder_name unchanged.
    """
    if "OfferedTransferCapacitiesContinuousEvolution" in folder_name:
        # Expected file_name format: YYYY_MM_DD_OUT_IN_Folder
        # e.g. 2026_07_08_HU_SK_OfferedTransferCapacitiesContinuousEvolution_11.1_r3.1
        parts = file_name.split("_")
        if len(parts) >= 4:
            year = parts[0]
            month = parts[1]
            day = parts[2]
            out_area = parts[3]
            return f"{folder_name}/{year}_{month}/{year}_{month}_{day}/{out_area}"
    return folder_name


def run_delta_metadata_refresh(
    env: str,
    is_test: bool = False,
    is_force: bool = False,
    domain_name: str | None = None,
    full_scan_callback: Callable[..., None] | None = None,
) -> None:
    """Incremental metadata crawler using Export_log_r3.csv and Export_oce_log_r3.csv."""
    logger.info("Starting incremental delta metadata crawl for environment: %s", env)

    if is_force:
        logger.info(
            "Force flag enabled. Falling back to full recursive metadata crawl."
        )
        if full_scan_callback:
            full_scan_callback(
                env, is_test=is_test, is_force=True, domain_name=domain_name
            )
        else:
            logger.error(
                "Force crawl requested but no full_scan_callback was provided."
            )
        return

    # 1. Resolve active domains and folders
    config = get_classifier_config()
    domains = config.domain_order
    if is_test:
        light_domains = ["Load", "Generation", "OtherMarketInformation"]
        domains = [d for d in domains if d in light_domains]

    target_domain = domain_name.strip() if domain_name else "ALL"
    if target_domain.lower() not in ("all", "legacy"):
        domains = [d for d in domains if d.lower() == target_domain.lower()]

    active_folders = []
    folder_to_domain = {}
    for domain in domains:
        folders = get_domain_folders(domain, env)
        active_folders.extend(folders)
        for f in folders:
            folder_to_domain[f] = domain

    if not active_folders:
        logger.info("No active folders found to monitor.")
        return

    # 2. Download FMS logs in memory
    logger.info("Downloading FMS log files in memory...")
    t_start = time.time()
    try:
        client = create_fms_client(env)

        # Check size before downloading to avoid OOM
        root_items = list_folder_raw_items(client, folder_name="", root_dir="TP_export")
        root_files = {item["name"]: item for item in root_items if item.get("name")}

        MAX_LOG_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB
        for log_file in ("Export_log_r3.csv", "Export_oce_log_r3.csv"):
            if log_file in root_files:
                file_size = (
                    root_files[log_file]
                    .get("sizes", {})
                    .get("original", {})
                    .get("bytes", 0)
                )
                if file_size > MAX_LOG_SIZE_BYTES:
                    size_mb = file_size / (1024 * 1024)
                    raise EntsoePipelineError(
                        f"CRITICAL OOM RISK: FMS log file '{log_file}' has grown too large "
                        f"({size_mb:.2f} MB, limit: 100.00 MB). "
                        f"Downloading this file in-memory may cause Out of Memory errors. "
                        f"Please redesign the metadata crawling architecture to stream or chunk this file."
                    )

        df_std = client.download_single_file(folder="", filename="Export_log_r3.csv")
        df_oce = client.download_single_file(
            folder="", filename="Export_oce_log_r3.csv"
        )
        logger.info(
            "Successfully downloaded FMS log files: Export_log_r3.csv (raw rows: %d), "
            "Export_oce_log_r3.csv (raw rows: %d) in %.2f seconds",
            len(df_std),
            len(df_oce),
            time.time() - t_start,
        )
    except EntsoePipelineError:
        raise
    except Exception as e:
        logger.exception(
            "Failed to download or parse log files from FMS: %s. Falling back to full scan.",
            e,
        )
        if full_scan_callback:
            full_scan_callback(
                env, is_test=is_test, is_force=False, domain_name=domain_name
            )
        else:
            logger.exception(
                "Fallback requested but no full_scan_callback was provided."
            )
        return

    # 3. Retrieve known files from database
    t_db = time.time()
    engine = create_engine(get_db_url())
    db_metadata = build_metadata()
    fms_files = db_metadata.tables["fms_files"]
    fms_folders = db_metadata.tables["fms_folders"]

    with engine.connect() as conn:
        db_file_rows = conn.execute(
            select(fms_files.c.name, fms_files.c.last_updated, fms_files.c.xxhash)
            .join(fms_folders, fms_folders.c.id == fms_files.c.folder_id)
            .where(fms_folders.c.environment == env.lower())
        ).fetchall()

    db_files = {
        strip_extension(row[0]): {
            "last_updated": parse_db_timestamp(row[1]),
            "xxhash": row[2],
        }
        for row in db_file_rows
    }

    # 4. Check folder crawl states. If a folder was never crawled, it must be fully crawled.
    with engine.connect() as conn:
        folder_rows = conn.execute(
            select(fms_folders.c.folder_path, fms_folders.c.crawled_at).where(
                fms_folders.c.environment == env.lower()
            )
        ).fetchall()

    folder_crawled_at = {}
    for path, crawled_at in folder_rows:
        leaf = path.strip("/").split("/")[-1]
        folder_crawled_at[leaf] = crawled_at

    logger.info(
        "Successfully retrieved %d files and %d folder states from database in %.2f seconds",
        len(db_files),
        len(folder_crawled_at),
        time.time() - t_db,
    )

    dirty_folders_to_leafs = {}  # Map of parent_folder -> set of leaf_paths
    for folder in active_folders:
        if not folder_crawled_at.get(folder):
            logger.info(
                "Folder '%s' has never been crawled. Falling back to full recursive crawl of this folder.",
                folder,
            )
            dirty_folders_to_leafs.setdefault(folder, set()).add(folder)

    # 5. Process standard logs (Export_log_r3.csv)
    logger.info("Scanning standard log 'Export_log_r3.csv' for changes...")
    std_records = []
    for _, row in df_std.iterrows():
        file_name = row.get("file_name")
        max_update = row.get("max_update_time(UTC)")
        if not file_name or pd.isna(file_name):
            continue
        # Find matching active folder
        matched_folder = None
        for folder in active_folders:
            if folder in file_name:
                matched_folder = folder
                break
        if matched_folder:
            std_records.append(
                {
                    "file_name": file_name,
                    "folder_name": matched_folder,
                    "max_update_time": parse_log_timestamp(max_update),
                }
            )

    std_records = [r for r in std_records if r["max_update_time"] is not None]
    std_records.sort(key=lambda x: x["max_update_time"], reverse=True)
    logger.info(
        "Found %d matched active records in Export_log_r3.csv.", len(std_records)
    )

    consecutive_matches = 0
    consecutive_matches_threshold = 3
    for record in std_records:
        file_base = strip_extension(record["file_name"])
        log_time = record["max_update_time"]
        parent_folder = record["folder_name"]

        db_record = db_files.get(file_base)
        if not db_record:
            leaf_path = resolve_exact_fms_folder(parent_folder, record["file_name"])
            logger.info(
                "New file detected in Export_log_r3.csv: %s. Marking leaf '%s' as dirty.",
                record["file_name"],
                leaf_path,
            )
            dirty_folders_to_leafs.setdefault(parent_folder, set()).add(leaf_path)
            consecutive_matches = 0
        else:
            db_time = db_record["last_updated"]
            if db_time is None or log_time > db_time:
                leaf_path = resolve_exact_fms_folder(parent_folder, record["file_name"])
                logger.info(
                    "Updated file detected in Export_log_r3.csv: %s (Log: %s > DB: %s). Marking leaf '%s' as dirty.",
                    record["file_name"],
                    log_time,
                    db_time,
                    leaf_path,
                )
                dirty_folders_to_leafs.setdefault(parent_folder, set()).add(leaf_path)
                consecutive_matches = 0
            else:
                consecutive_matches += 1
                logger.debug(
                    "File %s is up-to-date (consecutive matches: %d)",
                    record["file_name"],
                    consecutive_matches,
                )

        if consecutive_matches >= consecutive_matches_threshold:
            logger.info(
                "Hit %d consecutive matches in Export_log_r3.csv. Stopping scan.",
                consecutive_matches_threshold,
            )
            break

    # 6. Process Offered Capacity Evolution logs (Export_oce_log_r3.csv)
    logger.info(
        "Scanning Offered Capacity Evolution log 'Export_oce_log_r3.csv' for changes..."
    )
    oce_records = []
    for _, row in df_oce.iterrows():
        file_name = row.get("file_name")
        folder_name = row.get("folder_name")
        max_update = row.get("max_update_time(UTC)")
        if (
            not file_name
            or pd.isna(file_name)
            or not folder_name
            or pd.isna(folder_name)
        ):
            continue
        if folder_name in active_folders:
            oce_records.append(
                {
                    "file_name": file_name,
                    "folder_name": folder_name,
                    "max_update_time": parse_log_timestamp(max_update),
                }
            )

    oce_records = [r for r in oce_records if r["max_update_time"] is not None]
    oce_records.sort(key=lambda x: x["max_update_time"], reverse=True)
    logger.info(
        "Found %d matched active records in Export_oce_log_r3.csv.", len(oce_records)
    )

    consecutive_matches = 0
    for record in oce_records:
        file_base = strip_extension(record["file_name"])
        log_time = record["max_update_time"]
        parent_folder = record["folder_name"]

        db_record = db_files.get(file_base)
        if not db_record:
            leaf_path = resolve_exact_fms_folder(parent_folder, record["file_name"])
            logger.info(
                "New file detected in Export_oce_log_r3.csv: %s. Marking leaf '%s' as dirty.",
                record["file_name"],
                leaf_path,
            )
            dirty_folders_to_leafs.setdefault(parent_folder, set()).add(leaf_path)
            consecutive_matches = 0
        else:
            db_time = db_record["last_updated"]
            if db_time is None or log_time > db_time:
                leaf_path = resolve_exact_fms_folder(parent_folder, record["file_name"])
                logger.info(
                    "Updated file detected in Export_oce_log_r3.csv: %s (Log: %s > DB: %s). Marking leaf '%s' as dirty.",
                    record["file_name"],
                    log_time,
                    db_time,
                    leaf_path,
                )
                dirty_folders_to_leafs.setdefault(parent_folder, set()).add(leaf_path)
                consecutive_matches = 0
            else:
                consecutive_matches += 1
                logger.debug(
                    "File %s is up-to-date (consecutive matches: %d)",
                    record["file_name"],
                    consecutive_matches,
                )

        if consecutive_matches >= consecutive_matches_threshold:
            logger.info(
                "Hit %d consecutive matches in Export_oce_log_r3.csv. Stopping scan.",
                consecutive_matches_threshold,
            )
            break

    # 7. Perform targeted crawl phase for only the dirty leaf paths
    if not dirty_folders_to_leafs:
        logger.info("All active folders are completely up-to-date. No crawl needed.")
        return

    logger.info(
        "Crawling dirty paths for %d folders: %s",
        len(dirty_folders_to_leafs),
        list(dirty_folders_to_leafs.keys()),
    )

    api_counter = [0]
    processed_any = False

    try:
        for parent_folder, leaf_paths in dirty_folders_to_leafs.items():
            domain = folder_to_domain[parent_folder]
            parent_path = f"/TP_export/{parent_folder}/"

            # 7.1. Ensure parent folder entry exists in database
            try:
                with engine.begin() as conn:
                    stmt = select(fms_folders.c.id).where(
                        fms_folders.c.environment == env.lower(),
                        fms_folders.c.folder_path == parent_path,
                    )
                    row = conn.execute(stmt).fetchone()
                    if row:
                        folder_id = row[0]
                    else:
                        result = conn.execute(
                            fms_folders.insert().values(
                                environment=env.lower(),
                                domain=domain,
                                folder_path=parent_path,
                                item_count=0,
                                original_bytes=0,
                                compressed_bytes=0,
                                crawled_at=None,  # Not yet fully crawled
                            )
                        )
                        folder_id = result.inserted_primary_key[0]
            except Exception:
                logger.exception(
                    "Database error during folder initialization for '%s'. Skipping parent folder.",
                    parent_folder,
                )
                continue

            # 7.2. Crawl each leaf path and commit its files atomically to DB immediately
            all_leaves_succeeded = True

            for leaf_path in leaf_paths:
                logger.info("Executing targeted crawler on leaf folder: %s", leaf_path)
                try:
                    leaf_files = crawl_metadata_folder(
                        client=client,
                        folder=leaf_path,
                        root_files_by_name={},
                        api_counter=api_counter,
                        env=env,
                        root_dir="TP_export",
                    )

                    # 7.3. Atomic Bulk UPSERT: all files of this leaf in ONE round-trip.
                    # pg_insert with ON CONFLICT eliminates UniqueViolation on file_id
                    # and avoids the LBYL SELECT+INSERT/UPDATE anti-pattern.
                    if leaf_files:
                        logger.info(
                            "Syncing %d files to DB via atomic UPSERT for leaf '%s'",
                            len(leaf_files),
                            leaf_path,
                        )
                        upsert_data = [
                            {
                                "file_id": f["file_id"],
                                "folder_id": folder_id,
                                "name": f["name"],
                                "original_bytes": f["sizes"]["original"]["bytes"],
                                "compressed_bytes": f["sizes"]["compressed"]["bytes"],
                                "last_updated": f["last_updated"],
                                "xxhash": f["xxhash"],
                            }
                            for f in leaf_files
                        ]
                        insert_stmt = pg_insert(fms_files).values(upsert_data)
                        upsert_stmt = insert_stmt.on_conflict_do_update(
                            index_elements=[fms_files.c.file_id],
                            set_={
                                "folder_id": insert_stmt.excluded.folder_id,
                                "name": insert_stmt.excluded.name,
                                "original_bytes": insert_stmt.excluded.original_bytes,
                                "compressed_bytes": insert_stmt.excluded.compressed_bytes,
                                "last_updated": insert_stmt.excluded.last_updated,
                                "xxhash": insert_stmt.excluded.xxhash,
                            },
                        )
                        with engine.begin() as conn:
                            conn.execute(upsert_stmt)
                        processed_any = True

                except Exception:
                    logger.exception(
                        "Error crawling leaf folder '%s' on environment %s. Skipping leaf.",
                        leaf_path,
                        env,
                    )
                    all_leaves_succeeded = False

            # 7.4. Recalculate parent folder aggregate statistics based on all committed files
            try:
                with engine.begin() as conn:
                    agg_row = conn.execute(
                        select(
                            func.count(fms_files.c.file_id),
                            func.sum(fms_files.c.original_bytes),
                            func.sum(fms_files.c.compressed_bytes),
                        ).where(fms_files.c.folder_id == folder_id)
                    ).fetchone()

                    item_count = agg_row[0] or 0
                    original_bytes = agg_row[1] or 0
                    compressed_bytes = agg_row[2] or 0

                    update_values: dict = {
                        "item_count": item_count,
                        "original_bytes": original_bytes,
                        "compressed_bytes": compressed_bytes,
                    }
                    # Mark folder as fully crawled ONLY if every leaf succeeded.
                    # If any leaf errored, leave crawled_at=None so the next run re-visits.
                    if all_leaves_succeeded:
                        update_values["crawled_at"] = datetime.now(tz=UTC)

                    conn.execute(
                        fms_folders.update()
                        .where(fms_folders.c.id == folder_id)
                        .values(**update_values)
                    )

                logger.info(
                    "Checkpoint saved for parent folder '%s' (files: %d, size: %.4f MB, fully_crawled: %s)",
                    parent_folder,
                    item_count,
                    original_bytes / (1024 * 1024),
                    all_leaves_succeeded,
                )
            except Exception:
                logger.exception(
                    "Failed to save aggregate checkpoint for parent folder '%s'.",
                    parent_folder,
                )

    except KeyboardInterrupt:
        # Graceful degradation: user pressed Ctrl+C mid-crawl.
        # All leaves processed so far are already committed to DB (atomic per-leaf commits).
        # The current parent folder's aggregate may be partially updated — that is acceptable.
        # Folders where crawled_at=None will be re-visited on the next run automatically.
        logger.warning(
            "KeyboardInterrupt received. Crawl stopped after %d API requests. "
            "Progress committed to DB. Incomplete folders will resume on the next run.",
            api_counter[0],
        )

    finally:
        # ANALYZE always runs — even on Ctrl+C — to keep the query planner healthy
        # for whatever data was committed during this (possibly partial) run.
        if processed_any:
            logger.info(
                "Running ANALYZE on fms_files to refresh query planner statistics..."
            )
            with engine.connect() as conn:
                conn.execute(text("ANALYZE fms_files;"))
                conn.commit()

    logger.info(
        "Incremental delta metadata refresh completed. Total API requests: %d",
        api_counter[0],
    )
