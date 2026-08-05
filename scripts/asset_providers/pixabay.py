import os,json,urllib.parse,urllib.request
from datetime import datetime,timezone
from .base import AssetProvider,AssetResult,cache_key,download,safe_name,is_valid_license
from .scoring import asset_quality_score
class PixabayProvider(AssetProvider):
 name='pixabay'
 def search(self,q,scene_index,used):
  key=os.getenv('PIXABAY_API_KEY','').strip()
  if not key: return None
  url='https://pixabay.com/api/?'+urllib.parse.urlencode({'key':key,'q':q['primary'],'image_type':'photo','orientation':'vertical','per_page':12,'safesearch':'true'})
  data=json.load(urllib.request.urlopen(url,timeout=20)); candidates=[]
  for p in data.get('hits',[]):
   sid=str(p.get('id')); source=p.get('pageURL',''); src=p.get('largeImageURL') or p.get('webformatURL')
   cand={'asset_id':sid,'source_url':source,'asset_type':'photo','width':p.get('imageWidth',0),'height':p.get('imageHeight',0),'author':p.get('user','Pixabay contributor'),'license':'Pixabay Content License','license_url':'https://pixabay.com/service/license-summary/','alt':p.get('tags',''),'clear_subject':True}
   if src and sid not in used and source not in used and is_valid_license(cand['license'],cand['license_url']): cand['qualityScore']=asset_quality_score(cand,q,q.get('template','')); candidates.append((cand,src))
  for cand,src in sorted(candidates,key=lambda x:x[0]['qualityScore'],reverse=True):
   path=self.out_dir/f"scene-{scene_index:02d}-{safe_name(q['primary'])}.jpg"; cp=self.cache_dir/(cache_key(self.name,q['primary'],q.get('template',''),'portrait')+'.jpg')
   _,mt,_=download(src,path,cache_path=cp); used.update({cand['asset_id'],cand['source_url']})
   return AssetResult(scene_index,str(path),'photo',self.name,cand['source_url'],cand['author'],'',cand['license'],cand['license_url'],q['primary'],datetime.now(timezone.utc).isoformat(),cand['width'],cand['height'],mt,cand['qualityScore'],cand['asset_id'])
  return None
