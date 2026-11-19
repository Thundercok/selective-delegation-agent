# Đo tìm đúng trang (hero job A)

Hero job A hứa trả lời kèm số trang. Phép đo cũ (`tools/measure_search_quality.py`, `rat/ROADMAP.md` 2.7) chỉ chấm đúng file. Thí nghiệm này chấm đúng trang.

## Bộ câu hỏi

`questions_502044.json`: 20 câu trên slide môn 502044 (`~/Documents/Github/dump/schoolworks/to-chuc-may-tinh/`, 23 PDF). Viết ngày 19/11/2026. Đáp án (file, các trang chấp nhận) kiểm tra bằng cách đọc chữ trên chính trang đó (pypdf), **trước khi chạy câu nào trên RAT**.

- `term` (10 câu): câu tiếng Việt chứa đúng thuật ngữ tiếng Anh trong slide.
- `paraphrase` (10 câu): câu tiếng Việt không có từ nào của slide, như sinh viên hay hỏi.
- Không dùng 4 câu V1/V2 của `docs/observation_script_hero_a.md` và không dùng khái niệm của chúng (pipeline hazard, locality, Amdahl, Gray code). Đó là bộ giữ riêng cho buổi quan sát; không chỉnh RAT theo chúng.
- Số trang là số trang PDF, tính từ 1.

## Hai tầng đo

1. **Đúng file**: file đúng nằm trong 3 kết quả đầu của `SemanticIndex.search` (đường tìm theo nghĩa của desk). Cần mô hình embedding và chỉ mục, nên chỉ chạy khi máy cắm sạc.
2. **Đúng trang khi đã có đúng file**: `page_match.best_page(extract_document_content(file), query_terms(câu))` trả về một trang nằm trong danh sách chấp nhận. Đây đúng là đường `expand_context` dùng khi được đưa câu hỏi (`rat/kernel/capabilities/documents.py`). Chạy bằng Python thuần, không cần mô hình.

**Chỉ số quyết định** (đúng trang trong 3 kết quả đầu): đúng file ở tầng 1 **và** đúng trang ở tầng 2. Vì vế này luôn nhỏ hơn hoặc bằng tầng 2, nếu chỉ riêng tầng 2 đã dưới ngưỡng "sửa trước" thì kết luận được ngay, không cần tầng 1.

## Ngưỡng, ghi trước khi chạy (19/11/2026)

| Kết quả | Quyết định |
|---|---|
| Đúng trang trong 3 kết quả đầu ở từ 14/20 câu, và ở từ 6/10 câu `paraphrase` | GO: chạy buổi quan sát như kịch bản |
| Dưới 10/20 câu, hoặc dưới 4/10 câu `paraphrase` | Sửa phần tìm trang trước, rồi mới quan sát |
| Ở giữa | Vẫn quan sát, ghi trước nguy cơ lỗi sai trang |

## Dự đoán, ghi trước khi chạy

Đọc code thấy hai giới hạn (THỰC TẾ, chưa đo tác động):

- Trên macOS, `extract_document_content` đọc PDF bằng `read_pdf_native(max_pages=25)` (`rat/crawler/extractors.py:21`): chỉ 25 trang đầu. 7/20 đáp án nằm sau trang 25 (t06, t07, t09, p04, p07, p08, p09).
- `SemanticIndex` chỉ nhúng 3 trang đầu mỗi PDF (`rat/engine/semantic_index.py:82`, `max_pages=3`). Không đáp án nào nằm trong 3 trang đầu; tầng 1 chỉ có thể đúng nhờ tên file hoặc trang mục lục.

Dự đoán (GIẢ THUYẾT):

- Tầng 2: tối đa 13/20, vì 7 câu không thể đúng do giới hạn 25 trang.
- Tầng 2, `paraphrase`: 0-2/10. `best_page` so từ theo nghĩa đen, và câu tiếng Việt không chung từ nào với slide tiếng Anh.
- Nếu `paraphrase` ở tầng 2 đạt từ 4/10, thì dự đoán thứ hai sai, và cách chọn trang hiểu nghĩa tốt hơn mình nghĩ.

## Kết quả tầng 2, 19/11/2026

Lệnh (không cần mô hình, khoảng 7 giây):

```bash
uv run python tools/measure_search_quality.py --questions experiments/page_search/questions_502044.json --files ~/Documents/Github/dump/schoolworks/to-chuc-may-tinh --pages-only
```

Đầu ra đầy đủ: `out_pages_only.txt`.

| Bộ | Đúng trang khi đã có đúng file |
|---|---|
| `term` | 4/10 |
| `paraphrase` | 0/10 |
| Tổng | **4/20** |

**Quyết định: sửa phần tìm trang trước, rồi mới quan sát.** 4/20 dưới ngưỡng 10/20, và 0/10 dưới ngưỡng 4/10. Chỉ số quyết định không thể cao hơn tầng 2, nên không cần chạy tầng 1 để kết luận.

Hai dự đoán đều đúng: tầng 2 không vượt 13/20, và `paraphrase` đạt 0-2/10.

