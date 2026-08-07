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
from .local_assets import LocalAssetsProvider
from .wikimedia import WikimediaProvider
from scripts.entity_visual_planner import plan_entities

VOX_TEMPLATE = 'vox-paper-collage'
MIN_TOPIC_PHOTOS = 3
MAX_TOPIC_PHOTOS = 5
VERIFIED_IDENTITY_PROVIDERS = {'wikimedia-commons', 'wikipedia-topic-image'}
ONLINE_PROVIDERS = {
    'wikimedia-commons', 'wikipedia-topic-image', 'openverse',
    'pexels', 'pixabay', 'unsplash',
}


def keyword(scene: dict) -> dict:
    entity_plan = scene.get('entityVisualPlan', {})
    queries = entity_plan.get('searchQueries') or []
    subject = entity_plan.get('mainSubject') or 'documentary subject'
    return {
        'primary': queries[0] if queries else subject,
        'secondary': queries[1:],
        'asset_type': 'photo',
        'style': 'editorial documentary paper collage',
        'emotion': 'documentary',
        'subject': subject,
        'subject_type': entity_plan.get('mainSubjectType', 'concept'),
        'identity_required': bool(entity_plan.get('identityRequired')),
        'event': entity_plan.get('event', ''),
        'setting': entity_plan.get('location', '') or 'documentary context',
        'time_period': entity_plan.get('timePeriod', ''),
        'visual_evidence': entity_plan.get('visualEvidence') or [],
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
        subject_type = str(query.get('subject_type') or '').casefold()
        if query.get('identity_required') or subject_type == 'person':
            # Never use random stock people as the named person.
            return [WikimediaProvider(self.assets_dir, self.cache_dir)]
        if subject_type in {'event', 'place', 'company', 'organization'}:
            return [
                WikimediaProvider(self.assets_dir, self.cache_dir),
                OpenverseProvider(self.assets_dir, self.cache_dir),
                PexelsProvider(self.assets_dir, self.cache_dir),
                PixabayProvider(self.assets_dir, self.cache_dir),
                UnsplashProvider(self.assets_dir, self.cache_dir),
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
            headers={'User-Agent': 'premium-sticktalk/7.0 (verified-topic-image)'},
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
            search_query=f'{subject} verified topic lead image',
            downloaded_at=datetime.now(timezone.utc).isoformat(),
            width=0,
            height=0,
            mime_type=mime,
            qualityScore=95,
            asset_id=f'topic-lead-{safe_name(subject)}',
        )

    @staticmethod
    def _clean_query(value: str) -> str:
        value = str(value or '').replace('"', ' ')
        value = re.sub(r'\s+', ' ', value).strip(' ,;:-')
        return value[:180]

    @classmethod
    def query_variants(cls, query: dict) -> list[str]:
        subject = cls._clean_query(query.get('subject', ''))
        subject_type = cls._clean_query(query.get('subject_type', '')).casefold()
        event = cls._clean_query(query.get('event', ''))
        setting = cls._clean_query(query.get('setting', ''))
        period = cls._clean_query(query.get('time_period', ''))
        evidence = [cls._clean_query(item) for item in query.get('visual_evidence', [])]

        variants = [query.get('primary'), *(query.get('secondary') or [])]
        if subject:
            variants.append(subject)
            if subject_type == 'person':
                variants.extend([
                    f'{subject} portrait',
                    f'{subject} archival photograph',
                    f'{subject} historical photograph',
                    f'{subject} speaking',
                    f'{subject} official photograph',
                ])
            elif subject_type in {'company', 'organization'}:
                variants.extend([
                    f'{subject} headquarters', f'{subject} founder',
                    f'{subject} products', f'{subject} historical photo',
                ])
            elif subject_type == 'event':
                variants.extend([
                    f'{subject} historical photo', f'{subject} map',
                    f'{subject} newspaper', f'{subject} aftermath',
                ])
            elif subject_type == 'place':
                variants.extend([
                    f'{subject} landmark', f'{subject} aerial view',
                    f'{subject} old photograph', f'{subject} map',
                ])
            else:
                variants.extend([
                    f'{subject} documentary photo', f'{subject} illustration',
                    f'{subject} diagram',
                ])
        if subject and period:
            variants.append(f'{subject} {period}')
        if subject and setting and setting != 'documentary context':
            variants.append(f'{subject} {setting}')
        if subject and event:
            variants.append(f'{subject} {" ".join(event.split()[:14])}')
        variants.extend(evidence)

        cleaned: list[str] = []
        seen: set[str] = set()
        for value in variants:
            value = cls._clean_query(value)
            folded = value.casefold()
            if value and folded not in seen:
                cleaned.append(value)
                seen.add(folded)
        return cleaned[:18]

    def result_matches_query(self, result, query: dict) -> bool:
        if not self.valid(result):
            return False
        subject_type = str(query.get('subject_type') or '').casefold()
        if query.get('identity_required') or subject_type == 'person':
            return result.provider in VERIFIED_IDENTITY_PROVIDERS
        return result.provider in ONLINE_PROVIDERS

    def get(self, query: dict, scene_index: int, allow_local: bool = True):
        for search_text in self.query_variants(query):
            current_query = dict(query)
            current_query['primary'] = search_text
            cache_key = (search_text.casefold(), current_query['size'], str(current_query.get('subject_type')))
            cached = self.memory_cache.get(cache_key)
            if cached and cached.source_url not in self.used and self.result_matches_query(cached, current_query):
                return cached
            for provider in self.providers(current_query):
                try:
                    result = provider.search(current_query, scene_index, self.used)
                    if self.result_matches_query(result, current_query):
                        self.used.update({result.source_url, result.asset_id})
                        self.memory_cache[cache_key] = result
                        return result
                except Exception as error:  # noqa: BLE001
                    print(f'Asset provider {provider.name} skipped for {search_text!r}: {error}')

        if query.get('identity_required') or str(query.get('subject_type') or '').casefold() == 'person':
            try:
                lead = self.lead_image_fallback(query, scene_index)
                if self.result_matches_query(lead, {**query, 'identity_required': True}):
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
        item['identityVerified'] = result.provider in VERIFIED_IDENTITY_PROVIDERS
        item['topicMatched'] = result.provider in ONLINE_PROVIDERS
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
        entity_type = str(self.research.get('entityType') or 'topic').strip().casefold()

        for scene_index, scene in enumerate(scenes, start=1):
            query = keyword(scene)
            # The resolved topic type is authoritative. This prevents a person
            # video from accidentally treating later scenes as generic stock.
            if entity_type == 'person':
                query['subject_type'] = 'person'
                query['subject'] = canonical or query['subject']
                query['identity_required'] = True
            result = self.get(query, scene_index)
            relative_path = str(Path(result.file).as_posix())
            verified_identity = result.provider in VERIFIED_IDENTITY_PROVIDERS
            scene.update({
                'asset': relative_path,
                'image': relative_path,
                'assetType': result.asset_type,
                'assetProvider': result.provider,
                'assetAuthor': result.author,
                'assetLicense': result.license,
                'assetSource': result.source_url,
                'searchQuery': result.search_query,
                'qualityScore': result.qualityScore,
                'identityVerified': verified_identity,
                'topicMatched': result.provider in ONLINE_PROVIDERS,
                'cutoutStyle': 'white-outline-yellow-shadow',
            })
            manifest.append(self.manifest_item(
                result, scene_index,
                'main-subject' if query.get('identity_required') else 'context-evidence',
                query['subject'], self.query_variants(query),
            ))
            if result.provider in ONLINE_PROVIDERS and relative_path not in topic_gallery and len(topic_gallery) < MAX_TOPIC_PHOTOS:
                topic_gallery.append(relative_path)

            # Supporting photos must be scene-specific. For a person video,
            # continue using verified images of that person instead of generic
            # stock people. Other topic types may use contextual stock imagery.
            if len(topic_gallery) < MAX_TOPIC_PHOTOS:
                support_query = dict(query)
                support_query['secondary'] = []
                if entity_type == 'person':
                    support_query['subject_type'] = 'person'
                    support_query['identity_required'] = True
                    support_query['subject'] = canonical
                else:
                    support_query['identity_required'] = False
                    support_query['subject_type'] = entity_type
                for variant in self.query_variants(support_query):
                    support_query['primary'] = variant
                    extra = self.get(support_query, scene_index, allow_local=False)
                    if not extra:
                        continue
                    extra_path = str(Path(extra.file).as_posix())
                    if extra_path in topic_gallery or extra_path == relative_path:
                        continue
                    topic_gallery.append(extra_path)
                    scene.setdefault('assets', []).append(extra_path)
                    manifest.append(self.manifest_item(
                        extra, scene_index, 'supporting-photo', canonical, [variant]
                    ))
                    break

        for index, scene in enumerate(scenes):
            main = scene.get('image')
            candidates = [path for path in topic_gallery if path != main]
            start = index % max(1, len(candidates)) if candidates else 0
            ordered = candidates[start:] + candidates[:start]
            scene['assets'] = list(dict.fromkeys([*(scene.get('assets') or []), *ordered[:2]]))[:2]

        story['assetProviderSystem'] = 'vox-verified-scene-assets-v7'
        story['template'] = VOX_TEMPLATE
        story['topicSubjectImages'] = len(topic_gallery)
        story['topicImageGallery'] = topic_gallery
        story['topicImageMinimumMet'] = len(topic_gallery) >= MIN_TOPIC_PHOTOS
        story['identitySafetyRule'] = 'named-person-images-only-from-verified-topic-sources'
        self.story_path.write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding='utf-8')
        (self.output_dir / 'asset-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        credits = ['Asset credits', '=============', '']
        for item in manifest:
            credits.append(
                f"Scene {item['scene']}: {item['provider']} — {item['author']} — "
                f"{item['license']} — {item['source_url']} — role={item['role']} — "
                f"identityVerified={item['identityVerified']}"
            )
        (self.output_dir / 'credits.txt').write_text('\n'.join(credits) + '\n', encoding='utf-8')
        print(
            f'Đã chuẩn bị {len(topic_gallery)} ảnh bám sát chủ đề; '
            f'entityType={entity_type}; Pexels key={bool(os.getenv("PEXELS_API_KEY"))}; '
            f'Pixabay key={bool(os.getenv("PIXABAY_API_KEY"))}.'
        )
        if entity_type == 'person' and any(
            not item.get('identityVerified') for item in manifest if item.get('role') == 'main-subject'
        ):
            raise RuntimeError('Phát hiện ảnh nhân vật chính chưa được xác minh; dừng trước khi render sai người.')
        if len(topic_gallery) < MIN_TOPIC_PHOTOS:
            print('CẢNH BÁO: chưa đủ 3 ảnh trực tuyến; video vẫn dùng ảnh chủ đề đã xác minh và không dùng người lạ.')
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
