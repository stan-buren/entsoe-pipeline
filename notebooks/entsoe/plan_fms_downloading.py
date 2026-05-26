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


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Initialize fms session
    """)
    return


@app.cell
def _():
    from entsoe_pipeline import ConfigurableEntsoeFileClient, get_env_config


    # enviroment configuration
    env_config = get_env_config()

    environment_name = env_config.environment_name
    username = env_config.email
    pwd = env_config.password
    base_url = env_config.base_url
    token_url = env_config.token_url



    fms_client = ConfigurableEntsoeFileClient(username=username, pwd=pwd, base_url=base_url, token_url=token_url)
    return environment_name, fms_client


@app.cell
def _(environment_name):
    if environment_name != "IOP":
        raise ValueError(
            f"[ERROR] your current enviroment is '{environment_name}'"
            f"run 'just dev' and switch to 'IOP'"
        )
    return


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
def _(download_latest_df_by_index, folders):
    df_units, units_files_sorted = download_latest_df_by_index(folders, index=1)
    return (units_files_sorted,)


@app.cell
def _(units_files_sorted):
    units_files_sorted
    return


@app.cell
def _(fms_client):
    import json
    import logging
    from typing import List, Dict, Any
    import requests
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

    # 1. НАБЛЮДАЕМОСТЬ (Observability)
    # Забываем про голые print() для системной информации. В проде мы должны писать логи.
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    logger = logging.getLogger(__name__)

    # 2. ОТКАЗОУСТОЙЧИВОСТЬ (Resilience)
    # Если API ENTSO-E моргнет, мы не падаем. Мы ждем 2, 4, 8 секунд и пробуем снова (до 5 раз).
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.exceptions.RequestException),
        reraise=True
    )
    def fetch_folder_page(path: str, page_index: int, page_size: int = 1000) -> Dict[str, Any]:
        """
        Атомарная функция: делает ровно один HTTP-запрос за одной страницей.
        """
        logger.debug(f"Запрос страницы {page_index} для пути {path}...")

        response = fms_client.session.post(
            fms_client.BASEURL + "listFolder",
            data=json.dumps({
                "path": path,
                "sorterList": [{"key": "name", "ascending": True}],
                "pageInfo": {"pageIndex": page_index, "pageSize": page_size},
            }),
            headers={
                "Authorization": f"Bearer {fms_client.access_token}",
                "Content-Type": "application/json",
            },
            proxies=fms_client.proxies,
            timeout=fms_client.timeout,
        )
        # Если вернется 503 или 429, это бросит исключение, и tenacity автоматически уйдет в ретрай
        response.raise_for_status()
        return response.json()

    # 3. МАСШТАБИРУЕМОСТЬ (Scalability)
    # Типизация (-> List[str]) обязательна. Data Engineer всегда должен знать, что возвращает функция.
    def list_path_production(path: str, page_size: int = 1000) -> List[str]:
        """
        Собирает все файлы из папки через пагинацию.
        Никаких хардкодов на 5000 элементов.
        """
        all_items = []
        page_index = 0

        while True:
            data = fetch_folder_page(path, page_index, page_size)
            current_items = data.get("contentItemList", [])

            all_items.extend([x["name"] for x in current_items])

            # Защита от бесконечного цикла: если сервер вернул меньше записей, чем размер страницы,
            # значит, мы вычитали самый конец списка.
            if len(current_items) < page_size:
                break

            page_index += 1

        logger.info(f"Успешно собрано метаданных: {len(all_items)} файлов из директории {path}")
        return all_items

    # ==========================================
    # ЗАПУСК ИНДЖЕШНА
    # ==========================================

    logger.info("=== СТАРТ СБОРА: ACTIVE FOLDERS (/TP_export/) ===")
    active_folders = list_path_production("/TP_export/")

    # Для наглядности в ноутбуке выведем первые 5, чтобы не рвать интерфейс Marimo длинным выводом
    for folder in sorted(active_folders)[:5]:
        print(f" - {folder}")
    if len(active_folders) > 5:
        print(f"   ... и еще {len(active_folders) - 5} папок")

    logger.info("=== СТАРТ СБОРА: LEGACY FOLDERS (/TP_Legacy_Publications/) ===")
    legacy_folders = list_path_production("/TP_Legacy_Publications/")

    for folder in sorted(legacy_folders)[:5]:
        print(f" - {folder}")
    if len(legacy_folders) > 5:
        print(f"   ... и еще {len(legacy_folders) - 5} папок")
    return


if __name__ == "__main__":
    app.run()
