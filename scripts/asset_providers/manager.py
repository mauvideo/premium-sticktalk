from __future__ import annotations
import json,os,re
from pathlib import Path
from .base import is_valid_mime
from .openverse import OpenverseProvider
from .pexels import PexelsProvider
from .pixabay import PixabayProvider
from .unsplash import UnsplashProvider
from scripts.entity_visual_planner import plan_entities

VOX_TEMPLATE='vox-paper-collage';MIN_TOPIC_PHOTOS=3
ONLINE_PROVIDERS={'openverse','pexels','pixabay','unsplash'}
PERSON_TYPES={'person','people','historical_person','politician','military_person','celebrity','athlete'}

def keyword(scene):
 p=scene.get('entityVisualPlan') or {};qs=p.get('searchQueries') or scene.get('visualQueries') or []
 return {'primary':qs[0] if qs else p.get('mainSubject','documentary subject'),'secondary':qs[1:],'asset_type':'photo','style':'editorial documentary paper collage','emotion':'documentary','subject':p.get('mainSubject','documentary subject'),'subject_type':p.get('mainSubjectType','concept'),'identity_required':False,'event':p.get('event','') or scene.get('event',''),'setting':p.get('location',''),'time_period':p.get('timePeriod',''),'visual_evidence':p.get('visualEvidence') or [],'template':VOX_TEMPLATE,'size':'9:16'}

