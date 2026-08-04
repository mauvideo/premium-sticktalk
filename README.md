# Premium StickTalk V3.5 — AI Story Director

Premium StickTalk tạo video người que dọc 1080×1920 từ một ý tưởng tiếng Việt. Phiên bản 3.5 bổ sung **AI Story Director**: một đạo diễn kịch bản tự chọn cấu trúc, số cảnh, nhân vật, hành động, biểu cảm, bối cảnh, bố cục, camera và chuyển cảnh phù hợp với từng chủ đề. Hệ thống giọng đọc hiện có và quy trình xuất MP4 bằng Remotion được giữ nguyên.

## AI Story Director hoạt động ra sao?

Khi chọn **Tự động theo chủ đề**, hệ thống phân tích từ khóa và ngữ nghĩa của ý tưởng rồi xếp vào một trong 10 loại:

1. danh sách;
2. giải thích;
3. câu chuyện;
4. đối thoại;
5. so sánh;
6. hướng dẫn;
7. tin tức;
8. phân tích;
9. trích dẫn hoặc quan điểm;
10. hài tình huống.

Ý tưởng chưa đủ dấu hiệu được xử lý bằng loại **kể chuyện kết hợp giải thích**. Mỗi loại có dàn ý riêng thay vì bị ép vào mẫu tám cảnh. Video 30 giây có 5–7 cảnh, 45 giây có 7–10 cảnh và 60 giây có 9–13 cảnh; tổng thời lượng được cân bằng đúng lựa chọn.

Đạo diễn luật chạy được ngay cả khi không có khóa API. Việc chọn câu và chỉ dẫn dựa trên loại nội dung, giọng điệu cùng dấu vân tay ổn định của chủ đề, vì vậy có tính tái lập nhưng không bốc ngẫu nhiên thiếu ngữ cảnh. Kiến trúc đã có giao diện nhà cung cấp để sau này nối OpenAI hoặc Gemini mà không lưu khóa trong mã nguồn.

## Tạo video bằng GitHub Actions

1. Mở thẻ **Actions**, chọn quy trình **Tạo video Premium StickTalk** và bấm **Run workflow**.
2. Nhập ý tưởng, chọn 30, 45 hoặc 60 giây.
3. Ở **Chế độ viết kịch bản**, giữ **Tự động theo chủ đề** để AI Story Director tự quyết định. Bạn cũng có thể buộc chế độ một người dẫn chuyện, hai nhân vật đối thoại, kể chuyện, danh sách hoặc phân tích.
4. Chọn giọng điệu, phong cách, mức chuyển động và giọng đọc rồi chạy quy trình.
5. Khi có dấu tích xanh, mở phần **Artifacts**, tải `sticktalk-video` và giải nén.

Gói kết quả gồm `video.mp4`, `preview.png`, `script.txt` và `story.json`. File MP4 là video hoàn chỉnh để tải lên nền tảng, còn `story.json` chứa cả trường tiếng Việt V3.5 lẫn trường kỹ thuật tương thích Remotion V3.

## Chạy trên máy cá nhân

```bash
./make_video.sh \
  --idea "7 cách tiết kiệm tiền hiệu quả" \
  --duration 45 \
  --tone "gần gũi" \
  --format narration \
  --script-mode "Tự động theo chủ đề" \
  --style người_que_doanh_nhân \
  --motion-level medium \
  --voice "Nam miền Bắc Nội lực Plus"
```

Video được lưu tại `output/video.mp4`; ảnh xem trước ở `output/preview.png`.

## Giọng đọc và phong cách

Các phong cách gồm người que triết lý, TikTok, doanh nhân, kể chuyện và tin tức AI. Tên kỹ thuật cũ như `dark_neon`, `whiteboard` và `motivational` vẫn dùng được.

Các giọng đọc hiện có:

- Nam miền Bắc MC;
- Nam miền Bắc Nội lực;
- Nam miền Bắc Nội lực Plus (mặc định);
- Nam miền Bắc Podcast;
- Nam miền Bắc Truyền cảm;
- Nam miền Bắc Doanh nhân;
- Nữ miền Bắc Dịu nhẹ.

Chi tiết hậu kỳ giọng đọc nằm trong [`docs/VOICE_PRESETS.md`](docs/VOICE_PRESETS.md). V3.5 không thay đổi mã tạo TTS.

## Kiểm tra hai kịch bản

```bash
python scripts/kiem_tra_do_khac_nhau.py duong-dan/video-a.json duong-dan/video-b.json
```

Lệnh báo tỷ lệ trùng câu chữ, hành động, camera, bố cục và chuyển cảnh; mã thoát khác không nếu một chỉ số vượt ngưỡng chất lượng.
