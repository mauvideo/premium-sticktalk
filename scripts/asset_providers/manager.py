from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .base import AssetResult, download, is_valid_mime, safe_name
from .pexels import PexelsProvider
from .pixabay import PixabayProvider
from .unsplash import UnsplashProvider
from .local_assets import LocalAssetsProvider
from .wikimedia import WikimediaProvider
from scripts.entity_visual_planner import plan_entities

VOX_TEMPLATE = 'vox-paper-collage'


def keyword(scene: dict) -> dict:
    entity_plan = scene.get('entityVisualPlan', {})
    queries = entity_plan.get('searchQueries') or []
    subject = entity_plan.get('mainSubject') or 'documentary subject'
    event = entity_plan.get('event', '')
    location = entity_plan.get('location', '')

    return {
        'primary': queries[0] if queries else f'"{subject}"',
        'secondary': queries[1:],
        'asset_type': 'photo',
        'style': 'editorial documentary paper collage',
        'emotion': 'documentary',
        'subject': subject,
        'subject_type': entity_plan.get('mainSubjectType', 'concept'),
        'identity_required': bool(entity_plan.get('identityRequired')),
        'event': event,
        'setting': location or 'documentary context',
        'template': VOX_TEMPLATE,
        'size': '9:16',
    }


class AssetManager:
    def __init__(
        self,
        story_path: str = 'assets/story.json',
        assets_dir: str = 'assets/generated-assets',
        output_dir: str = 'output',
        cache_dir: str = 'assets/.asset-cache',
    ):
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
        # Wikimedia is tried first, but one HTTP 429 must not kill the render.
        # Context scenes then continue through stock/archive providers.
        if query.get('identity_required'):
            return [WikimediaProvider(self.assets_dir, self.cache_dir)]
        return [
            WikimediaProvider(self.assets_dir, self.cache_dir),
            PexelsProvider(self.assets_dir, self.cache_dir),
            PixabayProvider(self.assets_dir, self.cache_dir),
            UnsplashProvider(self.assets_dir, self.cache_dir),
            LocalAssetsProvider(self.assets_dir, self.cache_dir),
        ]

    def valid(self, result) -> bool:
        # The user requested that unavailable/unclear licence metadata must not
        # stop rendering. Source and licence text are still recorded in the
        # manifest so the output can be reviewed later.
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
            headers={'User-Agent': 'premium-sticktalk/5.0 (topic-image-fallback)'},
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

    def get(self, query: dict, scene_index: int):
        cache_key = (query['primary'], query['size'])
        cached = self.memory_cache.get(cache_key)
        if cached and cached.source_url not in self.used:
            return cached

        # Avoid repeated API hammering: one request per provider per scene.
        for provider in self.providers(query):
            try:
                result = provider.search(query, scene_index, self.used)
                if self.valid(result):
                    self.used.update({result.source_url, result.asset_id})
                    self.memory_cache[cache_key] = result
                    return result
            except Exception as error:  # noqa: BLE001
                print(f'Asset provider {provider.name} skipped: {error}')

        # For a named subject, use the lead image attached to the resolved topic
        # page when Commons is rate limited. This keeps the visual on-topic.
        if query.get('identity_required'):
            try:
                lead = self.lead_image_fallback(query, scene_index)
                if self.valid(lead):
                    self.used.update({lead.source_url, lead.asset_id})
                    return lead
            except Exception as error:  # noqa: BLE001
                print(f'Topic lead image fallback skipped: {error}')

        fallback = LocalAssetsProvider(self.assets_dir, self.cache_dir).search(
            query, scene_index, self.used
        )
        self.used.update({fallback.source_url, fallback.asset_id})
        return fallback

    def generate(self, story: dict):
        if not story.get('entityVisualPlan'):
            story = plan_entities(story)

        self.research = story.get('research') or {}
        manifest = []
        topic_subject_images = 0

        for scene_index, scene in enumerate(story.get('scenes', []), start=1):
            query = keyword(scene)
            result = self.get(query, scene_index)
            relative_path = str(Path(result.file).as_posix())
            topic_matched = bool(
                query.get('identity_required')
                and result.provider in {'wikimedia-commons', 'wikipedia-topic-image'}
            )
            if topic_matched:
                topic_subject_images += 1

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
                'identityVerified': result.provider == 'wikimedia-commons',
                'topicMatched': topic_matched,
                'cutoutStyle': 'white-outline-yellow-shadow',
            })

            item = result.manifest()
            item['role'] = 'main-subject' if query.get('identity_required') else 'context-evidence'
            item['fallback'] = result.provider == 'local-assets'
            item['identityQuery'] = query['subject']
            item['identityVerified'] = result.provider == 'wikimedia-commons'
            item['topicMatched'] = topic_matched
            item['searchQueries'] = [query['primary'], *query['secondary']]
            item['cutoutStyle'] = 'white-outline-yellow-shadow'
            item['licenseCheckBypassed'] = result.license == 'unverified-source'
            if item['fallback']:
                item['fallbackReason'] = 'Không tải được ảnh trực tuyến; dùng minh họa cục bộ.'
            manifest.append(item)

        # Do not fail the entire 20-40 minute render because Commons returned
        # HTTP 429. The manifest shows whether a verified or topic-page image
        # was used, and the video can still be inspected.
        story['assetProviderSystem'] = 'vox-topic-assets-tolerant-v3'
        story['template'] = VOX_TEMPLATE
        story['topicSubjectImages'] = topic_subject_images
        self.story_path.write_text(
            json.dumps(story, ensure_ascii=False, indent=2), encoding='utf-8'
        )
        (self.output_dir / 'asset-manifest.json').write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8'
        )

        credits = ['Asset credits', '=============', '']
        for item in manifest:
            credits.append(
                f"Scene {item['scene']}: {item['provider']} — {item['author']} — "
                f"{item['license']} — {item['source_url']} — quality {item['qualityScore']}/100 — "
                f"topicMatched={item['topicMatched']} — identityVerified={item['identityVerified']}"
            )
        (self.output_dir / 'credits.txt').write_text(
            '\n'.join(credits) + '\n', encoding='utf-8'
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