class AssetManager:
 def __init__(self,story_path='assets/story.json',assets_dir='assets/generated-assets',output_dir='output',cache_dir='assets/.asset-cache'):
  self.story_path=Path(story_path);self.assets_dir=Path(assets_dir);self.output_dir=Path(output_dir);self.cache_dir=Path(cache_dir)
  for p in (self.assets_dir,self.output_dir,self.cache_dir):p.mkdir(parents=True,exist_ok=True)
  self.used=set();self.research={}
 def providers(self,identity=False):
  # Luôn thử cả 4 nguồn. Thứ tự chỉ là ưu tiên, không dừng ở nguồn đầu tiên.
  if identity:return [OpenverseProvider(self.assets_dir,self.cache_dir),PexelsProvider(self.assets_dir,self.cache_dir),PixabayProvider(self.assets_dir,self.cache_dir),UnsplashProvider(self.assets_dir,self.cache_dir)]
  return [PexelsProvider(self.assets_dir,self.cache_dir),PixabayProvider(self.assets_dir,self.cache_dir),UnsplashProvider(self.assets_dir,self.cache_dir),OpenverseProvider(self.assets_dir,self.cache_dir)]
 @staticmethod
 def _clean(v):return re.sub(r'\s+',' ',str(v or '').replace('"',' ')).strip(' ,;:-')[:180]
 def variants(self,q,canonical,identity=False):
  s=self._clean(canonical);e=self._clean(q.get('event'));loc=self._clean(q.get('setting'));raw=[]
  if identity and s:
   raw += [s,f'{s} portrait',f'{s} historical photo',f'{s} archival photograph']
   if e:raw += [f'{s} {e}',f'{s} {e} historical photo']
   if loc:raw.append(f'{s} {loc}')
  else:
   raw += [q.get('primary'),*(q.get('secondary') or [])]
   if e:raw += [e,f'{e} photo',f'{e} people',f'person {e}']
   if e and loc:raw += [f'{e} {loc}',f'people {e} {loc}']
   if loc:raw.append(loc)
   if s:raw += [f'{s} {e}' if e else '',f'people {s}',f'{s} activity',s]
  seen=set();out=[]
  for v in raw:
   v=self._clean(v);k=v.casefold()
   if v and k not in seen:seen.add(k);out.append(v)
  return out[:18]
 def semantic_variants(self,scene,q,canonical,identity=False):
  headline=self._clean(scene.get('headline'));event=self._clean(scene.get('event') or q.get('event'));loc=self._clean(q.get('setting'));evidence=[self._clean(x) for x in (q.get('visual_evidence') or []) if self._clean(x)];raw=[]
  if identity:
   raw += [f'{canonical} {x}' for x in [event,headline,loc,*evidence] if x]
   raw += [canonical,f'{canonical} portrait',f'{canonical} documentary',f'{canonical} historical photo']
  else:
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
  return out[:20]
 def context_variants(self,scene,q,canonical):
  event=self._clean(scene.get('event') or q.get('event'));headline=self._clean(scene.get('headline'));loc=self._clean(q.get('setting'));evidence=[self._clean(x) for x in (q.get('visual_evidence') or []) if self._clean(x)]
  raw=[event,headline,*evidence]
  if event and loc:raw += [f'{event} {loc}',f'{event} historical photo']
  if loc:raw += [loc,f'{loc} historical photo']
  raw += [f'{canonical} era historical context',f'{canonical} documentary context']
  seen=set();out=[]
  for v in raw:
   v=self._clean(v);k=v.casefold()
   if v and k not in seen:seen.add(k);out.append(v)
  return out[:14]
 def valid(self,r):return bool(r and Path(r.file).exists() and Path(r.file).stat().st_size>700 and is_valid_mime(r.mime_type) and r.provider in ONLINE_PROVIDERS)
 def score(self,r,query_index=0,identity=False):
  if not self.valid(r):return -999
  base=float(getattr(r,'qualityScore',0) or 0)
  # Query càng cụ thể càng được thưởng; người thật cần ưu tiên kết quả từ truy vấn chứa tên.
  return base + max(0,12-query_index*1.2) + (8 if identity and query_index<4 else 0)
 def search_best(self,q,scene_index,texts,identity=False,canonical='',strict=True):
  candidates=[]
  # Mỗi phân cảnh hỏi tất cả 4 nguồn, lấy ứng viên tốt nhất thay vì dừng ở kết quả đầu tiên.
  for qi,text in enumerate(texts[:12]):
   current={**q,'primary':text,'subject':canonical if identity else text,'subject_type':q.get('subject_type') if identity else 'concept','identity_required':identity}
   for provider in self.providers(identity):
    try:
     r=provider.search(current,scene_index,self.used)
     if self.valid(r):
      s=self.score(r,qi,identity);candidates.append((s,r,text,provider.name))
      print(f'ASSET CANDIDATE scene {scene_index} {provider.name} score={s:.1f} query={text!r}')
    except Exception as e:print(f'ASSET SKIP {provider.name} {text!r}: {e}')
  if not candidates:return None
  candidates.sort(key=lambda x:x[0],reverse=True)
  threshold=55 if identity else 28
  if not strict:threshold=18 if identity else 14
  for s,r,text,provider_name in candidates:
   if s>=threshold:
    self.used.update({r.source_url,r.asset_id});print(f'ASSET PICK scene {scene_index}: {provider_name} score={s:.1f} query={text!r}');return r
  # Nếu không có ảnh đạt ngưỡng, vẫn chọn ảnh tốt nhất ở chế độ mềm để workflow không chết vì một cảnh.
  if not strict:
   s,r,text,provider_name=candidates[0]
   if s>=10:
    self.used.update({r.source_url,r.asset_id});print(f'ASSET SOFT PICK scene {scene_index}: {provider_name} score={s:.1f} query={text!r}');return r
  print(f'ASSET NO PICK scene {scene_index}: best={candidates[0][0]:.1f} threshold={threshold}')
  return None
 def item(self,r,scene,role,subject,queries,fallback=False,identity=False):
  d=r.manifest();d.update({'scene':scene,'role':role,'fallback':fallback,'identityQuery':subject,'identityAnchored':identity,'topicMatched':True,'searchQueries':queries,'cutoutStyle':'white-outline-yellow-shadow'});return d
 def generate(self,story):
  story=plan_entities(story,story.get('topic') or story.get('title'));self.research=story.get('research') or {};scenes=story.get('scenes') or [];plan=story.get('entityVisualPlan') or {}
  canonical=str(self.research.get('canonicalTitle') or self.research.get('canonicalSubject') or plan.get('mainEntity') or story.get('resolvedSubject') or story.get('title') or '').strip();entity_type=str(story.get('resolvedEntityType') or plan.get('mainEntityType') or 'concept').casefold();identity=entity_type in PERSON_TYPES or bool(self.research.get('isNamedPerson'))
  bad={'nhạc chủ đề','tài liệu gốc','mốc thời gian','ảnh bối cảnh','documentary subject'}
  if canonical.casefold() in bad:raise RuntimeError(f'Chủ thể hình ảnh không hợp lệ: {canonical!r}')
  manifest=[];gallery=[];max_gallery=max(12,len(scenes)*3);last_exact=None;last_topic=None
  print(f'IMAGE ENGINE subject={canonical!r} type={entity_type} identity={identity} mode=multi-source-ranking-v17')
  for idx,scene in enumerate(scenes,1):
   q=keyword(scene);q['subject']=canonical;q['subject_type']=entity_type;q['identity_required']=identity
   exact=self.variants(q,canonical,identity);main=self.search_best(q,idx,exact,identity,canonical,strict=True);fallback=False;role='named-entity' if identity else 'scene-exact'
   if not main:
    semantic=self.semantic_variants(scene,q,canonical,identity);print(f'ASSET SEMANTIC scene {idx}: {semantic[:8]}');main=self.search_best(q,idx,semantic,identity,canonical,strict=False);fallback=bool(main);role='named-entity-context' if identity else 'scene-semantic'
   if not main and identity:
    context=self.context_variants(scene,q,canonical);print(f'ASSET CONTEXT scene {idx}: {context[:8]}');main=self.search_best({**q,'identity_required':False},idx,context,False,canonical,strict=False);fallback=bool(main);role='historical-context'
   # Không để một phân cảnh làm chết toàn workflow: ưu tiên dùng lại ảnh đúng chủ đề đã tìm được.
   if not main and identity and last_exact:
    print(f'ASSET IDENTITY REUSE scene {idx}: dùng lại ảnh đúng nhân vật');main=last_exact;fallback=True;role='named-entity-reuse'
   if not main and last_topic:
    print(f'ASSET TOPIC REUSE scene {idx}: dùng lại ảnh cùng chủ đề');main=last_topic;fallback=True;role='topic-reuse'
   if not main:
    raise RuntimeError(f'Không tìm được bất kỳ ảnh hợp lệ nào từ 4 nguồn cho phân cảnh {idx}, chủ đề {canonical!r}.')
   if identity and role.startswith('named-entity'):last_exact=main
   last_topic=main
   main_path=Path(main.file).as_posix();scene['image']=main_path;scene['asset']=main_path;scene['assetProvider']=main.provider;scene['assetSource']=main.source_url;scene['topicMatched']=True;scene['identityAnchored']=identity and role.startswith('named-entity');scene['semanticImageFallback']=fallback;scene['assetRole']=role
   manifest.append(self.item(main,idx,role,canonical,exact,fallback,identity and role.startswith('named-entity')));gallery += [] if main_path in gallery else [main_path];scene['assets']=[]
   support=self.context_variants(scene,q,canonical) if identity else self.semantic_variants(scene,q,canonical,False)
   # Ảnh phụ cũng lấy theo xếp hạng nhiều nguồn, tối đa 2 ảnh/cảnh.
   for _ in range(2):
    extra=self.search_best({**q,'identity_required':False},idx,support,False,canonical,strict=False)
    if not extra:break
    p=Path(extra.file).as_posix()
    if p==main_path or p in scene['assets']:continue
    scene['assets'].append(p);manifest.append(self.item(extra,idx,'context-evidence',canonical,support,True,False))
    if p not in gallery and len(gallery)<max_gallery:gallery.append(p)
  story['assetProviderSystem']='vox-multi-source-ranking-v17';story['template']=VOX_TEMPLATE;story['topicImageGallery']=gallery[:max_gallery];story['topicSubjectImages']=len(gallery);story['topicImageMinimumMet']=len(gallery)>=MIN_TOPIC_PHOTOS;story['resolvedEntityType']=entity_type
  self.story_path.write_text(json.dumps(story,ensure_ascii=False,indent=2),encoding='utf-8');(self.output_dir/'asset-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8');(self.output_dir/'credits.txt').write_text('\n'.join(['Asset credits','=============','']+[f"Scene {x['scene']}: {x['provider']} — {x['source_url']} — role={x['role']}" for x in manifest])+'\n',encoding='utf-8');print(f'IMAGE ENGINE OK: {len(gallery)} unique images');return story

def generate_assets(story):
 path=Path('assets/story.json')
 if isinstance(story,(str,Path)):path=Path(story);data=json.loads(path.read_text(encoding='utf-8'))
 else:data=story
 return AssetManager(story_path=path).generate(data)
if __name__=='__main__':generate_assets(Path(os.getenv('STORY_PATH','assets/story.json')))
