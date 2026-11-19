# Kịch bản quan sát 30 phút: hero job A

Ngày chốt: 19/11/2026. Hero job là **A: hỏi tài liệu trên máy, trả lời kèm số trang**. Kịch bản này thay phần "3 việc" trong `docs/product_plan.md` §6 cho buổi quan sát; ngưỡng ở §6 giữ nguyên.

## Buổi này trả lời ba câu

1. Sinh viên có giữ tài liệu môn học trên Mac không, hay để trên LMS / Drive? Nếu đa số không giữ, A mất lý do tồn tại.
2. Với cùng một việc, cách quen thuộc và RAT khác nhau bao nhiêu bước, bao nhiêu lần chuyển cửa sổ, bao nhiêu giây?
3. Họ có muốn dùng lại không, và vì sao?

## Ngưỡng, ghi trước khi có dữ liệu

Giữ nguyên ngưỡng §6, quyết định sau 5 buổi:

| Kết quả sau 5 buổi | Quyết định |
|---|---|
| Từ 3/5 người muốn dùng tiếp, và RAT ít bước hơn cách cũ ở ít nhất 2/3 việc | Giữ A |
| 1-2/5 người | Chọn lại hero job |
| 0/5 người | Đổi hướng sản phẩm |
| Từ 3/5 người nói tài liệu môn học phần lớn không nằm trên máy | Dừng A, dù hai dòng trên ra sao |

Thay đổi so với §6, ghi lại cho minh bạch: §6 đo ba việc khác nhau (hỏi tài liệu, dịch, xem lịch). Khi đã chốt A, ba việc đều là biến thể của A. Đổi trước khi có bất kỳ số liệu nào; ngưỡng không đổi.

## Chuẩn bị (trước buổi, không tính vào 30 phút)

- Chưa có `.dmg`, nên buổi đầu chạy trên Mac của chủ RAT. **Thời gian cài đặt chưa đo được ở các buổi này**; ghi rõ là lỗ hổng, đo riêng khi có bản cài.
- Tài liệu: thư mục slide và giáo trình của một môn cả hai đều học (ví dụ 502044 Tổ chức máy tính). Chưa dùng file riêng của người tham gia: RAT chưa có lệnh gỡ một file khỏi chỉ mục (`rat index --purge` chỉ dọn file bị loại trừ, nhạy cảm hoặc nhị phân, không dọn file đã xoá), nên nội dung của họ sẽ nằm lại trong chỉ mục.
- Slide môn này còn một bản sao một phần ở `SchoolAppCoreRazor/1/schoolworks/to-chuc-may-tinh/`. Chỉ `rat index` thư mục `dump/schoolworks/to-chuc-may-tinh/`, để đáp án V2 chỉ nằm ở một nơi. Sau đó chạy `rat doctor`, cắm sạc, mở Ollama, hỏi thử một câu để mô hình đã nạp sẵn. Ghi lại: lần hỏi đầu tiên trong buổi là "nóng" (đã nạp).
- Mở sẵn Finder ở thư mục môn học và trình duyệt trống, để cách quen thuộc không bị thiệt vì khâu mở máy.
- Đồng hồ bấm giờ, bảng ghi chép bên dưới in sẵn.

## Câu hỏi

Mỗi việc có **hai câu cùng loại**: một câu làm bằng cách quen thuộc, câu kia bằng RAT. Không dùng một câu cho cả hai cách, vì làm lần đầu đã cho biết đáp án nằm ở đâu.

Luật viết câu: viết xong cả sáu câu **trước khi** thử câu nào trên RAT. Nếu thử rồi mới chọn, mình sẽ vô tình giữ lại những câu RAT làm đúng.

Bốn câu V1, V2 viết ngày 19/11/2026 từ slide môn 502044 (`~/Documents/Github/dump/schoolworks/to-chuc-may-tinh/`, 23 file PDF). Đáp án kiểm tra bằng cách đọc chữ trên chính trang đó, **chưa chạy câu nào trên RAT**. V1 dùng đúng thuật ngữ trong slide. V2 cố ý diễn đạt bằng lời của sinh viên, không có từ khoá trong slide, để Cmd-F không thắng chỉ nhờ câu hỏi trùng nguyên văn.

