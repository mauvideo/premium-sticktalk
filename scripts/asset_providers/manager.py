from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from .base import AssetResult, download, is_valid_mime, safe_name
from .openverse import OpenverseProvider
from .pexels import PexelsProvider
from .pixabay import PixabayProvider
from .unsplash import UnsplashProvider
from .wikimedia import WikimediaProvider
from scripts.entity_visual_planner import plan_entities

VOX_TEMPLATE='vox-paper-collage'; MIN_TOPIC_PHOTOS=3; MAX_TOPIC_PHOTOS=8
VERIFIED_IDENTITY_PROVIDERS={'wikimedia-commons','wikipedia-topic-image'}
ONLINE_PROVIDERS={'wikimedia-commons','wikipedia-topic-image','openverse','pexels','pixabay','unsplash'}

def keyword(scene):
 p=scene.get('entityVisualPlan') or {}; qs=p.get('searchQueries') or []
 return {'primary':qs[0] if qs else p.get('mainSubject','documentary subject'),'secondary':qs[1:],'asset_type':'photo','style':'editorial documentary paper collage','emotion':'documentary','subject':p.get('mainSubject','documentary subject'),'subject_type':p.get('mainSubjectType','concept'),'identity_required':bool(p.get('identityRequired')),'event':p.get('event',''),'setting':p.get('location',''),'time_period':p.get('timePeriod',''),'visual_evidence':p.get('visualEvidence') or [],'template':VOX_TEMPLATE,'size':'9:16'}

