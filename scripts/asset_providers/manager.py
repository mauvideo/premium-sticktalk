from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .base import is_valid_mime
from .openverse import OpenverseProvider
from .pexels import PexelsProvider
from .pixabay import PixabayProvider
from .unsplash import UnsplashProvider
from scripts.entity_visual_planner import plan_entities

VOX_TEMPLATE='vox-paper-collage'
MIN_TOPIC_PHOTOS=3
ONLINE_PROVIDERS={'openverse','pexels','pixabay','unsplash'}

def keyword(scene):
 p=scene.get('entityVisualPlan') or {}; qs=p.get('searchQueries') or scene.get('visualQueries') or []
 return {'primary':qs[0] if qs else p.get('mainSubject','documentary subject'),'secondary':qs[1:],'asset_type':'photo','style':'editorial documentary paper collage','emotion':'documentary','subject':p.get('mainSubject','documentary subject'),'subject_type':p.get('mainSubjectType','concept'),'identity_required':False,'event':p.get('event','') or scene.get('event',''),'setting':p.get('location',''),'time_period':p.get('timePeriod',''),'visual_evidence':p.get('visualEvidence') or [],'template':VOX_TEMPLATE,'size':'9:16'}

class AssetManager:
 def __init__(self,story_path='assets/story.json',assets_dir='assets/generated-assets',output_dir='output',cache_dir='assets/.asset-cache'):
  self.story_path=Path(story_path);self.assets_dir=Path(assets_dir);self.output_dir=Path(output_dir);self.cache_dir=Path(cache_dir)
  for p in (self.assets_dir,self.output_dir,self.cache_dir):p.mkdir(parents=True,exist_ok=True)
  self.used=set();self.research={}
 def providers(self):
  return [PexelsProvider(self.assets_dir,self.cache_dir),PixabayProvider(self.assets_dir,self.cache_dir),UnsplashProvider(self.assets_dir,self.cache_dir),OpenverseProvider(self.assets_dir,self.cache_dir)]
 @staticmethod
 def _clean(v):return re.sub(r'\s+',' ',str(v or '').replace('"',' ')).strip(' ,;:-')[:180]
 def variants(self,q,contextual=False):
  s=self._clean(q.get('subject'));e=self._clean(q.get('event'));loc=self._clean(q.get('setting'));out=[]
  if contextual:
   out += [e,loc];out += [self._clean(x) for x in q.get('visual_evidence',[]) if self._clean(x)]
   if s and e:out.append(f'{s} {e}')
  else:
   out += [q.get('primary'),*(q.get('secondary') or []),s,e]
   if s:out += [f'{s} photo',f'{s} lifestyle',f'{s} documentary']
  seen=set();clean=[]
  for v in out:
   v=self._clean(v);k=v.casefold()
   if v and k not in seen:seen.add(k);clean.append(v)
  return clean[:10]
 def semantic_variants(self,scene,q,canonical):
  """Broaden a failed exact query while staying inside the scene/topic meaning."""
  headline=self._clean(scene.get('headline'));event=self._clean(scene.get('event'));loc=self._clean(q.get('setting'))
  evidence=[self._clean(x) for x in (q.get('visual_evidence') or []) if self._clean(x)]
  raw=[*evidence,event,headline]
  if event and loc:raw.append(f'{event} {loc}')
  if headline and loc:raw.append(f'{headline} {loc}')
  if event:raw += [f'{event} people',f'{event} lifestyle',f'{event} activity',f'{event} environment']
  if headline:raw += [f'{headline} people',f'{headline} lifestyle',f'{headline} activity']
  raw += [f'{canonical} activity',f'{canonical} lifestyle',f'{canonical} environment',canonical]
  seen=set();out=[]
  for v in raw:
   v=self._clean(v);k=v.casefold()
   if v and k not in seen:seen.add(k);out.append(v)
  return out[:14]
 def valid(self,r):return bool(r and Path(r.file).exists() and Path(r.file).stat().st_size>700 and is_valid_mime(r.mime_type) and r.provider and r.qualityScore>=0)
 def matches(self,r):return self.valid(r) and r.provider in ONLINE_PROVIDERS
 def search_texts(self,q,scene_index,texts):
  for text in texts:
   current={**q,'primary':text,'subject':text,'subject_type':'concept','identity_required':False}
   for provider in self.providers():
    try:
     r=provider.search(current,scene_index,self.used)
     if self.matches(r):self.used.update({r.source_url,r.asset_id});return r
    except Exception as e:print(f'ASSET SKIP {provider.name} {text!r}: {e}')
  return None
 def search(self,q,scene_index,contextual=False):return self.search_texts(q,scene_index,self.variants(q,contextual))
 def item(self,r,scene,role,subject,queries,fallback=False):
  d=r.manifest();d.update({'scene':scene,'role':role,'fallback':fallback,'identityQuery':subject,'identityVerified':False,'topicMatched':True,'searchQueries':queries,'cutoutStyle':'white-outline-yellow-shadow'});return d
 def generate(self,story):
  story=plan_entities(story,story.get('topic') or story.get('title'));self.research=story.get('research') or {};scenes=story.get('scenes') or [];plan=story.get('entityVisualPlan') or {}
  canonical=str(self.research.get('canonicalTitle') or plan.get('mainEntity') or story.get('resolvedSubject') or story.get('title') or '').strip();entity_type=str(story.get('resolvedEntityType') or plan.get('mainEntityType') or 'concept').casefold()
  bad={'nhạc chủ đề','tài liệu gốc','mốc thời gian','ảnh bối cảnh','documentary subject'}
  if canonical.casefold() in bad:raise RuntimeError(f'Chủ thể hình ảnh không hợp lệ: {canonical!r}. Research stage phải cung cấp canonicalTitle trước khi tìm ảnh.')
  manifest=[];gallery=[];max_gallery=max(12,len(scenes)*3);last_good=None
  print(f'IMAGE ENGINE subject={canonical!r} type={entity_type} sources=Pexels,Pixabay,Unsplash,Openverse mode=semantic-fallback')
  for idx,scene in enumerate(scenes,1):
   q=keyword(scene);q['subject']=canonical;q['subject_type']=entity_type;q['identity_required']=False
   exact_queries=self.variants(q)
   main=self.search_texts(q,idx,exact_queries)
   fallback_used=False
   if not main:
    semantic=self.semantic_variants(scene,q,canonical)
    print(f'ASSET SEMANTIC FALLBACK scene {idx}: {semantic[:6]}')
    main=self.search_texts(q,idx,semantic);fallback_used=bool(main)
   if not main and last_good:
    print(f'ASSET LAST RESORT scene {idx}: reuse previous topic-matched image')
    main=last_good;fallback_used=True
   if not main:raise RuntimeError(f'Không tìm được ảnh đúng hoặc tương tự cho chủ đề {canonical!r}. Hãy cấu hình ít nhất một API ảnh PEXELS/PIXABAY/UNSPLASH hoặc thử lại khi nguồn ảnh hoạt động.')
   last_good=main
   main_path=Path(main.file).as_posix();scene['image']=main_path;scene['asset']=main_path;scene['assetProvider']=main.provider;scene['assetSource']=main.source_url;scene['identityVerified']=False;scene['topicMatched']=True;scene['semanticImageFallback']=fallback_used
   manifest.append(self.item(main,idx,'main-subject' if not fallback_used else 'semantic-topic-match',canonical,exact_queries,fallback_used))
   if main_path not in gallery:gallery.append(main_path)
   scene['assets']=[]
   # Prefer different but semantically related supporting images. They remain optional.
   support_queries=self.semantic_variants(scene,q,canonical)
   attempts=0
   while len(scene['assets'])<2 and attempts<3:
    attempts+=1;extra=self.search_texts(q,idx,support_queries)
    if not extra:break
    p=Path(extra.file).as_posix()
    if p==main_path or p in scene['assets']:continue
    scene['assets'].append(p);manifest.append(self.item(extra,idx,'context-evidence',canonical,support_queries,True))
    if p not in gallery and len(gallery)<max_gallery:gallery.append(p)
  story['assetProviderSystem']='vox-semantic-stock-assets-v12';story['template']=VOX_TEMPLATE;story['topicImageGallery']=gallery[:max_gallery];story['topicSubjectImages']=len(gallery);story['topicImageMinimumMet']=len(gallery)>=MIN_TOPIC_PHOTOS;story['resolvedEntityType']=entity_type
  self.story_path.write_text(json.dumps(story,ensure_ascii=False,indent=2),encoding='utf-8');(self.output_dir/'asset-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8');(self.output_dir/'credits.txt').write_text('\n'.join(['Asset credits','=============','']+[f"Scene {x['scene']}: {x['provider']} — {x['source_url']} — role={x['role']}" for x in manifest])+'\n',encoding='utf-8')
  print(f'IMAGE ENGINE OK: {len(gallery)} unique images; Pexels={bool(os.getenv("PEXELS_API_KEY"))}; Pixabay={bool(os.getenv("PIXABAY_API_KEY"))}; Unsplash={bool(os.getenv("UNSPLASH_ACCESS_KEY"))}');return story

def generate_assets(story):
 path=Path('assets/story.json')
 if isinstance(story,(str,Path)):path=Path(story);data=json.loads(path.read_text(encoding='utf-8'))
 else:data=story
 return AssetManager(story_path=path).generate(data)
if __name__=='__main__':generate_assets(Path(os.getenv('STORY_PATH','assets/story.json')))
