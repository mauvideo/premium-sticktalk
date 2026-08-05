from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional
import hashlib, mimetypes, shutil, urllib.request

MIN_BYTES = 700
VALID_MIME_PREFIXES = ('image/jpeg', 'image/png', 'image/webp', 'image/svg+xml')

@dataclass
class AssetResult:
    scene:int; file:str; asset_type:str; provider:str; source_url:str; author:str; author_url:str; license:str; license_url:str; search_query:str; downloaded_at:str; width:int=0; height:int=0; mime_type:str='image/svg+xml'; qualityScore:int=0; asset_id:str=''
    def manifest(self): return asdict(self)

class AssetProvider:
    name='base'; asset_types=('photo','svg')
    def __init__(self, out_dir:Path, cache_dir:Path|None=None): self.out_dir=Path(out_dir); self.cache_dir=Path(cache_dir or out_dir/'.cache')
    def search(self, query:dict, scene_index:int, used:set[str]) -> Optional[AssetResult]: raise NotImplementedError

def safe_name(text:str)->str:
    return ''.join(c if c.isalnum() else '-' for c in text.lower()).strip('-')[:72] or 'asset'

def cache_key(provider:str, query:str, template:str, size:str='portrait')->str:
    raw=f'{provider}|{query}|{template}|{size}'.encode('utf-8')
    return hashlib.sha256(raw).hexdigest()[:24]

def mime_for(path:Path, header:str='')->str:
    return header.split(';')[0].lower() if header else (mimetypes.guess_type(path.name)[0] or 'application/octet-stream')

def is_valid_license(license_name:str, license_url:str)->bool:
    bad={'', 'unknown', 'missing', 'unclear', 'n/a', 'none'}
    return license_name.strip().lower() not in bad and (bool(license_url.strip()) or license_name in {'Local fallback asset'})

def is_valid_mime(mime_type:str)->bool:
    return mime_type.lower() in VALID_MIME_PREFIXES

def download(url:str, path:Path, headers:dict|None=None, min_bytes:int=MIN_BYTES, cache_path:Path|None=None)->tuple[int,str,bool]:
    if cache_path and cache_path.exists() and cache_path.stat().st_size >= min_bytes:
        mt=mime_for(cache_path)
        if is_valid_mime(mt):
            path.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(cache_path,path); return path.stat().st_size, mt, True
    req=urllib.request.Request(url,headers=headers or {'User-Agent':'premium-sticktalk-free-assets/1.0'})
    with urllib.request.urlopen(req,timeout=20) as r:
        data=r.read(); ctype=r.headers.get('Content-Type','')
    mt=mime_for(path,ctype)
    if len(data)<min_bytes: raise RuntimeError('downloaded file too small')
    if not is_valid_mime(mt): raise RuntimeError(f'invalid image MIME type: {mt}')
    path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(data)
    if cache_path:
        cache_path.parent.mkdir(parents=True,exist_ok=True); cache_path.write_bytes(data)
    return len(data), mt, False
