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

"""Structured JSON formatter for application logs."""

from __future__ import annotations

import json
import logging


class JsonFormatter(logging.Formatter):
    """A custom logging Formatter that serializes records into structured JSON objects.

    Useful for containerized production environments where logs are scraped,
    aggregated, and indexed by central monitoring stacks (e.g., Elasticsearch, Loki).
    """

    def format(self, record: logging.LogRecord) -> str:
        """Formats the LogRecord as a single-line JSON string."""
        payload = {
            "timestamp": self.formatTime(record, self.datefmt),
            "logger": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
        }

        # Automatically capture stack trace info if an exception is logged
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        # Extract any dynamic context passed via the 'extra' keyword argument
        # while skipping the standard LogRecord attributes.
        standard_attrs = {
            "args",
            "asctime",
            "created",
            "exc_info",
            "exc_text",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "message",
            "msg",
            "name",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "thread",
            "threadName",
        }
        extra_attrs = {
            k: v for k, v in record.__dict__.items() if k not in standard_attrs
        }
        payload.update(extra_attrs)

        return json.dumps(payload, ensure_ascii=False)
