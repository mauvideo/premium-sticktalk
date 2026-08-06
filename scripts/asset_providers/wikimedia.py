"""Wikimedia Commons provider using the documented MediaWiki API."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from .base import AssetProvider, AssetResult, cache_key, download, safe_name
from .scoring import asset_quality_score

API = "https://commons.wikimedia.org/w/api.php"
FREE_LICENSES = ("public domain", "cc0", "cc by", "cc-by", "cc by-sa", "cc-by-sa", "gfdl")


class WikimediaProvider(AssetProvider):
    name = "wikimedia-commons"

    def search(self, query, scene_index, used):
        subject = str(query.get("subject") or "").strip()
        search = f'{subject} {query.get("event", "")}'.strip() or query["primary"]
        params = urllib.parse.urlencode({
            "action": "query", "generator": "search", "gsrsearch": search,
            "gsrnamespace": 6, "gsrlimit": 12, "prop": "imageinfo",
            "iiprop": "url|mime|size|extmetadata", "iiurlwidth": 1400,
            "format": "json", "origin": "*",
        })
        request = urllib.request.Request(f"{API}?{params}", headers={"User-Agent": "premium-sticktalk/2.0 (licensed-media-search)"})
        with urllib.request.urlopen(request, timeout=20) as response:
            pages = json.load(response).get("query", {}).get("pages", {}).values()
        subject_tokens = {x.casefold() for x in subject.split() if len(x) > 2}
        candidates = []
        for page in pages:
            info = (page.get("imageinfo") or [{}])[0]
            meta = info.get("extmetadata") or {}
            license_name = (meta.get("LicenseShortName") or {}).get("value", "")
            title = page.get("title", "")
            # A real person's result must match multiple name tokens.  Returning
            # no result is safer than silently substituting another person.
            title_tokens = {x.casefold() for x in title.replace("File:", "").replace("_", " ").split()}
            if len(subject_tokens) >= 2 and len(subject_tokens & title_tokens) < 2:
                continue
            if not any(mark in license_name.casefold() for mark in FREE_LICENSES):
                continue
            source = info.get("descriptionurl", "")
            if not source or source in used:
                continue
            author = re_text((meta.get("Artist") or {}).get("value", "")) or "Wikimedia Commons contributor"
            candidates.append((page, info, license_name, author))
        if not candidates:
            return None
        page, info, license_name, author = candidates[0]
        url = info.get("thumburl") or info["url"]
        suffix = ".png" if "png" in info.get("mime", "") else ".jpg"
        path = self.out_dir / f"scene-{scene_index:02d}-commons-{safe_name(subject)}{suffix}"
        cache = self.cache_dir / f"{cache_key(self.name, search, query.get('template', ''))}{suffix}"
        _, mime, _ = download(url, path, cache_path=cache)
        candidate = {"width": info.get("thumbwidth", info.get("width", 0)), "height": info.get("thumbheight", info.get("height", 0)), "clear_subject": True}
        score = asset_quality_score(candidate, query, query.get("template", ""), False)
        return AssetResult(scene_index, str(path), "photo", self.name, info["descriptionurl"], author, "", license_name,
                           (info.get("extmetadata", {}).get("LicenseUrl") or {}).get("value", info["descriptionurl"]),
                           search, datetime.now(timezone.utc).isoformat(), candidate["width"], candidate["height"], mime, score, str(page.get("pageid", "")))


def re_text(value: str) -> str:
    """Remove the small amount of HTML commonly present in Artist metadata."""
    import re
    return " ".join(re.sub(r"<[^>]+>", " ", value).split())
