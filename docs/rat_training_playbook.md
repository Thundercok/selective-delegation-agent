# Rat Training Playbook & Wicked Tasks Log

> **Mục đích**: Ghi nhận toàn bộ các tác vụ đặc biệt, kỳ lạ (strange / wicked workflows) từ User để chuẩn hóa quy trình, tài liệu hóa dữ liệu đầu vào/đầu ra và sau này lập trình/huấn luyện cho Agent **Rat** tự động thực thi.

---

## Danh mục Tác vụ Đặc biệt Đã Ghi nhận (Wicked Playbook)

### 1. Unity macOS Game Translation & Anti-Crash Patching (Case: Scene 3 Crash)
- **Bối cảnh**: Game Unity Mono trên macOS (`MGBuster.app`) cần dịch tiếng Nhật sang tiếng Anh/Việt mà không dùng BepInEx/Wine (vì macOS SIP chặn `DYLD_INSERT_LIBRARIES`). Khi patch chay bị crash ở Scene 3 (`level3`).
- **Nguyên nhân Crash Scene 3**:
  - Tìm-thay thế chuỗi mù quáng (blind search-replace) làm đụng vào Mesh (Type 7) hoặc GameObject (Type 1), do số thực tọa độ đỉnh (vertex float) ngẫu nhiên trùng khớp với byte UTF-8 của tiếng Nhật, gây lỗi `Position out of bounds!`.
- **Quy trình chuẩn dạy Rat**:
  1. Phải filter nghiêm ngặt object type: chỉ patch Type 12 (Text), Type 19/31 (TextMeshPro), Type 114 (MonoBehaviour).
  2. Bẫy 64KB heap trong `Assembly-CSharp.dll`: Quét full offset 24-bit (`\x72...\x70`), không dùng 16-bit để không bỏ sót 75% thoại.
  3. Dùng Base64 TSV để tránh lỗi quote `"` và newline `\n`.
  4. Sau khi patch, chạy `xattr -cr` xóa cờ quarantine của macOS.
- **Tài liệu chi tiết**: [unity_mac_translation_workflow.md](file:///Users/thundercock2/Documents/Github/selective-delegation-agent/docs/unity_mac_translation_workflow.md)

---

### 2. Academic PDF Retrieval & Paywall Classifier
- **Bối cảnh**: Tải hàng loạt bài báo nghiên cứu khoa học vào thư mục `~/Downloads/tai-lieu-vong-2/` và phân loại tình trạng truy cập.
- **Quy trình chuẩn dạy Rat**:
  1. Chuẩn hóa tên file: `tác_giả-năm.pdf` (e.g. `braun-clarke-2006.pdf`).
  2. Tự động tìm Open Access qua DOI / Europe PMC / arXiv / bioRxiv / OpenAlex.
  3. Nếu đụng paywall thương mại hoặc Bot/CAPTCHA challenge (Google Scholar, ResearchGate): gắn nhãn `[TM]` và báo cáo lý do rõ ràng, tuyệt đối không cố bypass để tránh vi phạm bảo mật.

---

### 3. Blender Python 3D Mascot Asset Generation (PS1 Retro Style)
- **Bối cảnh**: Dựng mascot 3D bằng code (Blender Python), không dùng AI image generation, xuất PNG trong suốt chuẩn phong cách PS1.
- **Quy trình chuẩn dạy Rat**:
  1. Sử dụng topology có sẵn (`rat.obj`) thay vì ghép khối hình học rời rạc để đảm bảo độ tự nhiên.
  2. Texture mapping: Đổi palette sang cool grey, thêm pixel whiskers trắng, mũi và tai hồng.
  3. Camera & Lighting: Set góc 3/4 isometric, dùng flat-shading (`shade_flat()`), bật `film_transparent = True`.
- **Tài liệu chi tiết**: [HANDOFF_NOTES.md](file:///Users/thundercock2/Documents/rat-mascot/HANDOFF_NOTES.md)

---

## Log Tác vụ Mới Tiếp Theo
*(Sẵn sàng ghi nhận task wicked mới hôm nay...)*
