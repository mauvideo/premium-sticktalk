from __future__ import annotations
import re, unicodedata
from .base import is_valid_license

STOP={'the','and','with','from','this','that','photo','image','picture','documentary','portrait','people','person','activity','environment','historical','archive','archival','ảnh','hình','người','với','của','một','các','cho','trong','và','đang'}
def _norm(s:str)->str:
    s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode('ascii').lower()
    return re.sub(r'[^a-z0-9 ]+',' ',s)
def _terms(text:str)->list[str]:
    return [w for w in _norm(text).split() if len(w)>=3 and w not in STOP]

def asset_quality_score(candidate:dict, query:dict, template:str, duplicate:bool=False)->int:
    score=0
    text=_norm(' '.join(str(candidate.get(k,'')) for k in ('title','description','alt','source_url','author')))
    terms=_terms(query.get('primary',''))
    subject_terms=_terms(query.get('subject',''))
    matched=sum(1 for t in terms if t in text)
    subject_matched=sum(1 for t in subject_terms if t in text)
    if terms:
        coverage=matched/max(1,len(terms))
        score += int(45*coverage)
        # Strongly punish attractive but unrelated stock images.
        if matched==0 and text.strip(): score -= 45
        elif coverage<0.34: score -= 18
    if query.get('identity_required') and subject_terms:
        # Named person/entity: require metadata to carry the actual identity instead of a look-alike.
        required=min(2,len(subject_terms))
        if subject_matched<required: return 0
        score += 25
    width=int(candidate.get('width') or 0); height=int(candidate.get('height') or 0)
    if width and height:
        ratio=width/height; score += max(0,int(10-abs(ratio-(9/16))*20))
        pixels=width*height; score += 10 if pixels>=1_200_000 else 6 if pixels>=500_000 else 2
    else: score += 4 if candidate.get('mime_type')=='image/svg+xml' else 1
    if not candidate.get('has_logo_or_text',False): score += 6
    if candidate.get('clear_subject',True): score += 6
    if candidate.get('asset_type')==query.get('asset_type'): score += 5
    if is_valid_license(candidate.get('license',''),candidate.get('license_url','')): score += 5
    if duplicate: score -= 35
    return max(0,min(100,score))
