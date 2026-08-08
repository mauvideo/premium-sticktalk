from __future__ import annotations
import json,os,re
from pathlib import Path
from .base import is_valid_mime
from .openverse import OpenverseProvider
from .pexels import PexelsProvider
from .pixabay import PixabayProvider
from .unsplash import UnsplashProvider
from scripts.entity_visual_planner import plan_entities
VOX_TEMPLATE='vox-paper-collage';MIN_TOPIC_PHOTOS=3;ONLINE_PROVIDERS={'openverse','pexels','pixabay','unsplash'}
PERSON_TYPES={'person','people','historical_person','politician','military_person','celebrity','athlete'}
def keyword(scene):
 p=scene.get('entityVisualPlan') or {};qs=p.get('searchQueries') or scene.get('visualQueries') or []
 return {'primary':qs[0] if qs else p.get('mainSubject','documentary subject'),'secondary':qs[1:],'asset_type':'photo','style':'editorial documentary paper collage','emotion':'documentary','subject':p.get('mainSubject','documentary subject'),'subject_type':p.get('mainSubjectType','concept'),'identity_required':False,'event':p.get('event','') or scene.get('event',''),'setting':p.get('location',''),'time_period':p.get('timePeriod',''),'visual_evidence':p.get('visualEvidence') or [],'template':VOX_TEMPLATE,'size':'9:16'}
