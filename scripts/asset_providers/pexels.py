import os,json,urllib.parse,urllib.request
from datetime import datetime,timezone
from .base import AssetProvider,AssetResult,cache_key,download,safe_name,is_valid_license
from .scoring import asset_quality_score
class PexelsProvider(AssetProvider):
 name='pexels'
 def search(self,q,scene_index,used):
  key=os.getenv('PEXELS_API_KEY','').strip()
  if not key: return None
  url='https://api.pexels.com/v1/search?'+urllib.parse.urlencode({'query':q['primary'],'orientation':'portrait','per_page':12})
  data=json.load(urllib.request.urlopen(urllib.request.Request(url,headers={'Authorization':key}),timeout=20))
  candidates=[]
  for p in data.get('photos',[]):
   sid=str(p.get('id')); source=p.get('url',''); src=p.get('src',{}).get('portrait') or p.get('src',{}).get('large2x')
   cand={'asset_id':sid,'source_url':source,'asset_type':'photo','width':p.get('width',0),'height':p.get('height',0),'author':p.get('photographer','Pexels contributor'),'author_url':p.get('photographer_url',''),'license':'Pexels License','license_url':'https://www.pexels.com/license/','alt':p.get('alt',''),'clear_subject':True}
   if src and sid not in used and source not in used and is_valid_license(cand['license'],cand['license_url']):
    cand['qualityScore']=asset_quality_score(cand,q,q.get('template',''))
    candidates.append((cand,src))
  for cand,src in sorted(candidates,key=lambda x:x[0]['qualityScore'],reverse=True):
   ext='.jpg'; path=self.out_dir/f"scene-{scene_index:02d}-{safe_name(q['primary'])}{ext}"; cp=self.cache_dir/(cache_key(self.name,q['primary'],q.get('template',''),'portrait')+ext)
   _,mt,_=download(src,path,cache_path=cp)
   used.update({cand['asset_id'],cand['source_url']})
   return AssetResult(scene_index,str(path),'photo',self.name,cand['source_url'],cand['author'],cand.get('author_url',''),cand['license'],cand['license_url'],q['primary'],datetime.now(timezone.utc).isoformat(),cand['width'],cand['height'],mt,cand['qualityScore'],cand['asset_id'])
  return None
