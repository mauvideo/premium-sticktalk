from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .base import AssetResult, download, is_valid_mime, safe_name
from .openverse import OpenverseProvider
from .pexels import PexelsProvider
from .pixabay import PixabayProvider
from .unsplash import UnsplashProvider
from .local_assets import LocalAssetsProvider
from .wikimedia import WikimediaProvider
from scripts.entity_visual_planner import plan_entities

VOX_TEMPLATE = 'vox-paper-collage'
MIN_TOPIC_PHOTOS = 3
MAX_TOPIC_PHOTOS = 5


def keyword(scene: dict) -> dict:
    entity_plan = scene.get('entityVisualPlan', {})
    queries = entity_plan.get('searchQueries') or []
    subject = entity_plan.get('mainSubject') or 'documentary subject'
    return {
        'primary': queries[0] if queries else f'"{subject}"',
        'secondary': queries[1:],
        'asset_type': 'photo',
        'style': 'editorial documentary paper collage',
        'emotion': 'documentary',
        'subject': subject,
        'subject_type': entity_plan.get('mainSubjectType', 'concept'),
        'identity_required': bool(entity_plan.get('identityRequired')),
        'event': entity_plan.get('event', ''),
        'setting': entity_plan.get('location', '') or 'documentary context',
        'template': VOX_TEMPLATE,
        'size': '9:16',
    }


