# case_gen/prompt_builder.py
from typing import List, Dict, Any

def build_row_prompt(payload: Dict[str, Any]) -> str:
    schema: List[str] = payload["schema"]
    row: Dict[str, str] = payload["row"]

    lines = []
    lines.append("你是测试工程师。请基于本行数据生成测试用例。")
    lines.append("规则：列名/标签仅用于理解字段含义，禁止为列名本身生成测试用例。测试点只能来自各列“值”以及值之间的约束关系。")
    lines.append("")
    lines.append(f"anchor: {payload.get('anchor')}")
    lines.append(f"table_id: {payload['table_id']}")
    lines.append(f"row_id: {payload['row_id']}")
    lines.append(f"row_index: {payload['row_index']}")
    lines.append("")
    lines.append("列标签（证据，不生成用例）： " + " / ".join(schema))
    lines.append("本行数据：")

    for col in schema:
        v = (row.get(col) or "").strip()
        if v:
            lines.append(f"- {col}：{v}")
        else:
            lines.append(f"- {col}：<EMPTY>")
    lines.append("")
    lines.append("请输出 JSON，必须原样回传 row_id/table_id/anchor。")
    lines.append('输出格式：{"anchor": "...", "table_id":"...", "row_id":"...", "cases":[{"title":"...","steps":[...],"expected":[...],"priority":"P0|P1|P2"}]}')
    return "\n".join(lines)