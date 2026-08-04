#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"; cd "$ROOT"
IDEA=""; DURATION=45; TONE="sâu sắc"; FORMAT="hybrid"; STYLE="dark_neon"; VOICE="vi-VN-NamMinhNeural"
while (($#)); do
  case "$1" in
    --idea) IDEA="${2:-}"; shift 2;;
    --duration) DURATION="${2:-45}"; shift 2;;
    --tone) TONE="${2:-sâu sắc}"; shift 2;;
    --format) FORMAT="${2:-hybrid}"; shift 2;;
    --style) STYLE="${2:-dark_neon}"; shift 2;;
    --voice) VOICE="${2:-vi-VN-NamMinhNeural}"; shift 2;;
    *) echo "Tham số không hợp lệ: $1" >&2; exit 2;;
  esac
done
[[ -n "$IDEA" ]] || { echo 'Thiếu --idea' >&2; exit 2; }
mkdir -p assets output remotion/public/assets
python3 scripts/generate_story.py --idea "$IDEA" --duration "$DURATION" --tone "$TONE" --format "$FORMAT" --style "$STYLE" --voice "$VOICE"
python3 scripts/generate_tts.py --voice "$VOICE"
cp assets/narration.mp3 remotion/public/assets/narration.mp3
python3 - <<'PY'
import json
p='assets/story.json'
d=json.load(open(p,encoding='utf-8'))
d['audio']='assets/narration.mp3'
json.dump(d,open(p,'w',encoding='utf-8'),ensure_ascii=False,indent=2)
PY
[[ -d remotion/node_modules ]] || npm --prefix remotion install
BROWSER="$(command -v google-chrome || command -v chromium || command -v chromium-browser || true)"
ARGS=(); [[ -z "$BROWSER" ]] || ARGS+=(--browser-executable="$BROWSER")
npx --prefix remotion remotion render remotion/src/index.ts StickTalk output/video.mp4 --props=assets/story.json --public-dir=remotion/public --codec=h264 "${ARGS[@]}"
ffmpeg -y -ss 00:00:03 -i output/video.mp4 -frames:v 1 output/preview.png
cp assets/story.json output/story.json
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate -show_entries format=duration,size -of default=noprint_wrappers=1 output/video.mp4
echo 'Hoàn tất: output/video.mp4'