### Vì sao sai, theo từng câu

| Nguyên nhân | Câu | Bằng chứng |
|---|---|---|
| Chỉ đọc 25 trang đầu | t06, t07, t09, p04, p07, p08, p09 (7) | File Combinational có 53 trang, `split_pages` chỉ thấy 25. Đáp án trang 30-84 không thể được chọn |
| Trang nhắc từ nhiều nhất thắng trang giới thiệu nó | t03, t04, t10 (3) | Cùng một tập từ khớp trên nhiều trang thì `best_page` xếp theo tổng số lần xuất hiện. Half adder: trang 15 có "adder" 4 lần, trang 9 (trang thiết kế) có 3. TLB: trang 14 có 5 lần, trang 11 (định nghĩa) có 2. Full adder: trang 22 thắng vì khớp thêm từ "bit" |
| Câu tiếng Việt, slide tiếng Anh | cả 10 câu `paraphrase` | Không có từ chung. 5 câu không chọn được trang nào; 5 câu chọn trang chỉ vì trùng ngẫu nhiên |

Câu tiếng Việt còn đưa những từ như "nằm", "slide", "thiết", "cộng" vào `query_terms`, vì chúng không có trong `STOPWORDS`. Với slide tiếng Anh chúng vô hại. Với tài liệu tiếng Việt chúng sẽ thành nhiễu; chưa đo.

### Giới hạn của phép đo

- 20 câu, do một người viết, người này đã đọc slide (mình). Câu `term` dễ hơn thực tế, vì chúng dùng đúng chữ của slide.
- Danh sách trang chấp nhận chỉ gồm trang giới thiệu hoặc định nghĩa khái niệm. Trang 15 (dùng half adder để ghép full adder) bị tính là sai cho câu "thiết kế half adder". Đó là một phán đoán, nhưng sinh viên hỏi câu đó cần trang 9.
- Tầng 1 (đúng file) chưa chạy.
- Đây là đường `expand_context` khi được đưa nguyên câu hỏi. Mô hình trong desk có thể tự rút từ khoá rồi gọi `search_pages`. Đường đó chưa đo.

## Sửa 1: bỏ giới hạn 25 trang (ghi trước khi sửa, 19/11/2026)

Thay đổi: `extract_text_from_pdf_native` truyền `max_pages=None`. Đường native khi đó giống đường dự phòng `read_pdf`: không giới hạn số trang, chỉ giới hạn `MAX_CHARS_PER_DOC = 100_000` ký tự. Con số 25 là giá trị mặc định trong chữ ký của cả `extract_text_from_pdf_native` (`extractors.py:21`) lẫn `read_pdf_native`; không nơi gọi nào truyền số khác, và không có ghi chú lý do. Đường dự phòng chưa bao giờ có giới hạn này.

Chi phí trước khi sửa, đo sau khi đã nạp PDFKit (lần gọi đầu mất thêm khoảng 4 giây để nạp): `Chapter 12 - Pipelining.pdf` mất 0,21 giây, đọc 25 trang, 7.244 ký tự. Slide dài nhất (99 trang, khoảng 30k ký tự theo pypdf) vẫn dưới giới hạn ký tự.

Dự đoán (GIẢ THUYẾT):

- `term` tăng từ 4/10 lên tối đa 7/10. t06, t07, t09 sẽ đọc tới được, nhưng có thể vẫn sai vì nguyên nhân "trang nhắc nhiều nhất thắng".
- `paraphrase` vẫn 0/10. p04, p07, p08, p09 đọc tới được nhưng vẫn không có từ chung với câu hỏi.

Giữ thay đổi nếu: tầng 2 tăng, không câu nào đang đúng thành sai, test liên quan đều đạt, Pipelining (99 trang) đọc dưới 1 giây và sách Epp (dạng chữ, dừng ở giới hạn ký tự) dưới 5 giây.
Bỏ thay đổi nếu: một câu đang đúng thành sai, hoặc đọc sách Epp mất trên 10 giây.

### Kết quả sửa 1

Đầu ra: `out_fix1_pages_only.txt`.

| Bộ | Trước | Sau |
|---|---|---|
| `term` | 4/10 | **7/10** |
| `paraphrase` | 0/10 | 0/10 |
| Tổng | 4/20 | **7/20** |

**Giữ thay đổi.** Mọi điều kiện giữ đều đạt:

- Tầng 2 tăng từ 4 lên 7. Không câu nào đang đúng thành sai: t01, t02, t05, t08 vẫn đúng.
- t06 (trang 69), t07 (trang 30), t09 (trang 31) giờ đúng.
- t10 đổi từ trang 22 sang trang 34, vẫn sai; nguyên nhân "trang nhắc nhiều nhất thắng".
- Thời gian đọc, đo sau khi đã nạp PDFKit: Pipelining (99 trang) 0,75 giây, dưới ngưỡng 1 giây. Sách Epp 2,67 giây, dưới ngưỡng 5 giây.
- Test: `tests/test_pdf_extract_all_pages.py` là test mới. Nó đạt khi có bản sửa và trượt khi bỏ bản sửa. 234 test về chỉ mục, tài liệu, trang và tìm kiếm đều đạt.
- Toàn bộ bộ test: 1513 đạt, 1 hỏng. Test hỏng là `test_quick_answer_presentation::test_answer_copy_and_source_page_journey`, phép so vị trí cửa sổ trong QML. Nó cũng hỏng khi bỏ bản sửa: 4 lần hỏng trên 12 lần chạy, so với 7/12 khi có bản sửa. PDF của test chỉ có 3 trang, nên bản sửa không làm đường đi của test thay đổi.

