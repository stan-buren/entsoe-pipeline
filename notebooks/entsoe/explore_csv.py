import marimo

__generated_with = "0.23.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _():
    import duckdb

    return (duckdb,)


@app.cell
def _():
    from pyprojroot.here import here as project_root

    data_dir = project_root(".data")

    data_dir
    return data_dir, project_root


@app.cell
def _(data_dir):
    data_files = {file.stem: str(file) for file in data_dir.glob("*.csv")}
    return (data_files,)


@app.cell
def _(data_files):
    import pprint

    pprint.pprint(data_files)
    return


@app.cell
def _(data_files, duckdb):
    duckdb.read_csv(data_files["inventory_of_generation_2019"])
    return


@app.cell
def _():
    from entsoe import EntsoeRawClient

    from entsoe import EntsoePandasClient

    return EntsoePandasClient, EntsoeRawClient


@app.cell
def _(EntsoePandasClient, EntsoeRawClient, project_root):
    import os
    from dotenv import load_dotenv
    import pandas as pd

    dotenv_path = project_root(".env")

    load_dotenv(dotenv_path)

    token = os.environ.get("ENTSOE_TOKEN")

    client_raw = EntsoeRawClient(api_key=token)

    client = EntsoePandasClient(api_key=token)
    return client, os, pd


@app.cell
def _(pd):
    start = pd.Timestamp("20260515", tz="Europe/Brussels")
    end = pd.Timestamp("20260517", tz="Europe/Brussels")
    country_code = "BE"  # Belgium
    country_code_from = "FR"  # France
    country_code_to = "DE_LU"  # Germany-Luxembourg
    type_marketagreement_type = "A01"
    contract_marketagreement_type = "A01"
    process_type = "A51"
    return country_code, end, start


@app.cell
def _(client, country_code, end, start):
    client.query_day_ahead_prices(country_code, start, end)
    return


@app.cell
def _(os):
    from entsoe.files import EntsoeFileClient

    username = os.environ.get("ENTSOE_EMAIL")

    pwd = os.environ.get("ENTSOE_PASSWORD")

    fms_client = EntsoeFileClient(username=username, pwd=pwd)

    folder_name = "BalancingEnergyBids_12.3.B_C_r3"
    file_list = fms_client.list_folder(folder_name)

    print(f"Найдено файлов: {len(file_list)}")

    return file_list, fms_client, folder_name


@app.cell
def _(file_list, fms_client, folder_name):
    # Берем первый файл из списка (самый свежий или случайный)
    # file_list — это словарь {имя_файла: id_файла}
    filenames = list(file_list.keys())
    target_file = filenames[0]

    print(f"Скачиваю файл: {target_file}")

    # Скачиваем (это может занять несколько секунд, файлы в FMS крупные)
    df_bids = fms_client.download_single_file(folder=folder_name, filename=target_file)

    # Посмотрим, сколько там реально строк
    print(f"Загружено строк: {len(df_bids)}")
    df_bids.head()
    return (df_bids,)


@app.cell
def _(df_bids):
    df_bids.tail()
    return


@app.cell
def _(df_bids):
    df_bids.info()
    return


@app.cell
def _(df_bids, mo):
    _df = mo.sql(
        """
        SELECT AreaCode, COUNT(*) as count 
            FROM df_bids 
            GROUP BY AreaCode 
            ORDER BY count DESC 
            LIMIT 10
        """
    )
    return


@app.cell
def _(df_bids, mo):
    _df = mo.sql(
        """
        SELECT 
            AreaDisplayName, 
            round(avg("Price[Currency/MWh]"), 2) as avg_price,
            min("Price[Currency/MWh]") as min_price,
            max("Price[Currency/MWh]") as max_price,
            count(*) as bid_count
        FROM df_bids
        WHERE "Price[Currency/MWh]" IS NOT NULL
        GROUP BY AreaDisplayName
        ORDER BY avg_price DESC;
        """
    )
    return


