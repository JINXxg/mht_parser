from dataclasses import dataclass
from typing import Optional,List,Dict
from urllib.parse import urlparse
from pathlib import Path

from model.mht_model import PartRecord


def _basename_from_content_location(loc:Optional[str]) -> Optional[str]:
    if not loc:
        return None
    
    p = urlparse(loc) # 这里urlparse返回的是什么
    path = p.path if p.scheme else loc
    name = Path(path).name
    return name or None

@dataclass
class PartIndex:
    by_basename: Dict[str, PartRecord]

    #这个方法的逻辑没看懂
    @classmethod
    def build(cls, parts: List[PartRecord]) -> "PartIndex":
        m: Dict[str, PartRecord] = {}
        for pr in parts:
            bn = _basename_from_content_location(pr.content_location)
            if bn:
                if bn not in m:
                    m[bn] = pr
        return cls(by_basename=m)
    
    def resolve_img(self, src: str) -> Optional[PartRecord]:
        # src可能是相对路径，去basename(这里的basename是什么)
        bn = Path(src).name
        return self.by_basename.get(bn)