| Việc | Câu | Đáp án (file, trang PDF) |
|---|---|---|
| V1a | Trong slide chương 12 (Pipelining), trang nào liệt kê ba loại pipeline hazard? | `Chapter 12 - Pipelining.pdf`, trang 47 |
| V1b | Trong slide chương 13.1 (Cache Part I), trang nào định nghĩa temporal locality và spatial locality? | `Chapter 13.1 - Cache Part I.pdf`, trang 18 |
| V2a | Slide nào giải thích vì sao tăng tốc một phần của chương trình thì cả chương trình không nhanh lên tương ứng? | `Chapter 8 - Computer Performance.pdf`, trang 25 (chấp nhận 24-27: Amdahl's Law) |
| V2b | Slide nào nói về loại mã mà hai giá trị liền nhau chỉ khác nhau đúng một bit? | `Chapter 1.2 - Number systems and Codes.pdf`, trang 50 (chân slide ghi 56; chấp nhận 50-52: Gray code) |
| V3a, V3b | Do người tham gia đặt (xem 03:00) | Người quan sát kiểm tra tại chỗ |

Độ khó hai câu cùng việc: V1a ở trang 47/99, V1b ở trang 18/76, cả hai đều là slide định nghĩa dạng gạch đầu dòng. V2a và V2b đều nằm trong file mà tên chỉ gợi ý mơ hồ ("Performance", "Codes").

## Diễn tiến 30 phút

| Phút | Việc | Người quan sát nói / làm |
|---|---|---|
| 00-03 | Đồng ý và câu hỏi nền | "Mình đo công cụ, không đo bạn. Bạn có thể dừng bất cứ lúc nào. Mình không ghi tên bạn." Hỏi: (1) Bạn dùng máy gì? (2) Slide và giáo trình các môn bạn để ở đâu? (3) Lần gần nhất bạn cần tìm lại một ý trong slide, bạn làm thế nào? (4) Bạn có dùng ChatGPT / NotebookLM / Gemini cho việc đó không? |
| 03-04 | Lấy câu V3 | "Kể một điều bạn từng phải lục lại trong tài liệu môn này." Biến nó thành hai câu cùng loại. |
| 04-06 | Giới thiệu RAT, đọc nguyên văn | "Nhấn ⌥⇧Space để mở. Gõ câu hỏi như hỏi bạn. Kết quả có số trang; bấm vào để mở đúng trang." Không giải thích thêm. |
| 06-24 | 3 việc × 2 cách, tối đa 3 phút mỗi lần | Đảo thứ tự để không cách nào luôn được làm sau: V1 cách quen trước, V2 RAT trước, V3 cách quen trước. Nhờ họ nói to điều đang nghĩ. Không giúp. Khi họ hỏi, chỉ nói "bạn sẽ làm gì nếu không có mình ở đây?". |
| 24-30 | Hỏi lại | (1) Tuần sau, gặp việc này, bạn sẽ dùng cách nào? Vì sao? (2) Chỗ nào trong RAT làm bạn khựng lại? (3) Nếu RAT cần tải tài liệu lên mạng để trả lời tốt hơn, bạn có đồng ý không? |

## Cách đếm

- **Bước**: mỗi cú nhấp, phím tắt, hoặc lần gửi câu hỏi. Một lượt cuộn liền mạch tính là 1 bước.
- **Chuyển cửa sổ**: mỗi lần đổi app hoặc đổi tab.
- **Thời gian**: từ lúc họ đọc xong câu hỏi đến lúc chỉ vào đúng trang. Người quan sát xác nhận trang theo cột đáp án.
- **Số trang**: tính theo trang PDF (Preview hiển thị số này). Nếu họ chỉ vào số ở chân slide, như "56" cho trang 50 của file Number systems, vẫn tính là đúng, nhưng ghi lại: RAT dẫn theo trang nào thì người dùng phải đối chiếu được với thứ họ nhìn thấy.
- **Kết quả**: đúng trang / sai trang / bỏ cuộc (hết 3 phút). RAT đưa trang sai mà họ tin là đúng thì ghi **sai, tin nhầm**. Lỗi này nặng hơn bỏ cuộc.

## Bảng ghi chép, mỗi buổi một bảng

Người tham gia: P__ (không ghi tên) · Ngày: __ · Máy của họ: __ · Tài liệu môn để ở: __

| Việc | Cách | Câu | Bước | Chuyển cửa sổ | Giây | Kết quả | Ghi chú (chỗ khựng, câu họ nói) |
|---|---|---|---|---|---|---|---|
| V1 | quen | a | | | | | |
| V1 | RAT | b | | | | | |
| V2 | RAT | a | | | | | |
| V2 | quen | b | | | | | |
| V3 | quen | a | | | | | |
| V3 | RAT | b | | | | | |

Muốn dùng tiếp? có / không / chưa chắc · Lý do, nguyên văn: __

## Sau buổi

- Chép bảng vào `experiments/observation/sessions.md` (chỉ mã P__, không tên).
- Mọi lần RAT đưa sai trang: ghi câu hỏi và trang đúng vào bộ câu hỏi đo tìm kiếm, vì phép đo hiện tại (`tools/measure_search_quality.py`, `rat/ROADMAP.md` mục 2.7) chỉ chấm đúng file, chưa chấm đúng trang.
