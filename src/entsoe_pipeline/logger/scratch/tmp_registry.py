#!/usr/bin/env python3

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

"""Registry tool — создание и управление реестром торрентов.

Использование:
  python3 registry_tool.py scan         # сканировать complete/, создать YAML-заготовки
  python3 registry_tool.py status       # показать статус: сколько готово/нет
  python3 registry_tool.py show <dir>   # показать YAML для торрента
  python3 registry_tool.py edit <dir>   # открыть YAML для редактирования ($EDITOR)

Реестр лежит в: /mnt/data_lake/developer_space/config/torrents_registry/
"""