class AssetManager:
 def __init__(self,story_path='assets/story.json',assets_dir='assets/generated-assets',output_dir='output',cache_dir='assets/.asset-cache'):
  self.story_path=Path(story_path);self.assets_dir=Path(assets_dir);self.output_dir=Path(output_dir);self.cache_dir=Path(cache_dir)
  for p in (self.assets_dir,self.output_dir,self.cache_dir):p.mkdir(parents=True,exist_ok=True)
  self.used=set();self.research={}
 def providers(self,identity=False):
  if identity:return [WikimediaProvider(self.assets_dir,self.cache_dir)]
  return [OpenverseProvider(self.assets_dir,self.cache_dir),PexelsProvider(self.assets_dir,self.cache_dir),PixabayProvider(self.assets_dir,self.cache_dir),UnsplashProvider(self.assets_dir,self.cache_dir),WikimediaProvider(self.assets_dir,self.cache_dir)]
 @staticmethod
 def _clean(v):return re.sub(r'\s+',' ',str(v or '').replace('"',' ')).strip(' ,;:-')[:180]
 def variants(self,q,contextual=False):
  s=self._clean(q.get('subject'));e=self._clean(q.get('event'));loc=self._clean(q.get('setting'));period=self._clean(q.get('time_period'));out=[]
  if contextual:
   out += [e,f'{e} historical photo' if e else '',loc,f'{loc} historical photo' if loc else ''];out += [self._clean(x) for x in q.get('visual_evidence',[]) if self._clean(x)]
   if period and e:out.append(f'{e} {period}')
   if s and e:out.append(f'{s} {e}')
  else:
   out += [q.get('primary'),*(q.get('secondary') or []),s]
   if q.get('subject_type')=='person':out += [f'{s} portrait',f'{s} archival photograph',f'{s} historical photograph']
   elif s:out += [f'{s} historical photo',f'{s} archive']
   if period:out.append(f'{s} {period}')
  seen=set();clean=[]
  for v in out:
   v=self._clean(v);k=v.casefold()
   if v and k not in seen:seen.add(k);clean.append(v)
  return clean[:12]
 def valid(self,r):return bool(r and Path(r.file).exists() and Path(r.file).stat().st_size>700 and is_valid_mime(r.mime_type) and r.provider and r.qualityScore>=0)
 def matches(self,r,identity=False):return self.valid(r) and (r.provider in VERIFIED_IDENTITY_PROVIDERS if identity else r.provider in ONLINE_PROVIDERS)
 def search(self,q,scene_index,identity=False,contextual=False):
  for text in self.variants(q,contextual):
   current={**q,'primary':text,'identity_required':identity}
   if contextual:current['subject']=text;current['subject_type']='concept'
   for provider in self.providers(identity):
    try:
     r=provider.search(current,scene_index,self.used)
     if self.matches(r,identity):self.used.update({r.source_url,r.asset_id});return r
    except Exception as e:print(f'ASSET SKIP {provider.name} {text!r}: {e}')
  return None
 def lead_image(self,q,scene_index):
  url=str(self.research.get('leadImageUrl') or '').strip()
  if not url:return None
  suffix='.png' if '.png' in url.lower() else '.jpg';subject=q.get('subject') or self.research.get('canonicalTitle') or 'subject';path=self.assets_dir/f'scene-{scene_index:02d}-topic-{safe_name(subject)}{suffix}';cache=self.cache_dir/f'lead-{safe_name(subject)}{suffix}'
  _,mime,_=download(url,path,headers={'User-Agent':'premium-sticktalk/9.0'},cache_path=cache)
  return AssetResult(scene_index,str(path),'photo','wikipedia-topic-image',str(self.research.get('sourceUrl') or url),'Wikipedia contributor','','source-page','',f'{subject} topic lead',datetime.now(timezone.utc).isoformat(),0,0,mime,100,f'lead-{safe_name(subject)}')
 def item(self,r,scene,role,subject,queries):
  d=r.manifest();d.update({'scene':scene,'role':role,'fallback':False,'identityQuery':subject,'identityVerified':r.provider in VERIFIED_IDENTITY_PROVIDERS,'topicMatched':r.provider in ONLINE_PROVIDERS,'searchQueries':queries,'cutoutStyle':'white-outline-yellow-shadow'});return d
 def generate(self,story):
  # Rebuild visual identity from researched subject every run. Generated labels can never win.
  story=plan_entities(story,story.get('topic') or story.get('title'));self.research=story.get('research') or {};scenes=story.get('scenes') or [];plan=story.get('entityVisualPlan') or {}
  canonical=str(self.research.get('canonicalTitle') or plan.get('mainEntity') or story.get('resolvedSubject') or story.get('title') or '').strip();entity_type=str(story.get('resolvedEntityType') or plan.get('mainEntityType') or 'concept').casefold()
  # Guard against stale/generic labels from old Story Engine.
  bad={'nhạc chủ đề','tài liệu gốc','mốc thời gian','ảnh bối cảnh','documentary subject'}
  if canonical.casefold() in bad:raise RuntimeError(f'Chủ thể hình ảnh không hợp lệ: {canonical!r}. Research stage phải cung cấp canonicalTitle trước khi tìm ảnh.')
  manifest=[];gallery=[];print(f'IMAGE ENGINE subject={canonical!r} type={entity_type}')
  # Canonical Wikipedia lead is the safest high-relevance main visual. Download it once,
  # then use scene-specific web search for alternates and context. This also avoids hammering Commons.
  lead=None
  baseq={'subject':canonical}
  try:lead=self.lead_image(baseq,1)
  except Exception as e:print(f'LEAD IMAGE SKIP: {e}')
  for idx,scene in enumerate(scenes,1):
   q=keyword(scene);q['subject']=canonical;q['subject_type']=entity_type;identity=entity_type=='person';q['identity_required']=identity
   main=None
   # Scene 1 always prefers verified canonical lead. Later scenes try a distinct web image first.
   if idx==1 and lead:main=lead
   if not main:main=self.search(q,idx,identity=identity,contextual=False)
   if not main and lead:main=lead
   if not main:raise RuntimeError(f'Không tìm được ảnh web phù hợp cho chủ thể {canonical!r}; dừng thay vì render placeholder sai chủ đề.')
   main_path=Path(main.file).as_posix();scene['image']=main_path;scene['asset']=main_path;scene['assetProvider']=main.provider;scene['assetSource']=main.source_url;scene['identityVerified']=main.provider in VERIFIED_IDENTITY_PROVIDERS;scene['topicMatched']=True
   manifest.append(self.item(main,idx,'main-subject',canonical,self.variants(q)))
   if main_path not in gallery:gallery.append(main_path)
   scene['assets']=[]
   # Context imagery is always based on THIS scene's fact/event/location and can use multiple providers.
   attempts=0
   while len(scene['assets'])<2 and attempts<4:
    attempts+=1;extra=self.search(q,idx,identity=False,contextual=True)
    if not extra:break
    p=Path(extra.file).as_posix()
    if p==main_path or p in scene['assets']:continue
    scene['assets'].append(p);manifest.append(self.item(extra,idx,'context-evidence',canonical,self.variants(q,True)))
    if p not in gallery and len(gallery)<MAX_TOPIC_PHOTOS:gallery.append(p)
  story['assetProviderSystem']='vox-research-authoritative-assets-v9';story['template']=VOX_TEMPLATE;story['topicImageGallery']=gallery[:MAX_TOPIC_PHOTOS];story['topicSubjectImages']=len(gallery);story['topicImageMinimumMet']=len(gallery)>=MIN_TOPIC_PHOTOS;story['resolvedEntityType']=entity_type
  self.story_path.write_text(json.dumps(story,ensure_ascii=False,indent=2),encoding='utf-8');(self.output_dir/'asset-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8');(self.output_dir/'credits.txt').write_text('\n'.join(['Asset credits','=============','']+[f"Scene {x['scene']}: {x['provider']} — {x['source_url']} — role={x['role']}" for x in manifest])+'\n',encoding='utf-8')
  if entity_type=='person' and any(not x['identityVerified'] for x in manifest if x['role']=='main-subject'):raise RuntimeError('Ảnh nhân vật chính chưa xác minh; dừng trước khi render sai người.')
  print(f'IMAGE ENGINE OK: {len(gallery)} unique web images; Pexels={bool(os.getenv("PEXELS_API_KEY"))}; Pixabay={bool(os.getenv("PIXABAY_API_KEY"))}');return story

def generate_assets(story):
 path=Path('assets/story.json')
 if isinstance(story,(str,Path)):path=Path(story);data=json.loads(path.read_text(encoding='utf-8'))
 else:data=story
 return AssetManager(story_path=path).generate(data)
if __name__=='__main__':generate_assets(Path(os.getenv('STORY_PATH','assets/story.json')))
