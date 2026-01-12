from dataclasses import dataclass
import re
from typing import List, Optional, Protocol, Dict,Any
from bs4 import Tag, NavigableString

from mht_parser.part_index import PartIndex
from model.mht_model import PartRecord, TableBlock
class ImageInterpreter(Protocol):
    def interpret(self, image_path: str) -> str:
        ...
    
# @dataclass
# class TableBlock:
#     kind: str 
#     order: int
#     schema: List[str]
#     rows: List[Dict[str, str]]
#     meta: Optional[Dict[str, Any]] = None

_RE_WS = re.compile(r"\s+")

def _ocr_ok(txt: str) -> bool:
    if not txt:
        return False
    t = _RE_WS.sub(" ", txt).strip()

    # 1) 太短：大概率是噪声（你可以先用 10 做门槛）
    if len(t) < 10:
        return False

    # 2) 有效字符占比：至少得有一些中文/字母/数字
    useful = 0
    for ch in t:
        if ("\u4e00" <= ch <= "\u9fff") or ch.isalnum():
            useful += 1
    if useful / max(len(t), 1) < 0.3:
        return False

    return True

def _replace_imgs_inplace(td, part_index, image_interpreter):
    for img in td.find_all("img"):
        src = (img.get("src") or "").strip()
        pr = part_index.resolve_img(src) if src else None

        ocr_txt =(image_interpreter.interpret(pr.payload_path) or "").strip()
        if image_interpreter and pr and pr.payload_path:
            ocr_txt = (image_interpreter.interpret(pr.payload_path) or "").strip()

        rep = ocr_txt if ocr_txt else f"[IMG:{src}]"
        img.replace_with(NavigableString(rep))

def _table_to_markdown(table: Tag) -> str:
    trs = table.find_all("tr")
    rows: List[List[str]] = []
    for tr in trs:
        cells = tr.find_all(["td","th"])
        row = [c.get_text(" ", strip=True) for c in cells]
        if any(x.strip() for x in row):
            rows.append(row)
    
    if not rows:
        return ""
    #对齐
    max_cols = max(len(r) for r in rows)
    for r in rows:
        if len(r) < max_cols:
            r.extend([""]*(max_cols - len(r)))
    header = rows[0]
    body = rows[1:]

    md = []
    md.append("| " + " | ".join(header) + " |")
    md.append("| " + " | ".join(["---"] * max_cols) + " |")
    for r in body:
        md.append("| " + " | ".join(r) + " |")
    return "\n".join(md)

def _cell_text_with_assets(td: Tag,
                           part_index: PartIndex,
                           image_interpreter: Optional[ImageInterpreter]) -> str:
    """
    规则：
    - 嵌套表格：转 markdown 塞回 cell（不作为顶层表格抽取）
    - 图片：能 OCR 就用 OCR 文本；否则保留 [IMG:src] 占位
    """
    # 1) 处理 nested table：先转 markdown，再移除避免影响 get_text
    nested_tables = td.find_all("table")
    nested_texts: List[str] = []
    for nt in nested_tables:
        md = _table_to_markdown(nt)
        if md:
            nested_texts.append("子表:\n" + md)
        nt.decompose()  # 从 DOM 移除，避免影响后续文本提取
    
    # 2) 图片原位替换（OCR）
    # 说明：把 <img> 标签直接替换成 OCR 文本（或占位），这样顺序不会乱
    for img in td.find_all("img"):
        src = (img.get("src") or "").strip()
        pr = part_index.resolve_img(src) if src else None

        ocr_txt = ""
        if image_interpreter and pr and pr.payload_path:
            ocr_txt = (image_interpreter.interpret(pr.payload_path) or "").strip()

        # 只考虑 OCR：有结果就替换成文本；没结果保留占位符，便于排查
        rep = ocr_txt if ocr_txt else f"[IMG:{src}]"
        img.replace_with(NavigableString(rep))
    # 3) 取 cell 自身文本
    base_text = td.get_text(" ", strip=True)

    # 4) 把 nested table 的 markdown 追加到 cell 末尾（它本来就在 cell 内，但已被 decompose）
    # 说明：nested_texts 是结构化补充信息，追加即可
    parts = []
    if base_text:
        parts.append(base_text)
    parts.extend(nested_texts)

    return "\n".join([p for p in parts if p]).strip()