class AssetManager:
    def __init__(self, story_path='assets/story.json', assets_dir='assets/generated-assets', output_dir='output', cache_dir='assets/.asset-cache'):
        self.template = VOX_TEMPLATE
        self.story_path = Path(story_path)
        self.assets_dir = Path(assets_dir)
        self.output_dir = Path(output_dir)
        self.cache_dir = Path(cache_dir)
        self.used: set[str] = set()
        self.memory_cache: dict = {}
        self.research: dict = {}
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def providers(self, query: dict):
        if query.get('identity_required'):
            return [
                WikimediaProvider(self.assets_dir, self.cache_dir),
                OpenverseProvider(self.assets_dir, self.cache_dir),
            ]
        return [
            WikimediaProvider(self.assets_dir, self.cache_dir),
            OpenverseProvider(self.assets_dir, self.cache_dir),
            PexelsProvider(self.assets_dir, self.cache_dir),
            PixabayProvider(self.assets_dir, self.cache_dir),
            UnsplashProvider(self.assets_dir, self.cache_dir),
        ]

    def valid(self, result) -> bool:
        return bool(
            result
            and Path(result.file).exists()
            and Path(result.file).stat().st_size > 100
            and is_valid_mime(result.mime_type)
            and result.provider
            and result.qualityScore >= 0
        )

    def lead_image_fallback(self, query: dict, scene_index: int):
        url = str(self.research.get('leadImageUrl') or '').strip()
        if not url:
            return None
        suffix = '.png' if '.png' in url.lower() else '.jpg'
        subject = query.get('subject') or self.research.get('canonicalTitle') or 'subject'
        path = self.assets_dir / f"scene-{scene_index:02d}-topic-{safe_name(subject)}{suffix}"
        cache = self.cache_dir / f"topic-lead-{safe_name(subject)}{suffix}"
        _, mime, _ = download(
            url,
            path,
            headers={'User-Agent': 'premium-sticktalk/6.0 (topic-image-fallback)'},
            cache_path=cache,
        )
        return AssetResult(
            scene=scene_index,
            file=str(path),
            asset_type='photo',
            provider='wikipedia-topic-image',
            source_url=str(self.research.get('sourceUrl') or url),
            author='Source page contributor',
            author_url='',
            license='unverified-source',
            license_url='',
            search_query=f'{subject} topic lead image',
            downloaded_at=datetime.now(timezone.utc).isoformat(),
            width=0,
            height=0,
            mime_type=mime,
            qualityScore=80,
            asset_id=f'topic-lead-{safe_name(subject)}',
        )

    @staticmethod
    def query_variants(query: dict) -> list[str]:
        variants = [query.get('primary'), *(query.get('secondary') or [])]
        event = str(query.get('event') or '').strip()
        setting = str(query.get('setting') or '').strip()
        subject = str(query.get('subject') or '').strip()
        if subject and event:
            variants.append(f'{subject} {event[:110]}')
        if subject and setting and setting != 'documentary context':
            variants.append(f'{subject} {setting}')
        cleaned: list[str] = []
        for value in variants:
            value = str(value or '').replace('"', ' ').strip()
            value = ' '.join(value.split())
            if value and value not in cleaned:
                cleaned.append(value)
        return cleaned

    def get(self, query: dict, scene_index: int, allow_local: bool = True):
        for search_text in self.query_variants(query):
            current_query = dict(query)
            current_query['primary'] = search_text
            cache_key = (search_text, current_query['size'])
            cached = self.memory_cache.get(cache_key)
            if cached and cached.source_url not in self.used:
                return cached

            for provider in self.providers(current_query):
                try:
                    result = provider.search(current_query, scene_index, self.used)
                    if self.valid(result):
                        self.used.update({result.source_url, result.asset_id})
                        self.memory_cache[cache_key] = result
                        return result
                except Exception as error:  # noqa: BLE001
                    print(f'Asset provider {provider.name} skipped for {search_text!r}: {error}')

        if query.get('identity_required'):
            try:
                lead = self.lead_image_fallback(query, scene_index)
                if self.valid(lead):
                    self.used.update({lead.source_url, lead.asset_id})
                    return lead
            except Exception as error:  # noqa: BLE001
                print(f'Topic lead image fallback skipped: {error}')

        if not allow_local:
            return None
        fallback = LocalAssetsProvider(self.assets_dir, self.cache_dir).search(query, scene_index, self.used)
        self.used.update({fallback.source_url, fallback.asset_id})
        return fallback

    @staticmethod
    def manifest_item(result, scene_index: int, role: str, subject: str, queries: list[str]):
        item = result.manifest()
        item['scene'] = scene_index
        item['role'] = role
        item['fallback'] = result.provider == 'local-assets'
        item['identityQuery'] = subject
        item['identityVerified'] = result.provider == 'wikimedia-commons'
        item['topicMatched'] = result.provider in {
            'wikimedia-commons', 'wikipedia-topic-image', 'openverse',
            'pexels', 'pixabay', 'unsplash',
        }
        item['searchQueries'] = queries
        item['cutoutStyle'] = 'white-outline-yellow-shadow'
        item['licenseCheckBypassed'] = result.license == 'unverified-source'
        return item

    def generate(self, story: dict):
        if not story.get('entityVisualPlan'):
            story = plan_entities(story)
        self.research = story.get('research') or {}
        scenes = story.get('scenes', [])
        manifest = []
        topic_gallery: list[str] = []
        canonical = str(self.research.get('canonicalTitle') or story.get('title') or '').strip()

        for scene_index, scene in enumerate(scenes, start=1):
            query = keyword(scene)
            result = self.get(query, scene_index)
            relative_path = str(Path(result.file).as_posix())
            scene['asset'] = relative_path
            scene['image'] = relative_path
            scene['assetType'] = result.asset_type
            scene['assetProvider'] = result.provider
            scene['assetAuthor'] = result.author
            scene['assetLicense'] = result.license
            scene['assetSource'] = result.source_url
            scene['searchQuery'] = result.search_query
            scene['qualityScore'] = result.qualityScore
            scene['identityVerified'] = result.provider == 'wikimedia-commons'
            scene['topicMatched'] = result.provider != 'local-assets'
            scene['cutoutStyle'] = 'white-outline-yellow-shadow'
            manifest.append(
                self.manifest_item(
                    result,
                    scene_index,
                    'main-subject' if query.get('identity_required') else 'context-evidence',
                    query['subject'],
                    self.query_variants(query),
                )
            )
            if result.provider != 'local-assets' and relative_path not in topic_gallery and len(topic_gallery) < MAX_TOPIC_PHOTOS:
                topic_gallery.append(relative_path)

            if len(topic_gallery) < MAX_TOPIC_PHOTOS:
                variants = [
                    f'{canonical} portrait',
                    f'{canonical} historical photo',
                    f'{canonical} {scene.get("timeMarker", "")}',
                    f'{canonical} {scene.get("location", "")}',
                    str(scene.get('event') or '')[:120],
                ]
                for variant in variants:
                    variant = ' '.join(str(variant or '').replace('"', ' ').split())
                    if not variant:
                        continue
                    extra_query = dict(query)
                    extra_query['primary'] = variant
                    extra_query['secondary'] = []
                    extra_query['identity_required'] = False
                    extra = self.get(extra_query, scene_index, allow_local=False)
                    if not extra:
                        continue
                    extra_path = str(Path(extra.file).as_posix())
                    if extra_path in topic_gallery:
                        continue
                    topic_gallery.append(extra_path)
                    scene.setdefault('assets', []).append(extra_path)
                    manifest.append(
                        self.manifest_item(extra, scene_index, 'supporting-photo', canonical, [variant])
                    )
                    if len(topic_gallery) >= MAX_TOPIC_PHOTOS:
                        break

        for index, scene in enumerate(scenes):
            main = scene.get('image')
            candidates = [path for path in topic_gallery if path != main]
            start = index % max(1, len(candidates)) if candidates else 0
            ordered = candidates[start:] + candidates[:start]
            scene['assets'] = list(
                dict.fromkeys([*(scene.get('assets') or []), *ordered[:2]])
            )[:2]

        story['assetProviderSystem'] = 'vox-topic-assets-gallery-v5-openverse'
        story['template'] = VOX_TEMPLATE
        story['topicSubjectImages'] = len(topic_gallery)
        story['topicImageGallery'] = topic_gallery
        story['topicImageMinimumMet'] = len(topic_gallery) >= MIN_TOPIC_PHOTOS
        self.story_path.write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding='utf-8')
        (self.output_dir / 'asset-manifest.json').write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8'
        )
        credits = ['Asset credits', '=============', '']
        for item in manifest:
            credits.append(
                f"Scene {item['scene']}: {item['provider']} — {item['author']} — "
                f"{item['license']} — {item['source_url']} — role={item['role']}"
            )
        (self.output_dir / 'credits.txt').write_text('\n'.join(credits) + '\n', encoding='utf-8')
        print(
            f'Đã chuẩn bị {len(topic_gallery)} ảnh trực tuyến bám sát chủ đề cho video '
            f'(Pexels key={bool(os.getenv("PEXELS_API_KEY"))}, '
            f'Pixabay key={bool(os.getenv("PIXABAY_API_KEY"))}).'
        )
        if len(topic_gallery) < MIN_TOPIC_PHOTOS:
            print(
                'CẢNH BÁO: chưa đủ 3 ảnh trực tuyến. Hãy kiểm tra PEXELS_API_KEY, '
                'PIXABAY_API_KEY hoặc phản hồi của Wikimedia/Openverse.'
            )
        return story


def generate_assets(story):
    path = Path('assets/story.json')
    if isinstance(story, (str, Path)):
        path = Path(story)
        data = json.loads(path.read_text(encoding='utf-8'))
    else:
        data = story
    return AssetManager(story_path=path).generate(data)


if __name__ == '__main__':
    story_path = Path(os.getenv('STORY_PATH', 'assets/story.json'))
    generate_assets(story_path)
