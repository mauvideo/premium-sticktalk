import json
from pathlib import Path
from scripts.asset_providers.manager import AssetManager, generate_assets
from scripts.asset_providers.base import AssetResult

class FakeProvider:
    name='fake'
    def __init__(self, out, provider='fake', license='CC0 1.0', source_prefix='https://example.test/asset'):
        self.out_dir=Path(out); self.provider=provider; self.license=license; self.source_prefix=source_prefix; self.calls=0
    def search(self,q,i,used):
        self.calls += 1
        p=self.out_dir/f'{self.provider}-{i}.svg'; p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 900"><rect width="600" height="900" fill="#fff"/><path d="M10 10H590V890H10Z" fill="none" stroke="#111" stroke-width="8"/></svg>')
        source=f'{self.source_prefix}-{i}'
        return AssetResult(i,str(p),q['asset_type'],self.provider,source,'Author','','CC0 1.0','https://creativecommons.org/publicdomain/zero/1.0/',q['primary'],'2026-08-05T00:00:00Z',600,900,'image/svg+xml',92,source)
class FailingProvider:
    name='fail'
    def __init__(self,out): pass
    def search(self,*a): raise RuntimeError('offline')
class UnknownLicenseProvider(FakeProvider):
    name='unknown'
    def search(self,q,i,used):
        r=super().search(q,i,used); r.license='unknown'; r.license_url=''; return r
class DuplicateProvider(FakeProvider):
    name='duplicate'
    def search(self,q,i,used):
        r=super().search(q,i,used); r.source_url='https://example.test/same'; r.asset_id='same'; return None if r.source_url in used else r

def story(): return {'template':'prompt-to-video','scenes':[{'id':1,'duration':4,'headline':'Ý chí','narration':'Người Việt hiển thị đúng chữ có dấu.'},{'id':2,'duration':4,'headline':'Hành động','narration':'Bắt đầu bằng một bước nhỏ.'},{'id':3,'duration':4,'headline':'Kết quả','narration':'Không bỏ cuộc.'}]}

def test_no_api_keys_creates_assets_for_every_scene(monkeypatch,tmp_path):
    monkeypatch.delenv('PEXELS_API_KEY',raising=False); monkeypatch.delenv('PIXABAY_API_KEY',raising=False); monkeypatch.delenv('UNSPLASH_ACCESS_KEY',raising=False)
    m=AssetManager('prompt-to-video', tmp_path/'story.json', tmp_path/'assets', tmp_path/'out', tmp_path/'cache')
    data=m.generate(story()); assert all(Path(s['asset']).exists() for s in data['scenes']); assert all(s['assetProvider']=='local-assets' for s in data['scenes'])

def test_only_pexels_like_provider_runs(monkeypatch,tmp_path):
    p=FakeProvider(tmp_path/'assets','pexels'); m=AssetManager('prompt-to-video', tmp_path/'story.json', tmp_path/'assets', tmp_path/'out', tmp_path/'cache'); monkeypatch.setattr(m,'providers',lambda:[p])
    data=m.generate(story()); assert all(s['assetProvider']=='pexels' for s in data['scenes']); assert p.calls==3

def test_pexels_error_falls_to_pixabay(monkeypatch,tmp_path):
    pix=FakeProvider(tmp_path/'assets','pixabay'); m=AssetManager('prompt-to-video', tmp_path/'story.json', tmp_path/'assets', tmp_path/'out', tmp_path/'cache'); monkeypatch.setattr(m,'providers',lambda:[FailingProvider(m.assets_dir),pix])
    data=m.generate(story()); assert all(s['assetProvider']=='pixabay' for s in data['scenes'])

def test_all_online_errors_fall_back_local(monkeypatch,tmp_path):
    m=AssetManager('prompt-to-video', tmp_path/'story.json', tmp_path/'assets', tmp_path/'out', tmp_path/'cache'); monkeypatch.setattr(m,'providers',lambda:[FailingProvider(m.assets_dir)])
    data=m.generate(story()); assert all(s['assetProvider']=='local-assets' for s in data['scenes'])

def test_no_two_scenes_reuse_same_source_url(tmp_path):
    m=AssetManager('paper-sketch', tmp_path/'story.json', tmp_path/'assets', tmp_path/'out', tmp_path/'cache'); data=m.generate(story())
    urls=[s['assetSource'] for s in data['scenes']]; assert len(set(urls)) >= 2; assert urls[0] != urls[1]

def test_unknown_license_is_rejected(monkeypatch,tmp_path):
    good=FakeProvider(tmp_path/'assets','good'); m=AssetManager('prompt-to-video', tmp_path/'story.json', tmp_path/'assets', tmp_path/'out', tmp_path/'cache'); monkeypatch.setattr(m,'providers',lambda:[UnknownLicenseProvider(m.assets_dir),good])
    data=m.generate(story()); assert all(s['assetProvider']=='good' for s in data['scenes'])

def test_memory_cache_used_when_valid_and_not_duplicate(monkeypatch,tmp_path):
    p=FakeProvider(tmp_path/'assets','pexels'); m=AssetManager('prompt-to-video', tmp_path/'story.json', tmp_path/'assets', tmp_path/'out', tmp_path/'cache'); monkeypatch.setattr(m,'providers',lambda:[p])
    same={'template':'prompt-to-video','scenes':[{'id':1,'duration':4,'headline':'Một cảnh','narration':'Cùng nội dung'},{'id':2,'duration':4,'headline':'Một cảnh','narration':'Cùng nội dung'}]}
    m.generate(same); assert p.calls==2

def test_quality_score_written_to_manifest(tmp_path):
    m=AssetManager('stick-figure', tmp_path/'story.json', tmp_path/'assets', tmp_path/'out', tmp_path/'cache'); m.generate(story())
    manifest=json.loads((tmp_path/'out/asset-manifest.json').read_text(encoding='utf-8'))
    assert all('qualityScore' in item and isinstance(item['qualityScore'], int) for item in manifest)

def test_generate_assets_updates_story_file(tmp_path, monkeypatch):
    p=tmp_path/'story.json'; p.write_text(json.dumps(story(),ensure_ascii=False),encoding='utf-8'); monkeypatch.chdir(tmp_path)
    generate_assets(p,'paper-cut-documentary'); data=json.loads(p.read_text(encoding='utf-8'))
    assert data['scenes'][0]['asset']; assert data['scenes'][0]['qualityScore'] >= 0; assert (tmp_path/'output/credits.txt').exists()

def test_download_cache_reused_without_redownload(monkeypatch,tmp_path):
    from scripts.asset_providers import base
    calls={'count':0}
    class FakeResponse:
        headers={'Content-Type':'image/svg+xml'}
        def __enter__(self): return self
        def __exit__(self,*args): return False
        def read(self): return b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 900">' + b' ' * 800 + b'</svg>'
    def fake_urlopen(*args, **kwargs):
        calls['count'] += 1
        if calls['count'] > 1: raise AssertionError('download should use cache')
        return FakeResponse()
    monkeypatch.setattr(base.urllib.request, 'urlopen', fake_urlopen)
    cache=tmp_path/'cache/image.svg'; first=tmp_path/'first.svg'; second=tmp_path/'second.svg'
    base.download('https://example.test/a.svg', first, cache_path=cache)
    base.download('https://example.test/a.svg', second, cache_path=cache)
    assert calls['count'] == 1 and first.exists() and second.exists()
