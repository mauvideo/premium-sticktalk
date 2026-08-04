# Premium StickTalk

Công cụ tạo video người que dọc 1080×1920 từ một ý tưởng ngắn. Hệ thống tự tạo kịch bản 8 cảnh, giọng đọc tiếng Việt, phụ đề động và video MP4 bằng Remotion.

## Cách dùng dễ nhất

1. Mở tab **Actions**.
2. Chọn **Create StickTalk Video**.
3. Bấm **Run workflow**.
4. Nhập ý tưởng.
5. Chọn thời lượng, định dạng, tone, phong cách và giọng đọc.
6. Chờ workflow có dấu tích xanh.
7. Mở **Summary → Artifacts → sticktalk-video** để tải file ZIP.

Trong ZIP có:

- `video.mp4`
- `preview.png`
- `script.txt`
- `story.json`

## Tùy chọn

Phong cách:
- `dark_neon`
- `whiteboard`
- `motivational`

Giọng đọc:
- Nam miền Bắc, phong cách MC thời sự (mặc định): `nam_bac_news`
- Nữ Việt Nam: `nu_viet_nam`

Preset `nam_bac_news` dùng Edge TTS `vi-VN-NamMinhNeural` với tốc độ
`-6%`, cao độ `-3Hz`, âm lượng `+8%` và khoảng nghỉ tự nhiên theo dấu câu.
Nếu Edge TTS gặp lỗi, hệ thống tự động chuyển sang gTTS.

## Chạy bằng lệnh

```bash
./make_video.sh \
  --idea "Người trưởng thành không cần thắng mọi cuộc tranh luận" \
  --duration 45 \
  --tone "sâu sắc" \
  --format hybrid \
  --style dark_neon \
  --voice nam_bac_news
```

Video được tạo tại `output/video.mp4`.

## Ghi chú Version 1

Version 1 dùng bộ mẫu thông minh để tạo kịch bản mà không cần API trả phí. Kiến trúc đã sẵn sàng để nâng cấp sang OpenAI hoặc Gemini ở phiên bản tiếp theo.
