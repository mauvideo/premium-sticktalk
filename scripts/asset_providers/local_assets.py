from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import shutil
from .base import AssetProvider,AssetResult,safe_name,cache_key
from .scoring import asset_quality_score

ROOT = Path(__file__).resolve().parents[2]
LOCAL_MAP={
 'stick-figure':['assets/free-assets/stick-figure/walking.svg','assets/free-assets/stick-figure/presenting.svg'],
 'paper-sketch':['assets/free-assets/hand-drawn/line-landscape.svg','assets/free-assets/hand-drawn/arrows.svg'],
 'paper-cut-documentary':['assets/free-assets/paper-cut/collage-card.svg','assets/free-assets/paper-cut/tape-arrow.svg'],
 'kinetic-captions':['assets/free-assets/textures/paper-grain.svg','assets/free-assets/nature/path.svg'],
 'business-motivation':['assets/free-assets/business/desk.svg','assets/free-assets/icons/goal.svg'],
 'smooth-transitions':['assets/free-assets/nature/path.svg','assets/free-assets/icons/idea.svg'],
 'prompt-to-video':['assets/free-assets/nature/path.svg','assets/free-assets/business/desk.svg'],
 'photo':['assets/free-assets/nature/path.svg','assets/free-assets/business/desk.svg'],
}
class LocalAssetsProvider(AssetProvider):
    name='local-assets'
    def search(self,query,scene_index,used):
        template=query.get('template','photo'); choices=LOCAL_MAP.get(template) or LOCAL_MAP.get('photo')
        ranked=[]
        for src in choices:
            source='local://'+src
            cand={'asset_id':source,'source_url':source,'asset_type':query.get('asset_type','svg'),'width':600,'height':900,'author':'Premium StickTalk','license':'Local fallback asset','license_url':'docs/free-asset-providers.md#local-fallback-assets','mime_type':'image/svg+xml','clear_subject':True,'alt':src}
            cand['qualityScore']=asset_quality_score(cand,query,template,duplicate=source in used)
            ranked.append((cand,ROOT / src))
        cand,src=max(ranked,key=lambda x:x[0]['qualityScore'])
        if cand['source_url'] in used:
            cand,src=ranked[scene_index % len(ranked)]
        path=self.out_dir/f"scene-{scene_index:02d}-{safe_name(template)}-{src.name}"
        path.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,path)
        used.add(cand['source_url'])
        return AssetResult(scene_index,str(path),query.get('asset_type','svg'),self.name,cand['source_url'],cand['author'],'',cand['license'],cand['license_url'],query.get('primary',''),datetime.now(timezone.utc).isoformat(),600,900,'image/svg+xml',cand['qualityScore'],cand['asset_id'])
