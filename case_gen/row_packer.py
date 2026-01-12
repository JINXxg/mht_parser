# case_gen/row_packer.py
from typing import Dict, Any, List
from pathlib import Path
import json

def make_row_payload(table, table_index: int, row_index: int) -> Dict[str, Any]:
    """
    table: 你的 TableBlock（含 schema/rows/meta）
    """
    table_id = f"T{table_index}"
    row_id = f"{table_id}-R{row_index}"

    anchor = None
    if getattr(table, "meta", None):
        anchor = table.meta.get("anchor")

    return {
        "anchor": anchor,
        "table_id": table_id,
        "row_id": row_id,
        "row_index": row_index,
        "schema": list(table.schema),
        "row": dict(table.rows[row_index]),
    }

def dump_row_payloads(tables: List[Any], out_path: str) -> None:
    """
    tables: TableBlock 列表（每个包含 schema, rows, meta.anchor）
    out_path: e.g. jobs/xxx/case_inputs/row_payloads.jsonl
    """
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    with out.open("w", encoding="utf-8") as f:
        for t_idx, table in enumerate(tables):
            for r_idx in range(len(table.rows)):
                payload: Dict[str, Any] = make_row_payload(table, table_index=t_idx, row_index=r_idx)
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")