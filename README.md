# Premium StickTalk V3.6 — AI Script Writer Pro

Premium StickTalk tạo video người que dọc 1080×1920 từ một ý tưởng tiếng Việt. V3.6 tập trung vào chất lượng câu chữ: hook nhanh, mỗi cảnh một ý, ví dụ cụ thể, bước ngoặt rõ và kết thúc phù hợp. Các thời lượng 30, 45 và 60 giây, hệ thống TTS cùng engine Remotion được giữ nguyên.

## Story Director và Script Writer khác nhau thế nào?

- **AI Story Director** (`scripts/story_director.py`) nhận diện loại nội dung, quyết định số cảnh, dàn ý, nhân vật, bố cục, camera và chuyển cảnh. Nó không còn ghép toàn bộ lời dẫn từ vài mẫu cứng.
- **AI Script Writer Pro** (`scripts/script_writer.py`) nhận diện lĩnh vực rồi viết hook, lời từng cảnh, ví dụ, hội thoại, cao trào, kết luận và CTA. Bộ humanizer loại văn mẫu, phát hiện câu lặp và rút câu dài cho giọng đọc.
- **Bộ chấm điểm** (`scripts/cham_diem_kich_ban.py`) đánh giá hook, độ cụ thể, tính tự nhiên, cấu trúc, cao trào, đa dạng câu, kết thúc và mức sạch văn mẫu. Ngưỡng đạt là 75/100; đầu ra dưới ngưỡng được làm sạch tối đa hai lần và giữ cảnh báo trong `story.json`.

Chế độ mặc định chạy hoàn toàn cục bộ, không cần khóa API. Các adapter OpenAI và Gemini chỉ chuẩn bị giao diện tích hợp và đọc `OPENAI_API_KEY` hoặc `GEMINI_API_KEY` từ môi trường; không có khóa nào được ghi cứng. Mọi đầu ra, kể cả đầu ra từ API khi được tích hợp, phải qua kiểm tra trước khi render. Tin tức chỉ dùng dữ kiện trong đầu vào; ví dụ chưa kiểm chứng luôn được giới thiệu là giả định bằng cách nói “Hãy tưởng tượng…”.

## Chọn phong cách viết nội dung

Trong **Actions → Tạo video Premium StickTalk → Run workflow**, mục **Phong cách viết nội dung** có các lựa chọn:

1. Tự động theo chủ đề — mặc định, tự nhận diện trong 14 lĩnh vực;
2. Ngắn gọn TikTok;
3. Kể chuyện cảm xúc;
4. Thực tế kinh doanh;
5. Giải thích dễ hiểu;
6. Đối thoại tự nhiên;
7. Tin tức rõ ràng.

Tên kỹ thuật ổn định được ánh xạ bên trong và không xuất hiện trên giao diện. Các lựa chọn cũ về chế độ kịch bản, hình ảnh, chuyển động và giọng đọc vẫn hoạt động.

## Tạo và tải video bằng GitHub Actions

1. Mở thẻ **Actions**, chọn **Tạo video Premium StickTalk** rồi bấm **Run workflow**.
2. Nhập ý tưởng; chọn thời lượng 30, 45 hoặc 60 giây và phong cách viết.
3. Chọn các thiết lập hình ảnh, chuyển động và giọng đọc như trước, sau đó chạy workflow.
4. Khi tác vụ có dấu tích xanh, mở **Artifacts** và tải gói `sticktalk-video`.
5. Giải nén để lấy `video.mp4`, `preview.png`, `script.txt` và `story.json`.

`video.mp4` là file hoàn chỉnh để đăng. MP4 không được lưu trong Git.

## Chạy trên máy cá nhân

```bash
./make_video.sh \
  --idea "5 sai lầm khiến cửa hàng nhỏ khó phát triển." \
  --duration 45 \
  --writing-style "Thực tế kinh doanh" \
  --script-mode "Tự động theo chủ đề" \
  --voice "Nam miền Bắc Nội lực Plus"
```

Kết quả nằm trong `output/`. Để chỉ tạo kịch bản mà chưa gọi TTS hay render:

```bash
python scripts/generate_story.py \
  --idea "Vì sao bầu trời có màu xanh?" \
  --duration 45 \
  --writing-style "Giải thích dễ hiểu"
```

## Xem và kiểm tra chất lượng

- Mở `output/script.txt` để đọc liên tục toàn bộ lời sẽ được đưa vào giọng đọc. Mỗi dòng tương ứng một cảnh.
- Mở `output/story.json`, tìm `chat_luong_kich_ban.tong_diem` để xem tổng điểm, hoặc xem các điểm thành phần và mảng `canh_bao`.
- Các trường `linh_vuc`, `phong_cach_viet`, `hook`, `cao_trao` và `ket_luan` giúp kiểm tra nhanh đường dây kể. Các trường kỹ thuật V3 cũ vẫn được giữ cho Remotion.

Chấm lại một hay nhiều kịch bản:

```bash
python scripts/cham_diem_kich_ban.py output/story.json
```

So sánh hai kịch bản; tỷ lệ câu chữ phải dưới 20% cho bộ mẫu V3.6:

```bash
python scripts/kiem_tra_do_khac_nhau.py \
  examples/v3.6/01-triet-ly.json \
  examples/v3.6/02-kinh-doanh.json
```

Năm kịch bản kiểm thử theo đề bài nằm trong `examples/v3.6/`. Chúng minh họa triết lý, danh sách đúng năm mục, khoa học, lịch sử và hội thoại A/B thực sự.

## Giọng đọc

V3.6 không sửa hệ thống TTS. Các preset cũ, gồm **Nam miền Bắc Nội lực Plus** mặc định, tiếp tục sử dụng như trước. Chi tiết nằm trong [`docs/VOICE_PRESETS.md`](docs/VOICE_PRESETS.md).
