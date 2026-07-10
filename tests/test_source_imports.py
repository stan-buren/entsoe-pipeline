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

"""Quality gate to enforce imports cleanliness and prevent circular import hacks.

Checks that all Python modules declare imports strictly at the module scope
(at the top of the file). Mid-file imports (within functions or classes) are
prohibited as they mask circular dependency anti-patterns, with rare exceptions
whitelisted.
"""

from __future__ import annotations

import ast

from pathlib import Path

import pytest

from entsoe_pipeline import PROJECT_ROOT, SRC_DIR

# Whitelist of allowed mid-file imports (file name -> set of allowed module/import names)
# Generally used for lazy-loading heavy libraries or raising custom errors.
ALLOWED_MID_FILE_IMPORTS: dict[str, set[str]] = {
    # Legitimate lazy loading or late binding exceptions
    "disk_safety.py": {"entsoe_pipeline.logger.exceptions"},
    "preflight.py": {"entsoe_pipeline.lakehouse.generate_tree_for_my_entsoe_domains"},
    "landing.py": {"entsoe_pipeline.lakehouse.ensure_bucket_exists"},
    "s3_operations.py": {"entsoe_pipeline.logger.exceptions"},
    "generate_tree_for_my_entsoe_domains.py": {"entsoe_pipeline.logger.exceptions"},
    "client.py": {"entsoe_pipeline.logger.exceptions"},
    # Circular config dependency exceptions
    "buckets.py": {"entsoe_pipeline.config.paths"},
    "classifier.py": {"entsoe_pipeline.config.paths"},
    "domain_classifier.py": {"entsoe_pipeline.config.paths"},
    "hosts.py": {"entsoe_pipeline.config.paths"},
    "lakehouse.py": {"entsoe_pipeline.config.paths"},
    "pipeline.py": {"entsoe_pipeline.config.paths"},
    "ports.py": {"entsoe_pipeline.config.paths"},
    "region.py": {"entsoe_pipeline.config.paths"},
    "switch.py": {"entsoe_pipeline.config.paths"},
    "urls.py": {"entsoe_pipeline.config.paths"},
    "volumes.py": {"entsoe_pipeline.config.paths"},
    "warning.py": {"entsoe_pipeline.config.paths"},
    "config_loader.py": {
        "entsoe_pipeline.config.paths",
        "sqlalchemy",
        "entsoe_pipeline.db",
    },
    "env_resolver.py": {
        "entsoe_pipeline.config.paths",
        "entsoe_pipeline.config.config_loader",
    },
    # Orchestrators and generator exceptions
    "ftp_map_collector.py": {"entsoe_pipeline.config.paths"},
    "landing_bucket_schema.py": {"entsoe_pipeline.logger"},
    "my_entsoe_domains.py": {"entsoe_pipeline.logger.yml_observability"},
}


def find_all_source_modules() -> list[Path]:
    """Retrieves all Python modules within the main source package.

    Returns:
        list[Path]: List of Path objects pointing to Python files.
    """
    source_files = list(SRC_DIR.rglob("*.py"))
    return sorted(source_files)


class ImportVisitor(ast.NodeVisitor):
    """AST visitor to audit imports position within the module."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.context_stack = ["module"]
        self.mid_file_violations = []

    def visit_FunctionDef(self, node):
        """Audits function definitions."""
        self.context_stack.append("function")
        self.generic_visit(node)
        self.context_stack.pop()

    def visit_AsyncFunctionDef(self, node):
        """Audits async function definitions."""
        self.context_stack.append("function")
        self.generic_visit(node)
        self.context_stack.pop()

    def visit_ClassDef(self, node):
        """Audits class definitions."""
        self.context_stack.append("class")
        self.generic_visit(node)
        self.context_stack.pop()

    def register_import(self, node, imported_module: str):
        """Registers an import and audits its scope."""
        # Enforce imports are only at the module level
        if self.context_stack[-1] != "module":
            allowed_imports = ALLOWED_MID_FILE_IMPORTS.get(self.file_path.name, set())
            if not any(imported_module.startswith(aimp) for aimp in allowed_imports):
                self.mid_file_violations.append(
                    f"Line {node.lineno}: import of '{imported_module}' is inside a {self.context_stack[-1]}"
                )

    def visit_Import(self, node):
        """Audits import statements."""
        for name in node.names:
            self.register_import(node, name.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """Audits from-import statements."""
        if node.module:
            self.register_import(node, node.module)
        self.generic_visit(node)


# =============================================================================
# QUALITY GATE TESTS: MID-FILE IMPORTS CONVENTION AUDIT
# =============================================================================


@pytest.mark.parametrize("file_path", find_all_source_modules())
def test_python_module_imports_cleanliness(file_path: Path) -> None:
    """Audits the module to enforce top-level imports and block mid-file import hacks.

    Ensures no mid-file imports inside classes/functions (unless whitelisted).
    """
    # Arrange
    assert file_path.exists(), f"Source file does not exist at: {file_path}"
    content = file_path.read_text(encoding="utf-8")

    # Act
    try:
        tree = ast.parse(content, filename=str(file_path))
    except SyntaxError as e:
        pytest.fail(f"Syntax error in Python module {file_path.name}: {e}")

    visitor = ImportVisitor(file_path)
    visitor.visit(tree)

    # Assert
    if visitor.mid_file_violations:
        error_msg = ["Mid-file import violations found:"]
        for violation in visitor.mid_file_violations:
            error_msg.append(f"  • {violation}")
        pytest.fail(
            f"Imports validation failed for [ {file_path.relative_to(PROJECT_ROOT)} ]:\n"
            + "\n".join(error_msg)
        )