Cả hai dự đoán đều đúng: `term` lên đúng mức trần 7/10, và `paraphrase` vẫn 0/10.

Vẫn dưới ngưỡng "sửa trước" (7/20 < 10/20; `paraphrase` 0/10 < 4/10). **Chưa được chạy buổi quan sát.**

### Giới hạn còn lại và tác dụng phụ

- **Giới hạn ký tự là bức tường tiếp theo** với giáo trình. Sách Epp dừng ở trang 42 và giáo trình Kinh tế chính trị dừng ở trang 69, cả hai đều chạm `MAX_CHARS_PER_DOC = 100_000`. Slide môn này không bị ảnh hưởng (dài nhất khoảng 33k ký tự).
- **Bản sửa đến ngay ở đường hỏi tài liệu.** `expand_context` và `handle_read` đọc lại file mỗi lần, nên nhận bản sửa ngay.
- **Chỉ mục từ khoá không tự cập nhật.** Indexer bỏ qua file có `modified_at` và kích thước không đổi (`rat/crawler/indexer.py:148`), nên PDF đã đánh chỉ mục vẫn giữ nội dung 25 trang cho đến khi đánh lại với `force`.
- **File scan có thể chậm hơn.** OCR trên luồng chính (`read_pdf_native`, chỉ khi gọi từ luồng chính) giờ có thể chạy quá 25 trang, chỉ dừng ở giới hạn ký tự. Chưa đo.

## Sửa 2: chọn trang theo nghĩa (ghi trước khi đo, 19/11/2026)

Lúc ghi mục này, đã có một thay đổi **chưa commit, không phải của người viết mục này** trong `rat/engine/page_match.py`. Nó làm ba việc:

1. Nếu khớp chữ yếu, nhúng từng trang bằng `paraphrase-multilingual-MiniLM-L12-v2` rồi chọn trang gần câu hỏi nhất (`semantic_fallback`). Trang 1 và trang mục lục bị trừ 0,15.
2. Khi tổng IDF bằng nhau, ưu tiên trang có từ khoá ở tiêu đề, rồi đến trang sớm hơn.
3. Thêm "slide", "nằm", "nói", "chương"… vào `STOPWORDS` và đếm cả dạng số nhiều ("adders").

`tools/measure_search_quality.py` cũng đã được sửa để gọi `semantic_fallback=True`. **Chưa ai chạy phép đo trên thay đổi này**: chưa có file `out_*` mới.

Có hai rủi ro khiến kết quả trên bộ 20 câu dễ đẹp hơn thực tế. Những từ mới thêm vào `STOPWORDS` lấy đúng từ cách đặt câu của bộ này. Luật tiêu đề cũng nhắm vào đúng t03, t04, t10. Vì vậy bộ 20 câu giờ là bộ **chỉnh**, không còn là bộ **thẩm định**. Kết quả thẩm định phải đến từ 4 câu V1/V2 (buổi quan sát), hoặc từ một bộ câu mới viết sau khi thay đổi này đã chốt.

Ngưỡng:

| Kết quả trên bộ 20 câu | Quyết định |
|---|---|
| `paraphrase` từ 4/10, `term` không dưới 7/10, chọn trang cho Pipelining (99 trang) dưới 2 giây sau khi mô hình đã nạp | GO cho cách chọn theo nghĩa |
| `paraphrase` dưới 2/10, hoặc trên 5 giây mỗi câu | KILL cách này, chuyển sang để LLM dịch câu hỏi thành từ khoá |
| Ở giữa | ITERATE |

Thêm một điều kiện, vì 20 câu này đã thành bộ chỉnh: trước khi gọi là GO cho buổi quan sát, viết **10 câu mới** (5 `term`, 5 `paraphrase`) trên những slide chưa dùng, kiểm tra đáp án bằng chữ trên trang, rồi chạy **một lần**. Nếu bộ mới thấp hơn bộ chỉnh từ 3 câu trở lên (tính theo tỉ lệ), thì cách chọn trang đang khớp theo bộ chỉnh chứ không phải theo nghĩa.

Dự đoán (GIẢ THUYẾT): `paraphrase` lên 4-7/10. Mô hình đa ngôn ngữ nối được câu tiếng Việt với slide tiếng Anh, nhưng nhiều slide chỉ có hình nên chữ trích ra rất ít. Chi phí là chỗ chưa chắc nhất: mỗi câu hỏi nhúng lại toàn bộ trang của file, không có bộ nhớ đệm.
