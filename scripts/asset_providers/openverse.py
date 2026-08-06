from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from .base import AssetProvider, AssetResult, cache_key, download, safe_name
from .scoring import asset_quality_score


class OpenverseProvider(AssetProvider):
    """Search Creative Commons/public-domain images without requiring an API key."""

    name = "openverse"

    def search(self, query: dict, scene_index: int, used: set[str]):
        search_text = str(query.get("primary") or "").replace('"', " ").strip()
        if not search_text:
            return None

        params = urllib.parse.urlencode(
            {
                "q": search_text,
                "page_size": 20,
                "mature": "false",
            }
        )
        request = urllib.request.Request(
            f"https://api.openverse.org/v1/images/?{params}",
            headers={"User-Agent": "premium-sticktalk/6.0 (openverse-topic-assets)"},
        )
        with urllib.request.urlopen(request, timeout=25) as response:
            payload = json.load(response)

        candidates: list[tuple[dict, str]] = []
        for item in payload.get("results", []):
            asset_id = str(item.get("id") or item.get("foreign_landing_url") or "")
            source_url = str(item.get("foreign_landing_url") or item.get("detail_url") or "")
            image_url = str(item.get("url") or item.get("thumbnail") or "")
            if not asset_id or not image_url or asset_id in used or source_url in used:
                continue

            license_code = str(item.get("license") or "cc").upper()
            license_version = str(item.get("license_version") or "").strip()
            license_name = f"CC {license_code}{(' ' + license_version) if license_version else ''}".strip()
            license_url = str(item.get("license_url") or source_url)
            candidate = {
                "asset_id": asset_id,
                "source_url": source_url,
                "asset_type": "photo",
                "width": int(item.get("width") or 0),
                "height": int(item.get("height") or 0),
                "author": str(item.get("creator") or "Openverse contributor"),
                "author_url": str(item.get("creator_url") or ""),
                "license": license_name,
                "license_url": license_url,
                "alt": " ".join(
                    str(value or "")
                    for value in (item.get("title"), item.get("tags"), item.get("source"))
                ),
                "clear_subject": True,
            }
            candidate["qualityScore"] = asset_quality_score(
                candidate, query, query.get("template", "")
            )
            candidates.append((candidate, image_url))

        for candidate, image_url in sorted(
            candidates, key=lambda pair: pair[0]["qualityScore"], reverse=True
        ):
            suffix = ".png" if ".png" in image_url.lower() else ".jpg"
            path = self.out_dir / (
                f"scene-{scene_index:02d}-openverse-{safe_name(search_text)}{suffix}"
            )
            cache = self.cache_dir / (
                cache_key(self.name, search_text, query.get("template", ""), "portrait")
                + suffix
            )
            try:
                _, mime_type, _ = download(
                    image_url,
                    path,
                    headers={"User-Agent": "premium-sticktalk/6.0"},
                    cache_path=cache,
                )
            except Exception:
                continue
            used.update({candidate["asset_id"], candidate["source_url"]})
            return AssetResult(
                scene_index,
                str(path),
                "photo",
                self.name,
                candidate["source_url"],
                candidate["author"],
                candidate["author_url"],
                candidate["license"],
                candidate["license_url"],
                search_text,
                datetime.now(timezone.utc).isoformat(),
                candidate["width"],
                candidate["height"],
                mime_type,
                candidate["qualityScore"],
                candidate["asset_id"],
            )
        return None
