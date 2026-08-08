#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"; cd "$ROOT"
IDEA="${VIDEO_IDEA:-}"; DURATION="${VIDEO_DURATION:-45}"; VOICE="${VIENEU_VOICE:-default}"; CUSTOM_VOICE_ID="${VIENEU_CUSTOM_VOICE_ID:-}"; ASPECT="${VIDEO_ASPECT_RATIO:-9:16}"
require_value(){ [[ $# -ge 2 && -n "$2" && "$2" != --* ]] || { echo "Thiếu giá trị cho $1" >&2; exit 2; }; }
while (($#)); do case "$1" in
  --idea|--y-tuong|--ý-tưởng) require_value "$@"; IDEA="$2"; shift 2;;
  --duration|--thoi-luong|--thời-lượng) require_value "$@"; DURATION="$2"; shift 2;;
  --voice|--giong-doc|--giọng-đọc) require_value "$@"; VOICE="$2"; shift 2;;
  --custom-voice-id|--ma-giong) require_value "$@"; CUSTOM_VOICE_ID="$2"; shift 2;;
  --aspect-ratio|--ty-le) require_value "$@"; ASPECT="$2"; shift 2;;
  *) echo "Tham số không hợp lệ: $1" >&2; exit 2;; esac; done
[[ -n "$IDEA" ]] || { echo 'Thiếu chủ đề video' >&2; exit 2; }
[[ "$DURATION" =~ ^(30|45|60|90)$ ]] || { echo "Thời lượng không hợp lệ: $DURATION" >&2; exit 2; }
[[ "$ASPECT" =~ ^(9:16|16:9)$ ]] || { echo "Tỷ lệ không hợp lệ: $ASPECT" >&2; exit 2; }
export VIDEO_PROJECT="documentary" VIDEO_TEMPLATE="vox-paper-collage" VIDEO_STYLE="vox_giay_cat" VIDEO_MOTION_LEVEL="high" VIDEO_SCRIPT_MODE="ai_research_grounded" VIDEO_CONTENT_FORMAT="narration" VIDEO_TONE="trung_tính" VIENEU_EMOTION="Kể chuyện"
printf '%s\n' "=== PREMIUM STICKTALK COMMERCIAL PIPELINE ===" "Chủ đề: $IDEA" "Thời lượng: $DURATION giây" "Khung hình: $ASPECT" "Giọng VieNeu: $VOICE" "Quy trình: Gemini text → facts → kịch bản → ảnh cục bộ → VieNeu → Remotion dựng hình → FFmpeg ghép tiếng"
mkdir -p assets output remotion/public/assets

PRIMARY_MODEL="${GEMINI_MODEL:-gemini-3.6-flash}"
FALLBACK_MODEL="${GEMINI_FALLBACK_MODEL:-gemini-3.5-flash}"
export GEMINI_MODEL="$PRIMARY_MODEL" GEMINI_FALLBACK_MODEL="$FALLBACK_MODEL"
python3 scripts/commercial_ai_pipeline_gemini_stable.py --topic "$IDEA" --duration "$DURATION" --voice "$VOICE"

python3 - <<PY
import json
p='assets/story.json'
with open(p,encoding='utf-8') as h:s=json.load(h)
s['aspectRatio']='$ASPECT'
with open(p,'w',encoding='utf-8') as h:json.dump(s,h,ensure_ascii=False,indent=2)
PY

python3 -m scripts.entity_visual_planner --story assets/story.json --topic "$IDEA"
python3 -m scripts.asset_providers.manager

rm -rf remotion/public/assets/generated-assets
mkdir -p remotion/public/assets/generated-assets
cp -R assets/generated-assets/. remotion/public/assets/generated-assets/
python3 - <<'PY'
import json, pathlib, re, sys
story_path=pathlib.Path('assets/story.json')
public=pathlib.Path('remotion/public')
story=json.loads(story_path.read_text(encoding='utf-8'))
remote=re.compile(r'^https?://',re.I)
missing=[]; remote_refs=[]
def check(value,label):
    if not value:return
    value=str(value)
    if remote.match(value): remote_refs.append((label,value)); return
    rel=value.replace('\\','/').lstrip('/')
    if rel.startswith('assets/'): target=public/rel
    elif rel.startswith('generated-assets/'): target=public/'assets'/rel
    else:return
    if not target.exists() or target.stat().st_size < 1: missing.append((label,value))
