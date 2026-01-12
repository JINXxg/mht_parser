#不做复杂重新排序，先按抽取顺序为序
# semantics/html_semantics.py
import re
from dataclasses import dataclass
from typing import Optional, List, Protocol, Dict, Any

from bs4 import BeautifulSoup, Tag

from model.mht_model import PartRecord, TableBlock
from mht_parser.part_index import PartIndex
from semantics.table_semantics import extract_table_blocks

class ImageInterpreter(Protocol):
    def interpret(self, image_path: str) -> Optional[str]:
        ... #为什么可以这样

@dataclass
class Block:
    kind: str  # "text", "image", "table", ...
    order: int 

@dataclass
class TextBlock(Block):
    text: str

@dataclass
class ImageBlock(Block):
    src: str
    part: Optional[PartRecord]
    extraced_text: Optional[str] = None
    method: Optional[str] = None

# A/B 序号： 1. 或 1、（你确认先覆盖这两类）
RE_NUMBERED = re.compile(r"^\s*\d+(\.|、)\s*")

def _shorten(s: str, max_len: int = 60) -> str:
    s = (s or "").strip()
    if len(s) <= max_len:
        return s
    return s[: max_len].strip() + "..."

def _extract_anchor_for_table(table: Tag, lookback_blocks: int = 3) -> Dict[str, Any]:
    """
    返回:
      {
        "anchor": str or None,
        "anchor_source": "bold_nearby" | "numbered_fallback" | "none",
        "anchor_candidates": [ ... ],
      }
    """
    candidates: List[str] = []

    # 只在“块级节点”里向前找：优先 p/div/li/标题
    block_tags = ("p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6")
    prev_blocks: List[Tag] = []
    cur = table

    # 取 table 的前置 sibling 块（最多 lookback_blocks 个）
    while len(prev_blocks) < lookback_blocks:
        cur = cur.find_previous_sibling()
        if cur is None:
            break

        if isinstance(cur, Tag) and cur.name in block_tags:
            txt = cur.get_text(" ", strip=True)
            if txt:
                prev_blocks.append(cur)

    # for blk in prev_blocks:
    #     bold = blk.find(["strong", "b"])
    #     if bold:
    #         bt = bold.get_text(" ", strip=True)
    #         if bt:
    #             candidates.append(bt)

    _RE_WS = re.compile(r"\s+")
    _RE_NUM_JOIN = re.compile(r"(\d+)\s*[、.]\s*")  # 只覆盖 1、 / 1. 两类

    def _norm_anchor(s: str) -> str:
        s = (s or "").strip()
        s = _RE_WS.sub(" ", s)           # 多空白合一
        s = _RE_NUM_JOIN.sub(r"\1、", s) # 统一成 1、xxx（你也可以改成保留 .）
        return s

    for blk in prev_blocks:
        # 只要块里出现过 b/strong，就认为它是“加粗候选块”
        if blk.find(["strong", "b"]) is not None:
            full = _norm_anchor(blk.get_text(" ", strip=True))
            if full:
                candidates.append(full)
        

    for blk in prev_blocks:
        txt = blk.get_text(" ", strip=True)
        if txt and RE_NUMBERED.match(txt):
            candidates.append(txt)
    
    if candidates:
        anchor = _shorten(candidates[0], 80)
        return {"anchor": anchor, "anchor_source": "numbered_fallback", "anchor_candidates": candidates}

    return {"anchor": None, "anchor_source": "none", "anchor_candidates": []}

def extract_tables_with_anchor(html: str,
                                part_index: PartIndex,
                                image_interpreter: Optional[ImageInterpreter] = None) -> List[TableBlock]:
    
    soup = BeautifulSoup(html, "lxml")
    tables: List[TableBlock] = []

    order = 0
    for table in soup.find_all("table"):
        #只抽取顶层table
        if table.find_parent("table") is not None:
            continue
            
        anchor_meta = _extract_anchor_for_table(table, lookback_blocks=3)

        tb = extract_table_blocks(table, order, part_index, image_interpreter)

        tb.meta = tb.meta or {}
        tb.meta.update(anchor_meta)

        tables.append(tb)
        order += 1

    return tables

# def extract_blocks(
#         html: str,
#         part_index: PartIndex,
#         image_interpreter: Optional[ImageInterpreter] = None,
# ) -> List[Block]:
    
#     soup = BeautifulSoup(html,"lxml") # 这个可以考虑换成html5lib
#     blocks: List[Block] = []
#     order = 0

#     body = soup.body or soup

#     for node in body.descendants:
#         if not isinstance(node, Tag):
#             continue

#         if node.name == "table":
#             tb = extract_table_blocks(node, order, part_index, image_interpreter)# 这个方法的逻辑需要搞懂
#             blocks.append(tb)
#             order += 1
#             continue

#         if node.name == "img":
#             src = node.get("src") or ""
#             pr = part_index.resolve_img(src) if src else None
#             ib = ImageBlock(kind ="image", order = order, src = src, part = pr)

#             if image_interpreter and pr and pr.payload_path:
#                 ib.extraced_text = image_interpreter.interpret(pr.payload_path)
#                 ib.method = "ocr"
#             blocks.append(ib)
#             order += 1
#             continue

#         if node.name in ("p","li","h1","h2","h3"):
#             text = node.get_text(" ",strip=True)
#             if text:
#                 tb = TextBlock(kind = "text", order = order, text = text)
#                 order += 1
#     return blocks
