# Free asset providers

Premium StickTalk uses the `scripts.asset_providers` package to fetch or create non-AI visual assets. The workflow and `make_video.sh` call the shared entrypoint `generate_assets(story, template)` via `python3 -m scripts.asset_providers.manager`; provider lookup logic is not embedded in workflow YAML.

## Sources and licenses

- Pexels API: real photos, Pexels License, optional API key `PEXELS_API_KEY`.
- Pixabay API: real photos, Pixabay Content License, optional API key `PIXABAY_API_KEY`.
- Unsplash API: real photos, Unsplash License, optional API key `UNSPLASH_ACCESS_KEY`.
- OpenMoji, unDraw, Openclipart, SVG Repo and Wikimedia-compatible modules are present for SVG/icon expansion. Any online extension must reject unknown, missing or non-commercial licenses before use.
- Local fallback assets: self-created SVG assets stored under `assets/free-assets/` and documented as project-local fallback assets.

No Google Images, Pollinations, Hugging Face Image, OpenAI Image, Gemini Image, or unclear-license scraping is used.

## Local fallback asset library

The repository includes reusable SVG components in:

- `assets/free-assets/stick-figure/`: stick figures with multiple poses.
- `assets/free-assets/hand-drawn/`: doodle arrows and line-art scenes.
- `assets/free-assets/paper-cut/`: collage cards, torn paper, tape and arrows.
- `assets/free-assets/business/`: desk/work objects.
- `assets/free-assets/nature/`: tree, mountain, sun and path scenes.
- `assets/free-assets/textures/`: paper grain texture.
- `assets/free-assets/icons/`: goal and idea icons.

These are self-created SVG code assets and are used only as fallbacks or no-key assets; they are not old circular placeholders.

## Fallback order

- `prompt-to-video`, `business-motivation`, `smooth-transitions`: Pexels if key exists → Pixabay if key exists → Unsplash if key exists → no-key SVG/local assets.
- `kinetic-captions`: Pexels if key exists → Pixabay if key exists → Unsplash if key exists → local dark/minimal texture SVG.
- `paper-cut-documentary`: Pexels if key exists → Pixabay if key exists → Unsplash if key exists → local paper collage SVG.
- `stick-figure`: SVG/icon style → local stick-figure SVG if online SVG is unavailable.
- `paper-sketch`: doodle/line-art style → local line-art SVG if online SVG is unavailable.

Each provider is retried at most two times. Missing API keys never fail the workflow, and failure of one source never fails the video.

## Cache and duplicate handling

Downloaded assets are cached by provider, search query, template and requested size. A valid cached image is reused on later runs instead of downloading again. HTML responses, unknown MIME types, tiny files and failed downloads are not cached. During one video, `used_asset_ids` and source URLs are tracked so two scenes do not use the same online image unless no alternative exists.

## Quality score

Every candidate receives a rule-based `qualityScore` from 0 to 100 based on keyword relevance, proximity to 9:16, resolution, clear subject metadata, low logo/text risk, duplicate status, template fit and valid license metadata. The highest-scoring valid candidate is selected instead of blindly taking the first result. `qualityScore` is written to both `assets/story.json` and `output/asset-manifest.json`.

## Attribution

Every selected asset is written to `output/asset-manifest.json` and `output/credits.txt` with scene number, file, asset type, provider, source URL, author, author page, license, license URL, search query, download date, size, MIME type and quality score. If a source requires attribution, include the generated credits with the published video.

## API keys

Add any of these optional GitHub Secrets: `PEXELS_API_KEY`, `PIXABAY_API_KEY`, `UNSPLASH_ACCESS_KEY`. The system works with one key, multiple keys, or no keys by falling back to no-key/local providers. Keys are read only from environment variables and are never logged.

## Adding a provider

Create a module in `scripts/asset_providers/` that subclasses `AssetProvider`, returns `AssetResult`, checks the provider license before use, validates downloaded MIME/size, avoids already-used source URLs, participates in cache by provider/query/template/size, assigns `qualityScore`, and add it to `AssetManager.providers()` in the appropriate template order.
