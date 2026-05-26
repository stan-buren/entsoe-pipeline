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

import marimo

__generated_with = "0.23.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _():
    from pyprojroot.here import here as project_root

    return (project_root,)


@app.cell
def _():
    import os
    from dotenv import load_dotenv
    from entsoe import EntsoePandasClient
    from entsoe.files import EntsoeFileClient
    from entsoe_pipeline import ENV_FILE

    load_dotenv(ENV_FILE)

    token = os.environ.get("ENTSOE_TOKEN")

    username = os.environ.get("ENTSOE_EMAIL")

    pwd = os.environ.get("ENTSOE_PASSWORD")

    client = EntsoePandasClient(api_key=token)

    fms_client = EntsoeFileClient(username=username, pwd=pwd)
    return (fms_client,)


@app.cell
def _(fms_client):
    def download_latest_df_by_index(folders_list, index):

        target_folder = folders_list[index]

        file_list = fms_client.list_folder(target_folder)

        file_list_sorted = sorted(file_list.keys())
        target_file = file_list_sorted[-1]

        dataframe = fms_client.download_single_file(
            folder=target_folder, filename=target_file
        )
        return dataframe, file_list_sorted

    return (download_latest_df_by_index,)


@app.cell
def _():
    folders = [
        "EnergyPrices_12.1.D_r3",
        "ActualTotalLoad_6.1.A_r3",
        "AggregatedGenerationPerType_16.1.B_C_r3",
        "BalancingEnergyBids_12.3.B_C_r3",
        "ProductionAndGenerationUnits_r3",
    ]
    return (folders,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Explore units
    """)
    return


@app.cell
def _(download_latest_df_by_index, folders):
    df_units, units_files_sorted = download_latest_df_by_index(folders, index=4)
    return (df_units,)


@app.cell
def _(df_units, mo):
    _df = mo.sql(
        """
        WITH active_production_units AS (
            -- Шаг 1: Схлопываем строки до уровня УНИКАЛЬНЫХ электростанций
            -- Выбираем DISTINCT только по колонкам самой СТАНЦИИ, игнорируя генераторы
            SELECT DISTINCT
                AreaDisplayName AS country,
                ProductionUnitCode,
                ProductionUnitType AS fuel_type,
                "ProductionUnitInstalledCapacity(MW)" AS capacity
            FROM df_units
            WHERE ProductionUnitType IS NOT NULL
              AND "ProductionUnitInstalledCapacity(MW)" > 0
              AND ProductionUnitStatus = 'COMMISSIONED'
              -- Фильтр времени
              AND CAST(ValidFrom AS TIMESTAMP) <= '2026-05-17 00:00:00'
              AND (ValidTo IS NULL OR CAST(ValidTo AS TIMESTAMP) > '2026-05-17 00:00:00')
        ),
        aggregated_capacity AS (
            -- Шаг 2: Теперь агрегируем чистые, не дублированные гигаватты
            SELECT country, fuel_type, SUM(capacity) AS total_mw
            FROM active_production_units
            GROUP BY country, fuel_type
        ),
        window_magic AS (
            -- Шаг 3: Накатываем наши оконные функции
            SELECT
                country,
                fuel_type,
                ROUND(total_mw, 0) AS capacity_mw,
                ROUND(100.0 * total_mw / SUM(total_mw) OVER (PARTITION BY fuel_type), 2) AS share_in_eu_fuel_pct,
                ROUND(100.0 * total_mw / SUM(total_mw) OVER (PARTITION BY country), 2) AS share_in_country_mix_pct,
                DENSE_RANK() OVER (PARTITION BY fuel_type ORDER BY total_mw DESC) AS rank_in_europe
            FROM aggregated_capacity
        )
        SELECT 
            fuel_type, 
            rank_in_europe, 
            country, 
            capacity_mw, 
            share_in_eu_fuel_pct AS "%_of_EU_fuel", 
            share_in_country_mix_pct AS "%_of_country_mix"
        FROM window_magic
        WHERE rank_in_europe <= 10
        ORDER BY fuel_type, rank_in_europe;
        """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Explore prices
    """)
    return


