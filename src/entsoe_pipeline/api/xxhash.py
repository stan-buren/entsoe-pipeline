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

"""ENTSO-E Data Pipeline xxHash Idempotency Fingerprint Module.

Provides pure utility functions to compute 128-bit xxHash (xxh3_128) digests
representing unique file and directory states, serving as reliable watermarks.
"""

from __future__ import annotations

import xxhash

# =============================================================================
# HASHING UTILITIES
# =============================================================================


def calculate_idempotency_hash(
    name: str,
    size_bytes: int,
    last_updated: str,
) -> str:
    """Computes a 128-bit xxHash signature for a file's state.

    Combines the file name, original physical size in bytes, and server-side
    modification timestamp into a unique signature, then hashes it. If any
    of these attributes change, the resulting xxHash changes instantly.

    Args:
        name: Name of the file or directory.
        size_bytes: Original physical file size in bytes.
        last_updated: Server-side ISO/UTC update timestamp.

    Returns:
        str: 128-bit hex digest signature.
    """
    idempotency_str = f"{name}_{size_bytes}_{last_updated}"
    return xxhash.xxh3_128(idempotency_str.encode("utf-8")).hexdigest()
