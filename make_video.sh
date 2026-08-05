#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

IDEA="${VIDEO_IDEA:-}"
DURATION="${VIDEO_DURATION:-45}"
TONE="${VIDEO_TONE:-sâu_sắc}"
CONTENT_FORMAT="${VIDEO_CONTENT_FORMAT:-hybrid}"
PROJECT="${VIDEO_PROJECT:-motivation}"
TEMPLATE="${VIDEO_TEMPLATE:-prompt-to-video}"
STYLE="${VIDEO_STYLE:-}"
VOICE="${VIENEU_VOICE:-default}"
CUSTOM_VOICE_ID="${VIENEU_CUSTOM_VOICE_ID:-}"
VOICE_EMOTION="${VIENEU_EMOTION:-Tự nhiên}"
MOTION_LEVEL="${VIDEO_MOTION_LEVEL:-}"
SCRIPT_MODE="${VIDEO_SCRIPT_MODE:-}"
WRITING_STYLE="${VIDEO_WRITING_STYLE:-}"

RESOLVED="$(python3 scripts/resolve_project_template.py --project "$PROJECT" --template "$TEMPLATE" --format shell)"
eval "$RESOLVED"
STYLE="${STYLE:-$VIDEO_STYLE}"
MOTION_LEVEL="${MOTION_LEVEL:-$VIDEO_MOTION_LEVEL}"
SCRIPT_MODE="${SCRIPT_MODE:-$VIDEO_SCRIPT_MODE}"
WRITING_STYLE="${WRITING_STYLE:-$VIDEO_WRITING_STYLE}"

case "$STYLE" in
  "Phác thảo điện ảnh — Trầm") STYLE=phac_thao_dien_anh_tram;;
  "Phác thảo điện ảnh — Sách kỹ năng") STYLE=phac_thao_sach_ky_nang;;
  "Phác thảo điện ảnh — Doanh nhân") STYLE=phac_thao_doanh_nhan;;
esac

require_value() { [[ $# -ge 2 && -n "$2" && "$2" != --* ]] || { echo "Thiếu giá trị cho $1" >&2; exit 2; }; }
while (($#)); do
  case "$1" in
    --idea|--y-tuong|--ý-tưởng) require_value "$@"; IDEA="$2"; shift 2;;
    --duration|--thoi-luong|--thời-lượng) require_value "$@"; DURATION="$2"; shift 2;;
    --tone|--giong-dieu|--giọng-điệu) require_value "$@"; TONE="$2"; shift 2;;
    --format|--content-format|--dinh-dang|--định-dạng) require_value "$@"; CONTENT_FORMAT="$2"; shift 2;;
    --project) require_value "$@"; PROJECT="$2"; shift 2;;
    --template) require_value "$@"; TEMPLATE="$2"; shift 2;;
    --style|--phong-cach|--phong-cách) require_value "$@"; STYLE="$2"; shift 2;;
    --voice|--giong-doc|--giọng-đọc) require_value "$@"; VOICE="$2"; shift 2;;
    --custom-voice-id|--ma-giong) require_value "$@"; CUSTOM_VOICE_ID="$2"; shift 2;;
    --voice-emotion|--cam-xuc-giong) require_value "$@"; VOICE_EMOTION="$2"; shift 2;;
    --motion-level|--muc-do-chuyen-dong|--mức-độ-chuyển-động) require_value "$@"; MOTION_LEVEL="$2"; shift 2;;
    --script-mode|--che-do-viet-kich-ban|--chế-độ-viết-kịch-bản) require_value "$@"; SCRIPT_MODE="$2"; shift 2;;
    --writing-style|--phong-cach-viet|--phong-cách-viết) require_value "$@"; WRITING_STYLE="$2"; shift 2;;
    *) echo "Tham số không hợp lệ: $1" >&2; exit 2;;
  esac
done

[[ -n "$IDEA" ]] || { echo 'Thiếu ý tưởng video' >&2; exit 2; }
[[ "$DURATION" =~ ^(30|45|60)$ ]] || { echo "Thời lượng không hợp lệ: $DURATION" >&2; exit 2; }

printf '%s\n' "=== CẤU HÌNH TẠO VIDEO ===" "Dự án: $PROJECT" "Mẫu video: $TEMPLATE" "Nguồn mở: ${VIDEO_TEMPLATE_SOURCE:-không rõ}" "Giấy phép: ${VIDEO_TEMPLATE_LICENSE:-không rõ}" "Chủ đề: $IDEA" "Thời lượng: $DURATION giây" "Phong cách: $STYLE" "Giọng VieNeu: $VOICE" "Cảm xúc giọng: $VOICE_EMOTION"

mkdir -p assets output remotion/public/assets

python3 scripts/generate_story.py \
  --idea "$IDEA" --duration "$DURATION" --tone "$TONE" --format "$CONTENT_FORMAT" \
  --style "$STYLE" --voice "$VOICE" --motion-level "$MOTION_LEVEL" \
  --script-mode "$SCRIPT_MODE" --writing-style "$WRITING_STYLE"

if [[ "$PROJECT" == "motivation" ]]; then
  python3 scripts/enrich_motivation_story.py \
    --story assets/story.json --topic "$IDEA" --template "$TEMPLATE" --duration "$DURATION"
fi

# Mỗi cảnh có một ảnh AI riêng, bám theo lời dẫn và phong cách mẫu đã chọn.
python3 scripts/generate_scene_images.py
rm -rf remotion/public/assets/generated-images
mkdir -p remotion/public/assets/generated-images
cp -R assets/generated-images/. remotion/public/assets/generated-images/

# Giữ nguyên toàn bộ hệ thống VieNeu-TTS đã ổn định.
python3 scripts/generate_tts.py --voice "$VOICE" --custom-voice-id "$CUSTOM_VOICE_ID" --emotion "$VOICE_EMOTION"
cp assets/narration.mp3 remotion/public/assets/narration.mp3

python3 - <<'PY'
import json, os
p='assets/story.json'
with open(p,encoding='utf-8') as f:d=json.load(f)
d['audio']='assets/narration.mp3'
d['project']=os.getenv('VIDEO_PROJECT','motivation')
d['template']=os.getenv('VIDEO_TEMPLATE','prompt-to-video')
d['templateSource']=os.getenv('VIDEO_TEMPLATE_SOURCE','')
d['templateLicense']=os.getenv('VIDEO_TEMPLATE_LICENSE','')
with open(p,'w',encoding='utf-8') as f:json.dump(d,f,ensure_ascii=False,indent=2)
PY

[[ -d remotion/node_modules ]] || npm --prefix remotion install
BROWSER="$(command -v google-chrome || command -v chromium || command -v chromium-browser || true)"
ARGS=(); [[ -z "$BROWSER" ]] || ARGS+=(--browser-executable="$BROWSER")
npx --prefix remotion remotion render remotion/src/index.ts StickTalk output/video.mp4 --props=assets/story.json --public-dir=remotion/public --codec=h264 "${ARGS[@]}"
ffmpeg -y -ss 00:00:03 -i output/video.mp4 -frames:v 1 output/preview.png
cp assets/story.json output/story.json
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate -show_entries format=duration,size -of default=noprint_wrappers=1 output/video.mp4
echo 'Hoàn tất: output/video.mp4'