@app.cell
def _(download_latest_df_by_index, folders):
    df_prices, prices_files_sorted = download_latest_df_by_index(folders, index=0)
    return (df_prices,)


@app.cell
def _(df_prices):
    df_prices
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## explore currency
    """)
    return


@app.cell
def _(df_prices, mo):
    _df = mo.sql(
        """
        SELECT 
            Currency, 
            COUNT(*) as records_count,
            MIN("Price[Currency/MWh]") as min_raw_price,
            MAX("Price[Currency/MWh]") as max_raw_price
        FROM df_prices
        GROUP BY 1;
        """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    > ## Important:
    > Currency block has UAH
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Calculate avg prices per bidding zone
    """)
    return


@app.cell
def _(df_prices, mo):
    _df = mo.sql(
        """
        WITH
            normalized_prices AS (
                SELECT
                    AreaDisplayName AS bidding_zone,
                    "DateTime(UTC)" AS dt,
                    CASE
                        WHEN Currency = 'UAH' THEN "Price[Currency/MWh]" * 0.023 -- Переводим в EUR
                        ELSE "Price[Currency/MWh]"
                    END AS price_eur
                FROM
                    df_prices
            )
        SELECT
            bidding_zone,
            ROUND(AVG(price_eur), 2) AS avg_price_eur
        FROM
            normalized_prices
        GROUP BY
            1
        ORDER BY
            2 DESC;
        """
    )
    return


@app.cell(hide_code=True)
def _(df_prices, mo):
    _df = mo.sql(
        """
        WITH
            normalized_prices AS (
                -- Шаг 1: Нормализуем валюту
                SELECT
                    AreaDisplayName AS bidding_zone,
                    CASE
                        WHEN Currency = 'UAH' THEN "Price[Currency/MWh]" * 0.023
                        ELSE "Price[Currency/MWh]"
                    END AS price_eur
                FROM
                    df_prices
            ),
            binned_prices AS (
                -- Шаг 2: Группируем по ценовым корзинам (размер шага — 10 евро)
                SELECT
                    bidding_zone,
                    CAST(FLOOR(price_eur / 10.0) * 10 AS INTEGER) AS price_bin_eur,
                    COUNT(*) AS hours_count
                FROM
                    normalized_prices
                GROUP BY
                    1,
                    2
            )
            -- Шаг 3: Накатываем продвинутую аналитику через окна
        SELECT
            bidding_zone,
            price_bin_eur,
            hours_count,
            -- 1. Доля текущей корзины от общего объема часов в этой стране
            ROUND(
                100.0 * hours_count / SUM(hours_count) OVER (
                    PARTITION BY
                        bidding_zone
                ),
                2
            ) AS bin_share_pct,
            -- 2. Кумулятивная доля (Running Total от 0% до 100%) — идеальный график CDF
            ROUND(
                100.0 * SUM(hours_count) OVER (
                    w_zone ROWS BETWEEN UNBOUNDED PRECEDING
                    AND CURRENT ROW
                ) / SUM(hours_count) OVER (
                    PARTITION BY
                        bidding_zone
                ),
                2
            ) AS cumulative_share_pct,
            -- 3. Сглаживание Гауссианы: Скользящее среднее по центральному окну (предыдущая + текущая + следующая корзина)
            ROUND(
                AVG(hours_count) OVER (
                    w_zone ROWS BETWEEN 1 PRECEDING
                    AND 1 FOLLOWING
                ),
                1
            ) AS smoothed_hours_count
        FROM
            binned_prices
            -- Используем Именованное Окно (Named Window), чтобы не дублировать код PARTITION/ORDER BY
        WINDOW
            w_zone AS (
                PARTITION BY
                    bidding_zone
                ORDER BY
                    price_bin_eur ASC
            )
        ORDER BY
            bidding_zone,
            price_bin_eur;
        """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Explore energy load
    """)
    return


@app.cell
def _(download_latest_df_by_index, folders):
    df_load, load_files_sorted = download_latest_df_by_index(folders, index=1)
    return df_load, load_files_sorted


@app.cell
def _(df_load):
    df_load
    return


@app.cell
def _(load_files_sorted):
    load_files_sorted[::-1]
    return


if __name__ == "__main__":
    app.run()
