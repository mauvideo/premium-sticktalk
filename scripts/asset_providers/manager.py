from __future__ import annotations
import json, os, re
from pathlib import Path
from .base import is_valid_license, is_valid_mime
from .pexels import PexelsProvider
from .pixabay import PixabayProvider
from .unsplash import UnsplashProvider
from .local_assets import LocalAssetsProvider

PHOTO_TEMPLATES={'prompt-to-video','business-motivation','smooth-transitions','kinetic-captions'}
PAPER={'paper-cut-documentary'}
STOP={'và','là','của','một','những','các','cho','trong','khi','để','the','and','with','you','your'}

def keyword(scene,template):
 text=' '.join(str(scene.get(k,'')) for k in ('headline','narration','text'))
 words=[w for w in re.findall(r"[\wÀ-ỹ]+",text.lower()) if len(w)>2 and w not in STOP]
 base=' '.join(words[:5]) or 'motivation focus'
 style={'stick-figure':'stick figure simple action svg','paper-sketch':'hand drawn doodle line art','paper-cut-documentary':'documentary portrait paper collage','kinetic-captions':'dark minimal background empty space'}.get(template,'portrait real photo motivation')
 return {'primary':f'{base} {style}', 'secondary':words[5:10], 'asset_type':'photo' if template in PHOTO_TEMPLATES|PAPER else 'svg', 'style':style, 'emotion':'motivational', 'subject':words[0] if words else 'person', 'setting':'vertical video', 'template':template, 'size':'9:16'}

class AssetManager:
 def __init__(self,template:str,story_path='assets/story.json',assets_dir='assets/generated-assets',output_dir='output',cache_dir='assets/.asset-cache'):
  self.template=template; self.story_path=Path(story_path); self.assets_dir=Path(assets_dir); self.output_dir=Path(output_dir); self.cache_dir=Path(cache_dir); self.used=set(); self.memory_cache={}
  self.assets_dir.mkdir(parents=True,exist_ok=True); self.output_dir.mkdir(parents=True,exist_ok=True); self.cache_dir.mkdir(parents=True,exist_ok=True)
 def providers(self):
  online=[PexelsProvider(self.assets_dir,self.cache_dir),PixabayProvider(self.assets_dir,self.cache_dir),UnsplashProvider(self.assets_dir,self.cache_dir)]
  if self.template in PHOTO_TEMPLATES or self.template in PAPER: return online+[LocalAssetsProvider(self.assets_dir,self.cache_dir)]
  return [LocalAssetsProvider(self.assets_dir,self.cache_dir)]
 def valid(self,r):
  return bool(r and Path(r.file).exists() and Path(r.file).stat().st_size>100 and is_valid_mime(r.mime_type) and is_valid_license(r.license,r.license_url) and r.provider and r.qualityScore>=0)
 def get(self,q,idx):
  ck=(q['template'],q['primary'],q['size'])
  if ck in self.memory_cache and self.memory_cache[ck].source_url not in self.used: return self.memory_cache[ck]
  for provider in self.providers():
   for _ in range(2):
    try:
     r=provider.search(q,idx,self.used)
     if self.valid(r):
      self.used.update({r.source_url,r.asset_id}); self.memory_cache[ck]=r; return r
    except Exception as e: print(f'Asset provider {provider.name} skipped: {e}')
  r=LocalAssetsProvider(self.assets_dir,self.cache_dir).search(q,idx,self.used)
  self.used.update({r.source_url,r.asset_id}); return r
 def generate(self,story:dict):
  manifest=[]
  for i,scene in enumerate(story.get('scenes',[]),1):
   q=keyword(scene,self.template); r=self.get(q,i); rel=str(Path(r.file).as_posix())
   scene.update({'asset':rel,'image':rel,'assetType':r.asset_type,'assetProvider':r.provider,'assetAuthor':r.author,'assetLicense':r.license,'assetSource':r.source_url,'searchQuery':r.search_query,'qualityScore':r.qualityScore})
   manifest.append(r.manifest())
  story['assetProviderSystem']='free-licensed-assets-v2'
  self.story_path.write_text(json.dumps(story,ensure_ascii=False,indent=2),encoding='utf-8')
  (self.output_dir/'asset-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
  credits=['Asset credits','=============','']
  for m in manifest: credits.append(f"Scene {m['scene']}: {m['provider']} — {m['author']} — {m['license']} — {m['source_url']} — quality {m['qualityScore']}/100")
  (self.output_dir/'credits.txt').write_text('\n'.join(credits)+'\n',encoding='utf-8')
  return story

def generate_assets(story, template):
 path=Path('assets/story.json')
 if isinstance(story,(str,Path)): path=Path(story); data=json.loads(path.read_text(encoding='utf-8'))
 else: data=story
 return AssetManager(template,story_path=path).generate(data)

if __name__=='__main__':
 p=Path(os.getenv('STORY_PATH','assets/story.json')); s=json.loads(p.read_text(encoding='utf-8'))
 generate_assets(p, os.getenv('VIDEO_TEMPLATE',s.get('template','prompt-to-video')))
