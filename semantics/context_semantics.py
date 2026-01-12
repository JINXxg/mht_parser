# semantics/context_semantics.py

import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup, Tag

@dataclass
class ContextTextBlock:
    kind: str   # "text"
    order: int
    text: str
    meta: Optional[Dict[str, Any]] = None

_BLOCK_TAGS = ("p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6")
_SKIP_TAGS = ("script", "style", "noscript")
_RE_WS = re.compile(r"\s+")

def _norm_text(s: str) -> str:
    s = (s or "").strip()
    return _RE_WS.sub(" ", s)

def _is_inside_table(node: Tag) -> bool:
    return node.find_parent("table") is not None

def _is_container_block(node: Tag) -> bool:
    # node 内部如果还有其它块级标签（除了它自己），说明它是容器，不抽
    for t in node.find_all(_BLOCK_TAGS):
        if t is node:
            continue
        return True
    return False

def _text_without_tables(node: Tag) -> str:
    tmp = BeautifulSoup(str(node), "lxml")
    root = tmp.find(node.name) or tmp
    for t in root.find_all("table"):
        t.decompose()
    return root.get_text(" ", strip=True)

def extract_non_table_text_context(html: str,
                                   max_blocks: int = 200,
                                   min_len: int = 2) -> List[ContextTextBlock]:
    soup = BeautifulSoup(html, "lxml")
    body = soup.body or soup

    blocks: List[ContextTextBlock] = []
    order = 0

    for node in body.find_all(_BLOCK_TAGS):
        if not isinstance(node, Tag):
            continue
        if node.name in _SKIP_TAGS:
            continue
        if _is_inside_table(node):
            continue

        # 关键：跳过“容器块”，只保留叶子块（p/li/h*）
        if _is_container_block(node):
            continue

        txt = _norm_text(_text_without_tables(node))
        if len(txt) < min_len:
            continue

        blocks.append(ContextTextBlock(kind="text", order=order, text=txt, meta={"tag": node.name}))
        order += 1
        if order >= max_blocks:
            break

    return blocks
