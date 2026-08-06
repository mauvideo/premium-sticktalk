from __future__ import annotations

import json
import os
from pathlib import Path

from .base import is_valid_license, is_valid_mime
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
        'primary': queries[0] if queries else f'"{subject}" Wikimedia Commons',
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
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def providers(self, query: dict):
        # A named person's hero image must come from Wikimedia metadata that
        # matches the person's name. Stock-photo providers may not substitute
        # another face. Context scenes may use broader archival/stock imagery.
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
        return bool(
            result
            and Path(result.file).exists()
            and Path(result.file).stat().st_size > 100
            and is_valid_mime(result.mime_type)
            and is_valid_license(result.license, result.license_url)
            and result.provider
            and result.qualityScore >= 0
        )

    def get(self, query: dict, scene_index: int):
        cache_key = (query['primary'], query['size'])
        cached = self.memory_cache.get(cache_key)
        if cached and cached.source_url not in self.used:
            return cached

        for provider in self.providers(query):
            for _ in range(2):
                try:
                    result = provider.search(query, scene_index, self.used)
                    if self.valid(result):
                        self.used.update({result.source_url, result.asset_id})
                        self.memory_cache[cache_key] = result
                        return result
                except Exception as error:  # noqa: BLE001
                    print(f'Asset provider {provider.name} skipped: {error}')

        if query.get('identity_required'):
            raise RuntimeError(
                f"Không tìm được ảnh xác minh đúng nhân vật '{query['subject']}' "
                "trên Wikimedia Commons. Dừng render để không dùng nhầm người."
            )

        fallback = LocalAssetsProvider(self.assets_dir, self.cache_dir).search(
            query, scene_index, self.used
        )
        self.used.update({fallback.source_url, fallback.asset_id})
        return fallback

    def generate(self, story: dict):
        if not story.get('entityVisualPlan'):
            story = plan_entities(story)

        manifest = []
        verified_subject_images = 0
        for scene_index, scene in enumerate(story.get('scenes', []), start=1):
            query = keyword(scene)
            result = self.get(query, scene_index)
            relative_path = str(Path(result.file).as_posix())
            identity_verified = bool(
                query.get('identity_required')
                and result.provider == 'wikimedia-commons'
            )
            if identity_verified:
                verified_subject_images += 1

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
                'identityVerified': identity_verified,
                'cutoutStyle': 'white-outline-yellow-shadow',
            })

            item = result.manifest()
            item['role'] = 'main-subject' if query.get('identity_required') else 'context-evidence'
            item['fallback'] = result.provider == 'local-assets'
            item['identityQuery'] = query['subject']
            item['identityVerified'] = identity_verified
            item['searchQueries'] = [query['primary'], *query['secondary']]
            item['cutoutStyle'] = 'white-outline-yellow-shadow'
            if item['fallback']:
                item['fallbackReason'] = (
                    'Không tìm thấy asset bối cảnh đúng chủ đề có giấy phép rõ ràng; '
                    'đã dùng minh họa trung tính và không thay bằng người khác.'
                )
            manifest.append(item)

        if story.get('entityVisualPlan', {}).get('mainEntityType') == 'person' and verified_subject_images < 1:
            raise RuntimeError('Video về nhân vật phải có ít nhất một ảnh đúng danh tính đã xác minh.')

        story['assetProviderSystem'] = 'vox-free-licensed-assets-v2'
        story['template'] = VOX_TEMPLATE
        story['verifiedSubjectImages'] = verified_subject_images
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
                f"identityVerified={item['identityVerified']}"
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
