#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"; cd "$ROOT"
IDEA="${VIDEO_IDEA:-}"; DURATION="${VIDEO_DURATION:-45}"; VOICE="${VIENEU_VOICE:-default}"; CUSTOM_VOICE_ID="${VIENEU_CUSTOM_VOICE_ID:-}"
require_value(){ [[ $# -ge 2 && -n "$2" && "$2" != --* ]] || { echo "Thiếu giá trị cho $1" >&2; exit 2; }; }
while (($#)); do case "$1" in
  --idea|--y-tuong|--ý-tưởng) require_value "$@"; IDEA="$2"; shift 2;;
  --duration|--thoi-luong|--thời-lượng) require_value "$@"; DURATION="$2"; shift 2;;
  --voice|--giong-doc|--giọng-đọc) require_value "$@"; VOICE="$2"; shift 2;;
  --custom-voice-id|--ma-giong) require_value "$@"; CUSTOM_VOICE_ID="$2"; shift 2;;
  *) echo "Tham số không hợp lệ: $1" >&2; exit 2;; esac; done
[[ -n "$IDEA" ]] || { echo 'Thiếu chủ đề video' >&2; exit 2; }
[[ "$DURATION" =~ ^(30|45|60)$ ]] || { echo "Thời lượng không hợp lệ: $DURATION" >&2; exit 2; }
export VIDEO_PROJECT="documentary" VIDEO_TEMPLATE="vox-paper-collage" VIDEO_STYLE="vox_giay_cat" VIDEO_MOTION_LEVEL="high" VIDEO_SCRIPT_MODE="tu_dong" VIDEO_WRITING_STYLE="tu_dong_theo_chu_de" VIDEO_CONTENT_FORMAT="narration" VIDEO_TONE="trung_tính" VIDEO_TEMPLATE_SOURCE="Nội bộ - CSS/SVG/Remotion tự tạo" VIDEO_TEMPLATE_LICENSE="MIT (theo giấy phép repository)" VIENEU_EMOTION="Kể chuyện"
printf '%s\n' "=== VOX PAPER COLLAGE ENGINE ===" "Chủ đề: $IDEA" "Thời lượng: $DURATION giây" "Giọng VieNeu: $VOICE" "Quy trình: nghiên cứu → biên tập phủ toàn chủ đề → cân thoại → ảnh/icon → dựng Vox"
mkdir -p assets output remotion/public/assets
python3 scripts/generate_story.py --idea "$IDEA" --duration "$DURATION" --voice "$VOICE"
python3 scripts/ground_story.py assets/story.json --topic "$IDEA"
# Editorial guard: broad history/biography prompts must cover the full chronology,
# not collapse into one subtopic such as death/funeral. Generic for every topic.
python3 scripts/editorial_story_guard.py --story assets/story.json --topic "$IDEA"
python3 scripts/fit_factual_narration.py --story assets/story.json --duration "$DURATION"
python3 -m scripts.entity_visual_planner --story assets/story.json --topic "$IDEA"
python3 -m scripts.asset_providers.manager
rm -rf remotion/public/assets/generated-assets; mkdir -p remotion/public/assets/generated-assets; cp -R assets/generated-assets/. remotion/public/assets/generated-assets/
python3 scripts/generate_tts.py --voice "$VOICE" --custom-voice-id "$CUSTOM_VOICE_ID" --emotion "Kể chuyện"
cp assets/narration.mp3 remotion/public/assets/narration.mp3
python3 - <<'PY'
import json
p='assets/story.json'
with open(p,encoding='utf-8') as h:s=json.load(h)
s.update({'audio':'assets/narration.mp3','project':'documentary','template':'vox-paper-collage','style':'vox_giay_cat','motionLevel':'high','contentMode':'research-first-editorial-auto-by-topic'})
with open(p,'w',encoding='utf-8') as h:json.dump(s,h,ensure_ascii=False,indent=2)
PY
[[ -d remotion/node_modules ]] || npm --prefix remotion install
BROWSER="$(command -v google-chrome || command -v chromium || command -v chromium-browser || true)"; ARGS=(); [[ -z "$BROWSER" ]] || ARGS+=(--browser-executable="$BROWSER")
npx --prefix remotion remotion render remotion/src/index.ts StickTalk output/video.mp4 --props=assets/story.json --public-dir=remotion/public --codec=h264 "${ARGS[@]}"
ffmpeg -y -ss 00:00:03 -i output/video.mp4 -frames:v 1 output/preview.png
cp assets/story.json output/story.json
# research.json is an optional diagnostic artifact. The grounded research is already
# embedded in story.json, so its absence must never fail an otherwise successful render.
if [[ -f assets/research.json ]]; then
  cp assets/research.json output/research.json
fi
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate -show_entries format=duration,size -of default=noprint_wrappers=1 output/video.mp4
echo 'Hoàn tất: output/video.mp4'
