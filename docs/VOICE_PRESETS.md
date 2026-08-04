# Preset giọng đọc Premium StickTalk

Workflow hiển thị và truyền trực tiếp bảy tên preset tiếng Việt:

| Preset | Edge TTS voice | Đặc tính |
|---|---|---|
| Nam miền Bắc MC | `vi-VN-NamMinhNeural` | Rõ, gọn, chất MC |
| Nam miền Bắc Nội lực | `vi-VN-NamMinhNeural` | Trầm và chắc |
| Nam miền Bắc Nội lực Plus | `vi-VN-NamMinhNeural` | Chậm nhất, bass mạnh, âm lượng lớn, nén và giới hạn đỉnh chuyên sâu |
| Nam miền Bắc Podcast | `vi-VN-NamMinhNeural` | Ấm và gần |
| Nam miền Bắc Truyền cảm | `vi-VN-NamMinhNeural` | Chậm, giàu cảm xúc |
| Nam miền Bắc Doanh nhân | `vi-VN-NamMinhNeural` | Điềm tĩnh, dứt khoát |
| Nữ miền Bắc Dịu nhẹ | `vi-VN-HoaiMyNeural` | Nhẹ và sáng |

Tất cả preset nam miền Bắc đều được kiểm tra bắt buộc dùng NamMinh. Pipeline không fallback sang gTTS hay một voice khác khi Edge TTS lỗi; render sẽ dừng để không phát hành nhầm giọng.

## Nội lực Plus

Văn bản được chuẩn hóa cách đọc số, số thập phân, `%`, `$`, `km`, `triệu` và `tỷ`; câu dài được chia nhịp và thêm khoảng nghỉ theo dấu câu. Hậu kỳ dùng EQ tăng dải 90–180 Hz, compressor tỉ lệ 4:1, limiter, rồi loudness normalization ở mức -14 LUFS / -1 dBTP.
