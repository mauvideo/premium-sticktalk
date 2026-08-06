# Định hướng sản phẩm: video tự động theo mọi chủ đề

`premium-sticktalk` nhận **một chủ đề** và tạo video hoàn chỉnh. Hệ thống không
được chứa logic riêng cho một nhân vật, doanh nghiệp, sự kiện hoặc nhóm chủ đề.
Ví dụ trong tài liệu và test chỉ là dữ liệu kiểm chứng tính tổng quát.

## Luồng phát triển chính thức

Các tầng được phát triển theo đúng thứ tự sau:

1. **Story Engine** — hiểu chủ đề, chia cảnh; mỗi cảnh cung cấp thông tin mới.
2. **Entity & Asset Planner** — xác định người, địa điểm, tổ chức, thời gian,
   sự kiện, vật thể, bản đồ, biểu đồ và tìm tài nguyên có giấy phép phù hợp.
3. **Visual Planner** — biến bằng chứng thành layout nhiều lớp, không biến một
   ảnh toàn màn hình thành cảnh bằng thao tác zoom.
4. **Vox Composition Engine** — dựng mỗi cảnh như một trang tạp chí chuyển động.
5. **Motion Engine** — documentary motion, parallax và chuyển động độc lập giữa lớp.
6. **Render Engine** — ghép hình, lời thoại và audio thành video cuối.

Không mở rộng sang template rời rạc trước khi các tầng trên của Vox Paper
Collage đạt tiêu chuẩn chất lượng.

## Hợp đồng chất lượng Vox Paper Collage

Mỗi scene phải có paper texture, grid hoặc newspaper, cutout chủ thể có viền
trắng/vàng, một đến hai bằng chứng bối cảnh, ít nhất một lớp map/chart/timeline,
mảng màu editorial, marker hoặc hand-drawn annotation, typography, shadow và
parallax. Bản đồ, biểu đồ và timeline là lớp dữ liệu có ngữ nghĩa lấy từ planner,
không phải icon trang trí ngẫu nhiên.

Asset người thật phải có danh tính và giấy phép được xác minh. Khi không tìm
được ảnh phù hợp, scene dùng silhouette hoặc minh họa trung tính và manifest
phải ghi rõ fallback; tuyệt đối không thay bằng ảnh của người khác.
