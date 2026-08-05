from __future__ import annotations
from .base import is_valid_license

def asset_quality_score(candidate:dict, query:dict, template:str, duplicate:bool=False)->int:
    score=0
    text=' '.join(str(candidate.get(k,'')) for k in ('title','description','alt','source_url','author')).lower()
    terms=[w for w in query.get('primary','').lower().split() if len(w)>3]
    if terms:
        score += min(20, sum(4 for t in terms if t in text))
    width=int(candidate.get('width') or 0); height=int(candidate.get('height') or 0)
    if width and height:
        ratio=width/height
        score += max(0, int(20 - abs(ratio-(9/16))*45))
        pixels=width*height
        score += 20 if pixels>=1_200_000 else 12 if pixels>=500_000 else 5
    else:
        score += 18 if candidate.get('mime_type')=='image/svg+xml' else 5
    if not candidate.get('has_logo_or_text', False): score += 10
    if candidate.get('clear_subject', True): score += 10
    if candidate.get('asset_type') == query.get('asset_type'): score += 10
    if is_valid_license(candidate.get('license',''), candidate.get('license_url','')): score += 10
    if duplicate: score -= 35
    return max(0,min(100,score))
