# Preset giọng đọc Premium StickTalk

Workflow mặc định dùng Microsoft Edge TTS và hiển thị năm preset tiếng Việt:

| Preset | Edge TTS voice | Đặc tính |
|---|---|---|
| Nam tiếng Việt — Tự nhiên | `vi-VN-NamMinhNeural` | Rõ, tự nhiên |
| Nam tiếng Việt — Nội lực | `vi-VN-NamMinhNeural` | Trầm và chắc |
| Nam tiếng Việt — Phát thanh | `vi-VN-NamMinhNeural` | Điềm tĩnh, dứt khoát |
| Nam tiếng Việt — Kể chuyện | `vi-VN-NamMinhNeural` | Chậm, giàu cảm xúc |
| Nữ tiếng Việt — Tự nhiên | `vi-VN-HoaiMyNeural` | Nhẹ và sáng |

Tất cả preset nam đều được kiểm tra bắt buộc dùng NamMinh. Pipeline không fallback sang HoaiMy, gTTS hay một voice khác khi Edge TTS lỗi; render sẽ dừng để không phát hành nhầm giọng. Tên preset không khẳng định vùng miền vì Microsoft không công bố vùng giọng cho các Voice ID này.

## Hậu kỳ âm thanh

Văn bản được chuẩn hóa cách đọc số, số thập phân, `%`, `$`, `km`, `triệu` và `tỷ`; câu dài được chia nhịp và thêm khoảng nghỉ theo dấu câu. Hậu kỳ dùng EQ tăng dải 90–180 Hz, compressor tỉ lệ 4:1, limiter, rồi loudness normalization ở mức -14 LUFS / -1 dBTP.
