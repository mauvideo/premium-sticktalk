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
[[ "$DURATION" =~ ^(30|45|60)$ ]] || { echo "Thời lượng không hợp lệ: $DURATION" >&2; exit 2; }
[[ "$ASPECT" =~ ^(9:16|16:9)$ ]] || { echo "Tỷ lệ không hợp lệ: $ASPECT" >&2; exit 2; }
export VIDEO_PROJECT="documentary" VIDEO_TEMPLATE="vox-paper-collage" VIDEO_STYLE="vox_giay_cat" VIDEO_MOTION_LEVEL="high" VIDEO_SCRIPT_MODE="ai_research_grounded" VIDEO_CONTENT_FORMAT="narration" VIDEO_TONE="trung_tính" VIENEU_EMOTION="Kể chuyện"
printf '%s\n' "=== PREMIUM STICKTALK COMMERCIAL PIPELINE ===" "Chủ đề: $IDEA" "Thời lượng: $DURATION giây" "Khung hình: $ASPECT" "Giọng VieNeu: $VOICE" "Quy trình: Gemini text → facts → kịch bản Vox → ảnh miễn phí → VieNeu + phụ đề cùng text → Remotion"
mkdir -p assets output remotion/public/assets

# Gemini 503/429 là lỗi tạm thời. Retry toàn bước text với backoff; nếu model chính
# vẫn bận thì lần cuối chuyển sang model Flash ổn định dự phòng.
PRIMARY_MODEL="${GEMINI_MODEL:-gemini-3.6-flash}"
FALLBACK_MODEL="${GEMINI_FALLBACK_MODEL:-gemini-3.5-flash}"
AI_OK=0
for attempt in 1 2 3 4 5; do
  if (( attempt == 5 )); then export GEMINI_MODEL="$FALLBACK_MODEL"; else export GEMINI_MODEL="$PRIMARY_MODEL"; fi
  echo "Gemini text attempt $attempt/5 — model=$GEMINI_MODEL"
  if python3 scripts/commercial_ai_pipeline.py --topic "$IDEA" --duration "$DURATION" --voice "$VOICE"; then
    AI_OK=1; break
  fi
  wait_seconds=$((2 ** attempt))
  echo "Gemini tạm lỗi; chờ ${wait_seconds}s rồi thử lại..."
  sleep "$wait_seconds"
done
[[ "$AI_OK" == "1" ]] || { echo "Gemini vẫn không khả dụng sau retry + fallback." >&2; exit 1; }

python3 - <<PY
import json
p='assets/story.json'
with open(p,encoding='utf-8') as h:s=json.load(h)
s['aspectRatio']='$ASPECT'
with open(p,'w',encoding='utf-8') as h:json.dump(s,h,ensure_ascii=False,indent=2)
PY

python3 -m scripts.entity_visual_planner --story assets/story.json --topic "$IDEA"
python3 -m scripts.asset_providers.manager
rm -rf remotion/public/assets/generated-assets; mkdir -p remotion/public/assets/generated-assets; cp -R assets/generated-assets/. remotion/public/assets/generated-assets/

python3 scripts/generate_tts.py --voice "$VOICE" --custom-voice-id "$CUSTOM_VOICE_ID" --emotion "Kể chuyện"
cp assets/narration.mp3 remotion/public/assets/narration.mp3
python3 - <<'PY'
import json
p='assets/story.json'
with open(p,encoding='utf-8') as h:s=json.load(h)
s.update({'audio':'assets/narration.mp3','project':'documentary','template':'vox-paper-collage','style':'vox_giay_cat','motionLevel':'high','contentMode':'commercial-ai-grounded'})
with open(p,'w',encoding='utf-8') as h:json.dump(s,h,ensure_ascii=False,indent=2)
PY

[[ -d remotion/node_modules ]] || npm --prefix remotion install
BROWSER="$(command -v google-chrome || command -v chromium || command -v chromium-browser || true)"; ARGS=(); [[ -z "$BROWSER" ]] || ARGS+=(--browser-executable="$BROWSER")
npx --prefix remotion remotion render remotion/src/index.ts StickTalk output/video.mp4 --props=assets/story.json --public-dir=remotion/public --codec=h264 "${ARGS[@]}"
ffmpeg -y -ss 00:00:03 -i output/video.mp4 -frames:v 1 -update 1 output/preview.png
cp assets/story.json output/story.json
[[ -f assets/research.json ]] && cp assets/research.json output/research.json || true
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate -show_entries format=duration,size -of default=noprint_wrappers=1 output/video.mp4
echo 'Hoàn tất: output/video.mp4'
