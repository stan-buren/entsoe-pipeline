---
trigger: always_on
---

# We use uv in our project.

run scripts using `uv run`, not vanilla `python` or `python3`.

> Good: `uv run python tests/pre_commit/validate_adrs.py`

> Bad: `python tests/pre_commit/validate_adrs.py

See `pyproject.toml`