def _normalize_table_to_grid(table: Tag,
                             part_index,
                             image_interpreter) -> List[List[Tag]]:
    trs = table.find_all("tr")
    grid: List[List[Tag]] = []
    spans: List[Optional[Dict[str, Any]]] = []

    for tr in trs:
        row: List[Tag] = []

        col = 0
        while col < len(spans):
            sp = spans[col]
            if sp and sp["remain"] > 0:
                row.append(sp["value"])
                sp["remain"] -= 1
            else:
                row.append("")
            col += 1
        
        cells = tr.find_all(["td","th"])
        col = 0
        for cell in cells:
            if cell is None or not isinstance(cell, Tag):
                continue
            #找下一个空位（跳过 rowspan 已占用的列）
            while col < len(row) and row[col] != "":
                col += 1
            if col >= len(row):
                extend = col - len(row) + 1
                row.extend([""] * extend)
                spans.extend([None] * extend)

            value = _cell_text_with_assets(cell, part_index, image_interpreter)
            attrs = cell.attrs or {}
            rowspan = int(attrs.get("rowspan") or 1)
            colspan = int(attrs.get("colspan") or 1)

            for k in range(colspan):
                idx = col + k
                if idx >= len(row):
                    row.extend([""] * (idx - len(row) + 1))
                    spans.extend([None] * (idx - len(spans) + 1))
                row[idx] = value
                if rowspan > 1:
                    spans[idx] = {"remain": rowspan - 1, "value": value}

            col += colspan

        # 去掉末尾多余空列
        while row and row[-1] == "":
            row.pop()

        grid.append(row)
    
    # 全表对齐列数
    max_cols = max((len(r) for r in grid), default=0)
    for r in grid:
        if len(r) < max_cols:
            r.extend([""] * (max_cols - len(r)))

    return grid


def _cell_text_with_images(
        td: Tag,
        part_index: PartIndex,
        image_interpreter: Optional[ImageInterpreter] = None,)-> str:
    # 把单元格内的文字 + 图片识别文本合并成一个字符串（你也可以更细：返回 blocks 列表）
    parts: List[str] = []
    txt = td.get_text(strip=True)
    if txt:
        parts.append(txt)
    
    for img in td.find_all("img"):
        src = img.get("src") or ""
        pr = part_index.resolve_img(src) if src else None
        if image_interpreter and pr and pr.payload_path:
            ocr_txt = image_interpreter.interpret(pr.payload_path)
            if ocr_txt:
                parts.append(f"[IMG_TEXT]{ocr_txt}[/IMG_TEXT]")
            else:
                # 无法解析时保留占位，便于人工排查
                if src:
                    parts.append(f"[IMG]{src}[/IMG]")
    return "\n".join(parts)

def extract_table_blocks(table: Tag,
                         order: int,
                         part_index: PartIndex,
                         image_interpreter) -> TableBlock:
    
    grid = _normalize_table_to_grid(table, part_index, image_interpreter)
    if not grid:
        return TableBlock(kind="table", order=order, schema=[], rows=[], meta=None)
    
    schema = [x.strip() for x in grid[0]]
    rows: List[Dict[str, str]] = []

    for r in grid[1:]:
        if not any((c or "").strip() for c in r):
            continue
        values = [c.strip() for c in r]

        if len(values) < len(schema):
            values.extend([""] * (len(schema) - len(values)))
        elif len(values) > len(schema):
            values = values[:len(schema)]

        rows.append(dict(zip(schema, values)))

    return TableBlock(kind="table", order=order, schema=schema, rows=rows, meta=None)

    # 简单按首行作为表头处理
    # trs = table.find_all("tr")
    # if not trs:
    #     return TableBlock(kind="table", order=order, schema=[], rows=[])
    
    # header_cells = trs[0].find_all(["th","td"])
    # schema = [hc.get_text(" ",strip = True) for hc in header_cells]

    # rows: List[Dict[str,str]] = []
    # for tr in trs[1:]:
    #     cells = tr.find_all(["td","th"])
    #     values = [_cell_text_with_images(td,part_index,image_interpreter) for td in cells]

    #     if len(values) != len(schema):
    #         values += [""] * (len(schema) - len(values))

    #     if len(values) > len(schema):
    #         values = values[:len(schema)]
        
    #     rows.append(dict(zip(schema,values)))
    
    # return TableBlock(kind="table", order=order, schema=schema, rows=rows)