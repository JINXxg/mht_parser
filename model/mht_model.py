from __future__ import annotations
from typing import Any, Dict, Optional, List
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


@dataclass
class Block:
    kind: str   # "text" | "table" | "image"
    order: int

@dataclass
class TextBlock(Block):
    text: str

@dataclass
class ImageBlock(Block):
    src: str
    part_sha256: Optional[str] = None
    payload_path: Optional[str] = None
    extracted_text: Optional[str] = None
    method: Optional[str] = None

    
@dataclass
class TableBlock:
    kind: str 
    order: int
    schema: List[str]
    rows: List[Dict[str, str]]
    meta: Optional[Dict[str, Any]] = None

@dataclass
class OcrResult:
    text: str
    method: str = "tesseract"
    error: Optional[str] = None