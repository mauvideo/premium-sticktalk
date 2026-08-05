import os,json,urllib.parse,urllib.request
from datetime import datetime,timezone
from .base import AssetProvider,AssetResult,cache_key,download,safe_name,is_valid_license
from .scoring import asset_quality_score
class UnsplashProvider(AssetProvider):
 name='unsplash'
 def search(self,q,scene_index,used):
  key=os.getenv('UNSPLASH_ACCESS_KEY','').strip()
  if not key: return None
  url='https://api.unsplash.com/search/photos?'+urllib.parse.urlencode({'query':q['primary'],'orientation':'portrait','per_page':12,'client_id':key})
  data=json.load(urllib.request.urlopen(url,timeout=20)); candidates=[]
  for p in data.get('results',[]):
   sid=p.get('id'); source=p.get('links',{}).get('html',''); src=p.get('urls',{}).get('regular'); u=p.get('user',{})
   cand={'asset_id':sid,'source_url':source,'asset_type':'photo','width':p.get('width',0),'height':p.get('height',0),'author':u.get('name','Unsplash contributor'),'author_url':u.get('links',{}).get('html',''),'license':'Unsplash License','license_url':'https://unsplash.com/license','alt':p.get('alt_description') or p.get('description') or '','clear_subject':True}
   if src and sid not in used and source not in used and is_valid_license(cand['license'],cand['license_url']): cand['qualityScore']=asset_quality_score(cand,q,q.get('template','')); candidates.append((cand,src))
  for cand,src in sorted(candidates,key=lambda x:x[0]['qualityScore'],reverse=True):
   path=self.out_dir/f"scene-{scene_index:02d}-{safe_name(q['primary'])}.jpg"; cp=self.cache_dir/(cache_key(self.name,q['primary'],q.get('template',''),'portrait')+'.jpg')
   _,mt,_=download(src,path,cache_path=cp); used.update({cand['asset_id'],cand['source_url']})
   return AssetResult(scene_index,str(path),'photo',self.name,cand['source_url'],cand['author'],cand['author_url'],cand['license'],cand['license_url'],q['primary'],datetime.now(timezone.utc).isoformat(),cand['width'],cand['height'],mt,cand['qualityScore'],cand['asset_id'])
  return None