for i,scene in enumerate(story.get('scenes') or [],1):
    check(scene.get('image'),f'phân cảnh {i} ảnh chính')
    check(scene.get('asset'),f'phân cảnh {i} tài nguyên chính')
    for j,v in enumerate(scene.get('assets') or [],1):check(v,f'phân cảnh {i} ảnh phụ {j}')
if remote_refs:
    print('LỖI: vẫn còn đường dẫn ảnh mạng trong dữ liệu dựng:')
    for x in remote_refs:print(' -',*x)
    sys.exit(20)
if missing:
    print('LỖI: ảnh cục bộ chưa được sao chép đầy đủ trước khi dựng:')
    for x in missing:print(' -',*x)
    sys.exit(21)
print('KIỂM TRA ẢNH OK: toàn bộ ảnh dùng khi dựng đã nằm cục bộ trên máy chủ tạm.')
PY

python3 scripts/generate_tts.py --voice "$VOICE" --custom-voice-id "$CUSTOM_VOICE_ID" --emotion "Kể chuyện"
cp assets/narration.mp3 remotion/public/assets/narration.mp3
python3 - <<'PY'
import json
p='assets/story.json'
with open(p,encoding='utf-8') as h:s=json.load(h)
# Render hình riêng, không để Remotion/FFmpeg giữ luồng audio ở bước encode cuối.
s.update({'audio':'assets/narration.mp3','renderAudio':False,'project':'documentary','template':'vox-paper-collage','style':'vox_giay_cat','motionLevel':'high','contentMode':'commercial-ai-grounded','assetMode':'local-only'})
with open(p,'w',encoding='utf-8') as h:json.dump(s,h,ensure_ascii=False,indent=2)
PY

[[ -d remotion/node_modules ]] || npm --prefix remotion install
BROWSER="$(command -v google-chrome || command -v chromium || command -v chromium-browser || true)"; ARGS=(); [[ -z "$BROWSER" ]] || ARGS+=(--browser-executable="$BROWSER")
rm -f output/video.mp4 output/video-silent.mp4
# Dựng hình không tiếng với 1 luồng để tránh lỗi encoder treo ở bước cuối trên runner.
RENDER_LIMIT=$((DURATION * 8 + 300))
echo "Bắt đầu dựng hình cục bộ; giới hạn an toàn: ${RENDER_LIMIT}s"
render_cmd=(npx --prefix remotion remotion render remotion/src/index.ts StickTalk output/video-silent.mp4 --props=assets/story.json --public-dir=remotion/public --codec=h264 --concurrency=1 "${ARGS[@]}")
if command -v timeout >/dev/null 2>&1; then
  timeout --signal=TERM --kill-after=25s "${RENDER_LIMIT}s" "${render_cmd[@]}"
else
  "${render_cmd[@]}"
fi
[[ -s output/video-silent.mp4 ]] || { echo 'LỖI: Remotion chưa tạo được video hình hợp lệ.' >&2; exit 22; }

# Ghép tiếng riêng bằng FFmpeg, cắt theo track ngắn hơn để kết thúc chắc chắn và giữ nguyên hình H.264.
echo 'Ghép giọng đọc vào video bằng FFmpeg...'
ffmpeg -y -v warning -i output/video-silent.mp4 -i assets/narration.mp3 -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart output/video.mp4
[[ -s output/video.mp4 ]] || { echo 'LỖI: FFmpeg chưa tạo được MP4 cuối.' >&2; exit 23; }
ffmpeg -y -ss 00:00:03 -i output/video.mp4 -frames:v 1 -update 1 output/preview.png
cp assets/story.json output/story.json
[[ -f assets/research.json ]] && cp assets/research.json output/research.json || true
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate -show_entries format=duration,size -of default=noprint_wrappers=1 output/video.mp4
rm -f output/video-silent.mp4
echo 'Hoàn tất: output/video.mp4'
