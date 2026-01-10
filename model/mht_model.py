from __future__ import annotations
from typing import Any, Dict, Optional
from dataclasses import dataclass

@dataclass
class PartRecord:
    part_index: int
    content_type: str
    content_location: Optional[str]
    content_id: Optional[str]
    filename: str
    size_bytes: int
    sha256: str
    headers: dict[str, str]
    payload_path: Optional[str] = None