class AssetManager:
 def __init__(self,story_path='assets/story.json',assets_dir='assets/generated-assets',output_dir='output',cache_dir='assets/.asset-cache'):
  self.story_path=Path(story_path);self.assets_dir=Path(assets_dir);self.output_dir=Path(output_dir);self.cache_dir=Path(cache_dir)
  for p in (self.assets_dir,self.output_dir,self.cache_dir):p.mkdir(parents=True,exist_ok=True)
  self.used=set();self.research={}
 def providers(self):return [PexelsProvider(self.assets_dir,self.cache_dir),PixabayProvider(self.assets_dir,self.cache_dir),UnsplashProvider(self.assets_dir,self.cache_dir),OpenverseProvider(self.assets_dir,self.cache_dir)]
 @staticmethod
 def _clean(v):return re.sub(r'\s+',' ',str(v or '').replace('"',' ')).strip(' ,;:-')[:180]
 def variants(self,q,canonical,identity=False):
  s=self._clean(canonical);e=self._clean(q.get('event'));loc=self._clean(q.get('setting'));raw=[]
  # Named people/entities must remain in every high-priority query. This prevents a Võ Nguyên Giáp topic from drifting to generic soldiers.
  if identity and s:
   raw += [s,f'{s} portrait',f'{s} photo']
   if e:raw += [f'{s} {e}',f'{s} {e} photo']
   if loc:raw.append(f'{s} {loc}')
  else:
   raw += [q.get('primary'),*(q.get('secondary') or [])]
   if e:raw += [e,f'{e} photo',f'{e} people']
   if e and loc:raw.append(f'{e} {loc}')
   if s:raw += [f'{s} {e}' if e else '',s,f'{s} photo']
  seen=set();out=[]
  for v in raw:
   v=self._clean(v);k=v.casefold()
   if v and k not in seen:seen.add(k);out.append(v)
  return out[:14]
 def semantic_variants(self,scene,q,canonical,identity=False):
  headline=self._clean(scene.get('headline'));event=self._clean(scene.get('event') or q.get('event'));loc=self._clean(q.get('setting'));evidence=[self._clean(x) for x in (q.get('visual_evidence') or []) if self._clean(x)];raw=[]
  if identity:
   # Keep the named entity anchored even during fallback; context may broaden, identity may not.
   raw += [f'{canonical} {x}' for x in [event,headline,loc,*evidence] if x]
   raw += [canonical,f'{canonical} documentary',f'{canonical} historical photo']
  else:
   # Lifestyle/how-to topics are action-first: gym -> actual exercising, treadmill, weights, stretching, etc.
   raw += [*evidence,event,headline]
   if event and loc:raw += [f'{event} {loc}',f'{event} activity {loc}']
   if headline and loc:raw.append(f'{headline} {loc}')
   if event:raw += [f'{event} people',f'person {event}',f'{event} activity',f'{event} environment']
   if headline:raw += [f'{headline} people',f'person {headline}',f'{headline} activity']
   raw += [f'{canonical} {event}' if event else '',f'people {canonical}',f'{canonical} activity',canonical]
  seen=set();out=[]
  for v in raw:
   v=self._clean(v);k=v.casefold()
   if v and k not in seen:seen.add(k);out.append(v)
  return out[:18]
 def valid(self,r):return bool(r and Path(r.file).exists() and Path(r.file).stat().st_size>700 and is_valid_mime(r.mime_type) and r.provider and r.qualityScore>=0)
 def matches(self,r):return self.valid(r) and r.provider in ONLINE_PROVIDERS
 def search_texts(self,q,scene_index,texts,identity=False,canonical=''):
  for text in texts:
   # Providers receive identity_required for named-person searches instead of being forced to generic concept mode.
   current={**q,'primary':text,'subject':canonical if identity else text,'subject_type':q.get('subject_type') if identity else 'concept','identity_required':identity}
   for provider in self.providers():
    try:
     r=provider.search(current,scene_index,self.used)
     if self.matches(r):self.used.update({r.source_url,r.asset_id});return r
    except Exception as e:print(f'ASSET SKIP {provider.name} {text!r}: {e}')
  return None
 def item(self,r,scene,role,subject,queries,fallback=False,identity=False):
  d=r.manifest();d.update({'scene':scene,'role':role,'fallback':fallback,'identityQuery':subject,'identityVerified':identity,'topicMatched':True,'searchQueries':queries,'cutoutStyle':'white-outline-yellow-shadow'});return d
 def generate(self,story):
  story=plan_entities(story,story.get('topic') or story.get('title'));self.research=story.get('research') or {};scenes=story.get('scenes') or [];plan=story.get('entityVisualPlan') or {}
  canonical=str(self.research.get('canonicalTitle') or self.research.get('canonicalSubject') or plan.get('mainEntity') or story.get('resolvedSubject') or story.get('title') or '').strip();entity_type=str(story.get('resolvedEntityType') or plan.get('mainEntityType') or 'concept').casefold();identity=entity_type in PERSON_TYPES or bool(self.research.get('isNamedPerson'))
  bad={'nhạc chủ đề','tài liệu gốc','mốc thời gian','ảnh bối cảnh','documentary subject'}
  if canonical.casefold() in bad:raise RuntimeError(f'Chủ thể hình ảnh không hợp lệ: {canonical!r}')
  manifest=[];gallery=[];max_gallery=max(12,len(scenes)*3);last_good=None
  print(f'IMAGE ENGINE subject={canonical!r} type={entity_type} identity={identity} mode=entity-first-scene-accurate')
  for idx,scene in enumerate(scenes,1):
   q=keyword(scene);q['subject']=canonical;q['subject_type']=entity_type;q['identity_required']=identity
   exact=self.variants(q,canonical,identity);main=self.search_texts(q,idx,exact,identity,canonical);fallback=False
   if not main:
    semantic=self.semantic_variants(scene,q,canonical,identity);print(f'ASSET SEMANTIC FALLBACK scene {idx}: {semantic[:8]}');main=self.search_texts(q,idx,semantic,identity,canonical);fallback=bool(main)
   # For a named person, never silently substitute a different person. Reuse a previously found image of the same entity instead.
   if not main and identity and last_good:print(f'ASSET IDENTITY FALLBACK scene {idx}: reuse same named entity image');main=last_good;fallback=True
   # For generic/lifestyle topics, reuse only after action/context searches have failed.
   if not main and not identity and last_good:print(f'ASSET AVAILABILITY FALLBACK scene {idx}: reuse previous topic image');main=last_good;fallback=True
   if not main:raise RuntimeError(f'Không tìm được ảnh phù hợp cho scene {idx}, chủ đề {canonical!r}.')
   last_good=main;main_path=Path(main.file).as_posix();scene['image']=main_path;scene['asset']=main_path;scene['assetProvider']=main.provider;scene['assetSource']=main.source_url;scene['topicMatched']=True;scene['identityVerified']=identity;scene['semanticImageFallback']=fallback
   manifest.append(self.item(main,idx,'named-entity' if identity else ('main-subject' if not fallback else 'semantic-topic-match'),canonical,exact,fallback,identity));gallery += [] if main_path in gallery else [main_path];scene['assets']=[]
   support=self.semantic_variants(scene,q,canonical,identity);attempts=0
   while len(scene['assets'])<2 and attempts<3:
    attempts+=1;extra=self.search_texts(q,idx,support,identity,canonical)
    if not extra:break
    p=Path(extra.file).as_posix()
    if p==main_path or p in scene['assets']:continue
    scene['assets'].append(p);manifest.append(self.item(extra,idx,'context-evidence',canonical,support,True,identity))
    if p not in gallery and len(gallery)<max_gallery:gallery.append(p)
  story['assetProviderSystem']='vox-entity-first-scene-accurate-v14';story['template']=VOX_TEMPLATE;story['topicImageGallery']=gallery[:max_gallery];story['topicSubjectImages']=len(gallery);story['topicImageMinimumMet']=len(gallery)>=MIN_TOPIC_PHOTOS;story['resolvedEntityType']=entity_type
  self.story_path.write_text(json.dumps(story,ensure_ascii=False,indent=2),encoding='utf-8');(self.output_dir/'asset-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8');(self.output_dir/'credits.txt').write_text('\n'.join(['Asset credits','=============','']+[f"Scene {x['scene']}: {x['provider']} — {x['source_url']} — role={x['role']}" for x in manifest])+'\n',encoding='utf-8');print(f'IMAGE ENGINE OK: {len(gallery)} unique images');return story
def generate_assets(story):
 path=Path('assets/story.json')
 if isinstance(story,(str,Path)):path=Path(story);data=json.loads(path.read_text(encoding='utf-8'))
 else:data=story
 return AssetManager(story_path=path).generate(data)
if __name__=='__main__':generate_assets(Path(os.getenv('STORY_PATH','assets/story.json')))
