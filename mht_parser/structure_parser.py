import hashlib
import json
import mimetypes
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Union
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model.mht_model import PartRecord

from email.parser import BytesParser
from email import policy

def _safe_filename(name: str) -> str:
    name = name.strip().strip('"')
    name = re.sub(r"[\\/:*?\"<>|]", "_", name)
    return name[:180] if len(name) > 180 else name


def _filename_from_location(content_location: Optional[str]) -> Optional[str]:
    if not content_location:
        return None

    # WPS 里常见 file:///... 这种 URI
    try:
        parsed = urlparse(content_location)
        if parsed.scheme in ("file", "http", "https"):
            base = Path(parsed.path).name
        else:
            base = Path(content_location).name
    except Exception:
        base = Path(content_location).name

    base = _safe_filename(base) if base else ""
    return base or None


def _ensure_extension(filename: str, content_type: str) -> str:
    # 如果没有扩展名，按 content_type 猜一个
    if Path(filename).suffix:
        return filename
    ext = mimetypes.guess_extension(content_type) or ""
    return filename + (ext if ext else ".bin")

def parse_mht_to_structure(
    mht_path: Union[str, Path],
    dump_dir: Optional[Union[str, Path]] = None,
) -> list[PartRecord]:
    mht_path = Path(mht_path)
    raw = mht_path.read_bytes()
    msg = BytesParser(policy=policy.default).parsebytes(raw)

    parts: list[PartRecord] = []

    dump_root = Path(dump_dir) if dump_dir else None
    assets_dir = None
    if dump_root:
        dump_root.mkdir(parents=True, exist_ok=True)
        assets_dir = dump_root / "parts"
        assets_dir.mkdir(parents=True, exist_ok=True)

    # 遍历所有非 multipart part
    logical_index = 0
    for part in msg.walk():
        if part.is_multipart():
            continue

        content_type = part.get_content_type()
        content_location = part.get("Content-Location")
        content_id = part.get("Content-ID")
        headers = {k: str(v) for (k, v) in part.items()}

        payload = part.get_payload(decode=True) or b""
        size_bytes = len(payload)
        sha256 = hashlib.sha256(payload).hexdigest()

        # 生成落盘文件名
        base = _filename_from_location(content_location) or f"part_{logical_index:03d}"
        base = _ensure_extension(base, content_type)
        filename = base

        payload_path = None
        if assets_dir is not None:
            # 用 hash 前缀 + 序号避免重名，且便于定位
            final_name = f"{logical_index:03d}_{sha256[:10]}_{filename}"
            out_path = assets_dir / final_name
            out_path.write_bytes(payload)
            payload_path = str(out_path)

        rec = PartRecord(
            part_index=logical_index,
            content_type=content_type,
            content_location=content_location,
            content_id=content_id,
            filename=filename,
            size_bytes=size_bytes,
            sha256=sha256,
            headers=headers,
            payload_path=payload_path,
        )
        parts.append(rec)
        logical_index += 1

    # 把结构清单落盘（不包含二进制，只保存元数据/路径）
    if dump_root:
        manifest = {
            "source_file": str(mht_path),
            "root_content_type": msg.get_content_type(),
            "is_multipart": msg.is_multipart(),
            "part_count": len(parts),
            "parts": [asdict(p) for p in parts],
        }
        (dump_root / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return parts


# if __name__ == "__main__":
#     parts = parse_mht_to_structure(
#         ".\\大宽基地成就馆升级.mht",
#         dump_dir="结构目录_大宽基地成就馆升级",
#     )
#     print("parts:", len(parts))
#     print("first part:", parts[0])