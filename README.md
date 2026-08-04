# Premium StickTalk — Google Cloud TTS và Phác thảo điện ảnh

Premium StickTalk tạo video dọc 1080×1920, 30 khung hình/giây và giữ ba thời lượng 30, 45, 60 giây. Bản nâng cấp bổ sung **Google Cloud Text-to-Speech thật** (mặc định), vẫn giữ **Microsoft Edge TTS**, cùng phong cách **Phác thảo điện ảnh trên giấy**. Khi chọn Google, hệ thống không bao giờ tự chuyển sang Edge hoặc một Voice ID khác.

## Cấu hình Google Cloud Text-to-Speech

1. Trong Google Cloud Console, tạo hoặc chọn một dự án và bật thanh toán cho dự án đó.
2. Mở **API và dịch vụ → Thư viện**, tìm **Cloud Text-to-Speech API** rồi chọn **Bật**.
3. Mở **IAM và quản trị → Tài khoản dịch vụ**, tạo tài khoản dịch vụ với quyền sử dụng Text-to-Speech phù hợp, sau đó tạo khóa JSON. Hãy giới hạn và luân chuyển thông tin xác thực theo chính sách của tổ chức.
4. Trong GitHub, mở **Settings → Secrets and variables → Actions → New repository secret**. Đặt tên `GOOGLE_CLOUD_CREDENTIALS_JSON` và dán toàn bộ nội dung JSON làm giá trị.
5. Tuyệt đối không lưu khóa JSON vào Git, README, artifact hoặc log. Workflow chỉ ghi secret vào file tạm, đặt `GOOGLE_APPLICATION_CREDENTIALS`, rồi xóa file ở bước `always()`.

Google Cloud có thể phát sinh chi phí theo số ký tự và loại giọng. Hãy xem bảng giá hiện hành, đặt ngân sách/cảnh báo chi phí và xóa tài nguyên không còn dùng. Repository không hard-code mã dự án.

Chạy trên máy cá nhân bằng Application Default Credentials:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/duong-dan/credentials.json"
export TTS_PROVIDER=google
export GOOGLE_TTS_VOICE=google_nam_neural2
./make_video.sh --idea "Khi hiệu quả trở thành gánh nặng." --duration 45 \
  --style phac_thao_dien_anh_tram --voice "Google Nam Neural 2"
```

Nếu chưa cấu hình, tiến trình dừng với hướng dẫn tiếng Việt; không fallback. Metadata gồm nhà cung cấp, mã preset, Voice ID thực tế, dung lượng và thời lượng được ghi tại `output/tts-info.json`.

## Nghe thử và chọn giọng Google

Trong thẻ **Actions**, chạy workflow **Tạo bản nghe thử giọng Google**. Tải artifact `ban-nghe-thu-giong-google`, nghe bốn file MP3 và xem `thong_tin_giong.json`. Bộ thử gồm Neural2-D, WaveNet-D, Chirp3-HD-Charon và Chirp3-HD-Fenrir. Các giọng Chirp được đối chiếu với danh sách giọng Google ở thời điểm chạy; thiếu Voice ID sẽ làm workflow thất bại, không thay thế ngầm.

Các tên “Google Nam Bắc” là preset phục vụ **nghe và tự chọn**, không phải khẳng định giọng thuộc vùng miền. Người dùng cần nghe bản thử trước khi quyết định.

Voice ID được quản lý tập trung trong `scripts/tts/presets.py`: `vi-VN-Neural2-D`, `vi-VN-Wavenet-D`, `vi-VN-Standard-D`, `vi-VN-Chirp3-HD-Charon`, `vi-VN-Chirp3-HD-Fenrir`, `vi-VN-Chirp3-HD-Orus`, `vi-VN-Neural2-A` và `vi-VN-Wavenet-C`.

## Chọn Phác thảo điện ảnh trên giấy

Trong workflow **Tạo video Premium StickTalk**, tại **Phong cách hình ảnh**, chọn một trong ba mã tương ứng với tên hiển thị:

- `phac_thao_dien_anh_tram` — **Phác thảo điện ảnh — Trầm**;
- `phac_thao_sach_ky_nang` — **Phác thảo điện ảnh — Sách kỹ năng**;
- `phac_thao_doanh_nhan` — **Phác thảo điện ảnh — Doanh nhân**.

Theme dùng giấy kem, SVG nét chì tự tạo, typography tối giản, mười bố cục và tám chuyển cảnh luân phiên. Các trường tùy chọn cho mỗi cảnh là `phong_cach_minh_hoa`, `mo_ta_hinh_anh`, `bo_cuc_phac_thao`, `mau_nhan` và `muc_do_chi_tiet`. Không tải tài sản không rõ giấy phép.

Hệ thống kịch bản hiện hữu tiếp tục tập trung vào hook nhanh, mỗi cảnh một ý, ví dụ cụ thể, bước ngoặt rõ và kết thúc phù hợp. AI Script Writer và AI Story Director không bị thay đổi trong lần nâng cấp này.

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

## Giọng Edge hiện hữu

Chọn nhà cung cấp `edge` để dùng các preset Microsoft Edge hiện hữu, gồm **Nam miền Bắc Nội lực Plus**. Giọng Edge không dùng chuỗi hậu kỳ hoặc thông số tốc độ của Google. Chi tiết preset cũ nằm trong [`docs/VOICE_PRESETS.md`](docs/VOICE_PRESETS.md).
