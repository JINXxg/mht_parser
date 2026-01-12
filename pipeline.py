#pipeline.py
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional

from mht_parser.structure_parser import parse_mht_to_structure
from mht_parser.part_index import PartIndex
from semantics.html_semantics import extract_tables_with_anchor
from semantics.image_semantics import OcrInterpreter
from model.mht_model import PartRecord

def _dump_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    def default(o):
        if is_dataclass(o):
            return asdict(o)
        return TypeError(f"Not JSON serializable: {type(o)}")
    
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2, default=default),encoding = "utf-8")

def _find_root_html_part(parts: List[PartRecord]) -> Optional[PartRecord]:
    for p in parts:
        if p.content_type == "text/html":
            return p
        
    for p in parts:
        if p.filename.lower().endswith(".html"):
            return p
    return None

def _load_html(root_part: PartRecord) -> str:
    if not root_part.payload_path:
        raise RuntimeError("root HTML part has no payload_path. Enable dump_dir so payloads are written.")
    
    html_bytes = Path(root_part.payload_path).read_bytes()

    for enc in ("utf-8","utf-8-sig", "gb18030", "latin1"):
        try:
            return html_bytes.decode(enc)
        except Exception:
            continue

    return html_bytes.decode("utf-8",errors="replace")

def run_pipeline(mht_path: str, job_dir: str) -> None:
    job_root = Path(job_dir)
    job_root.mkdir(parents=True, exist_ok=True)

    # 1) 结构解析 + parts 落盘 + manifest.json
    parts = parse_mht_to_structure(mht_path, dump_dir=str(job_root / "structure"))

    # 2) 建资源索引（img src -> part）
    part_index = PartIndex.build(parts)

    # 3) 找 root HTML 并加载
    root_html = next((p for p in parts if p.content_type == "text/html"), None)
    if not root_html or not root_html.payload_path:
        raise RuntimeError("root HTML not found or not dumped to disk")
    html_bytes = Path(root_html.payload_path).read_bytes()
    html = html_bytes.decode("utf-8", errors="replace")

    # 4) OCR 解释器（先跑通：全用 OCR）
    ocr = OcrInterpreter(engine="tesseract", lang="chi_sim+eng")

    # 5) 语义提取（blocks）
    # 4) 语义：只抽顶层表格 + anchor
    tables = extract_tables_with_anchor(html, part_index, image_interpreter=ocr)
    blocks = tables
    

    # 6) 诊断信息：计数 + 未映射图片
    img_placeholders = 0
    for t in tables:
        for row in t.rows:
            for v in row.values():
                if isinstance(v, str) and "[IMG:" in v:
                    img_placeholders += v.count("[IMG:")

    diagnostics: Dict[str, Any] = {
        "table_count": len(tables),
        "rows_per_table": [len(t.rows) for t in tables],
        "img_placeholders": img_placeholders,
        "anchors": [t.meta.get("anchor") if t.meta else None for t in tables],
    }
    sem_dir = job_root / "semantics"
    _dump_json(sem_dir / "tables.json", tables)
    _dump_json(sem_dir / "diagnostics.json", diagnostics)

    # 7) 语义结果落盘
    # sem_dir = job_root / "semantics"
    _dump_json(sem_dir / "blocks.json", blocks)

    # tables_only = [b for b in blocks if getattr(b, "kind", None) == "table"]
    # _dump_json(sem_dir / "tables.json", tables_only)

    # _dump_json(sem_dir / "diagnostics.json", diagnostics)


if __name__ == "__main__":

    run_pipeline("大宽基地成就馆升级.mht", "job_大宽基地成就馆升级")
    # parts = parse_mht_to_structure(
    #     "大宽基地成就馆升级.mht",
    #     dump_dir="结构目录_大宽基地成就馆升级",
    # )
    # print("parts:", len(parts))
    # print("first part:", parts[0])