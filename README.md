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

Phong cách hình ảnh Version 3:
- `người_que_triết_lý`, `người_que_tiktok`, `người_que_doanh_nhân`
- `người_que_kể_chuyện`, `tin_tức_ai`

Mức chuyển động: `nhẹ`, `trung_bình`, `nhiều`, hoặc `viral_tiktok`.
Các tên phong cách cũ (`dark_neon`, `whiteboard`, `motivational`) vẫn hoạt động.

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
  --motion-level medium \
  --voice nam_bac_news
```

Video được tạo tại `output/video.mp4`.

## Premium Motion Engine Version 3

Mỗi cảnh có thể điều khiển độc lập camera, transition, emotion, gesture,
zoom và hiệu ứng phụ đề. Camera Engine có 12 chuyển động, Transition Engine
có 10 hiệu ứng, còn Stickman được rig theo từng bộ phận cơ thể với 17 gesture
và 10 emotion. Story JSON cũ vẫn được hỗ trợ để không làm gián đoạn workflow.