@app.cell
def _(df_bids, mo):
    _df = mo.sql(
        """
        SELECT 
            Direction, 
            count(*) as total_bids,
            round(sum("Volume[MW]"), 0) as total_volume_mw,
            round(avg("Price[Currency/MWh]"), 2) as avg_price
        FROM df_bids
        GROUP BY Direction;
        """
    )
    return


@app.cell
def _(df_bids, mo):
    _df = mo.sql(
        """
        SELECT 
            AreaDisplayName, 
            "Volume[MW]", 
            "Price[Currency/MWh]", 
            Direction,
            "DeliveryPeriodStart(UTC)"
        FROM df_bids
        ORDER BY "Volume[MW]" DESC
        LIMIT 20;
        """
    )
    return


@app.cell
def _(df_bids, mo):
    _df = mo.sql(
        """
        SELECT "Price[Currency/MWh]", "Currency" FROM df_bids 
        WHERE "Price[Currency/MWh]" < 0
        GROUP BY 1, 2
        ORDER BY "Price[Currency/MWh]" ASC
        LIMIT 100;
        """
    )
    return


@app.cell
def _(df_bids, mo):
    _df = mo.sql(
        """
        -- Считаем, сколько времени рынок висел на "ценовом дне"
        SELECT 
            "Price[Currency/MWh]" as price,
            count(*) as intervals_count,
            (count(*) * 15) as total_minutes,
            round((count(*) * 15) / 60.0, 2) as total_hours,
            min("DeliveryPeriodStart(UTC)") as first_seen,
            max("DeliveryPeriodEnd(UTC)") as last_seen
        FROM df_bids
        WHERE AreaDisplayName = 'DE-LU' 
          AND "Price[Currency/MWh]" = (SELECT min("Price[Currency/MWh]") FROM df_bids WHERE AreaDisplayName = 'DE-LU')
        GROUP BY 1;
        """
    )
    return


@app.cell
def _(df_bids, mo):
    _df = mo.sql(
        """
        SELECT 
            "Price[Currency/MWh]" as price,
            count(*) as frequency,
            min("DeliveryPeriodStart(UTC)") as sample_time
        FROM df_bids
        WHERE AreaDisplayName = 'DE-LU' AND "Price[Currency/MWh]" < 0
        GROUP BY 1
        ORDER BY 1 ASC
        LIMIT 20;
        """
    )
    return


@app.cell
def _(df_bids, mo):
    _df = mo.sql(
        """
        SELECT 
            AreaDisplayName,
            "Price[Currency/MWh]" as price,
            -- Считаем уникальные 15-минутки
            count(DISTINCT "DeliveryPeriodStart(UTC)") as unique_intervals,
            -- Реальное время в часах (интервалы * 15 мин / 60)
            round((count(DISTINCT "DeliveryPeriodStart(UTC)") * 15) / 60.0, 2) as actual_hours_at_floor,
            -- Плотность: сколько в среднем заявок висело на этом уровне одновременно
            round(count(*) * 1.0 / count(DISTINCT "DeliveryPeriodStart(UTC)"), 1) as bids_density
        FROM df_bids
        WHERE AreaDisplayName = 'DE-LU' 
          AND "Price[Currency/MWh]" = -15000
        GROUP BY 1, 2;
        """
    )
    return


@app.cell
def _(df_bids, mo):
    _df = mo.sql(
        """
        WITH unique_pain_intervals AS (
            -- Сначала достаем только УНИКАЛЬНЫЕ моменты времени, 
            -- когда хотя бы один бедолага выставил -15 000
            SELECT DISTINCT "DeliveryPeriodStart(UTC)"
            FROM df_bids
            WHERE AreaDisplayName = 'DE-LU' 
              AND "Price[Currency/MWh]" = -15000
        )
        -- А теперь просто считаем количество этих 15-минуток
        SELECT 
            count(*) as total_intervals,
            (count(*) * 15 / 60.0) as real_hours_at_the_floor
        FROM unique_pain_intervals;
        """
    )
    return


if __name__ == "__main__":
    app.run()
