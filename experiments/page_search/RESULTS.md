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

### Bộ thẩm định (viết 19/11/2026, trước mọi lần chạy phần theo nghĩa)

`questions_502044_holdout.json`: 10 câu (5 `term`, 5 `paraphrase`) trên 6 file. Bốn file trong số đó (9.2, 9.3, 11.1, 11.2) chưa có câu nào trong bộ chỉnh. Hai file còn lại (Ch2, Ch6) có câu trong bộ chỉnh, nhưng câu mới hỏi khái niệm khác: duality, flip-flop, J-K. Không câu nào hỏi lại khái niệm của bộ 20 câu hay của V1/V2. Mỗi đáp án đã đối chiếu với chữ trích ra từ trang PDF (pypdf). Số trang là trang PDF, không phải số in trên slide.

Câu `paraphrase` chỉ dùng tiếng Việt thường, không dùng thuật ngữ trên slide. Câu `term` giữ đúng thuật ngữ của slide.

Quy tắc: bộ này chạy **đúng một lần**, sau khi bộ chỉnh đã cho kết quả và mã chọn trang đã chốt. Không sửa câu, không sửa trang chấp nhận, không sửa mã sau khi thấy kết quả của bộ này. Nếu phải sửa mã sau lần chạy đó, cần viết một bộ thẩm định mới.

### Kết quả Sửa 2 (19/11/2026)

**Thứ tự sự việc.** Người sửa `page_match.py` đã chạy bản có phần theo nghĩa trên cả bộ chỉnh và bộ thẩm định. Kết quả nằm trong `out_fix2_pages_only.txt` và `out_fix2_holdout_pages_only.txt`, cả hai file đều ghi giờ sửa 14:19. Sau đó họ gỡ phần theo nghĩa. Lúc 16:48, `page_match.py` (sha256 `92e7b9f286c6…`) không còn `semantic_fallback` ở đâu trong `rat/`, `tools/`, `tests/`, và `documents.py` cùng tool đã quay về bản commit. Không có hash của bản có phần theo nghĩa, nên không chạy lại được đúng bản đó.

| | Sửa 1 | Theo nghĩa, bộ chỉnh | Theo nghĩa, **bộ thẩm định** | Chỉ khớp chữ (bản hiện tại), bộ chỉnh |
|---|---|---|---|---|
| Tất cả | 7/20 | 15/20 | **4/10** | 10/20 |
| `term` | 7/10 | 10/10 | 3/5 | 10/10 |
| `paraphrase` | 0/10 | 5/10 | 1/5 | 0/10 |

Bản chỉ khớp chữ: `out_fix2_lexical_pages_only.txt`, 3,6 s cho cả 20 câu.

**So với ngưỡng đã ghi trước:**

- Bộ chỉnh đạt điều kiện GO về độ đúng: `paraphrase` 5/10 (cần ít nhất 4), `term` 10/10 (cần ít nhất 7). Thời gian trên Pipelining **chưa đo**.
- Bộ thẩm định đạt 40%, bộ chỉnh 75%. Quy về 10 câu, đó là 4 so với 7,5, thấp hơn 3,5 câu. Ngưỡng là 3, nên theo quy tắc đã ghi: **cách chọn trang khớp theo bộ chỉnh, không phải theo nghĩa.** Từng loại cũng thấp hơn: `term` 6/10 so với 10/10, `paraphrase` 2/10 so với 5/10.
- Bộ thẩm định đã dùng. Bất kỳ thay đổi nào sau đây cần một bộ thẩm định mới.

**Kết quả này mong manh.** Ghi lại, nhưng không đổi kết luận:

- Mẫu nhỏ: chỉ 5 câu mỗi loại.
- h_t5 (PC-relative) chọn trang 23, là trang mở đầu mục "PC-Relative Addressing (1/5)". Trang chấp nhận đã ghi trước là 25-26, nơi có công thức. Nếu tính trang 23 là đúng, bộ thẩm định thành 5/10 và khoảng cách còn 2,5, dưới ngưỡng. Không đổi trang chấp nhận sau khi đã thấy kết quả.
- Lỗi bộ thẩm định cho thấy hai kiểu sai:
  - Luật "khi bằng điểm thì chọn trang sớm hơn" đưa về trang mở đầu mục (h_t5).
  - Khớp chữ ăn vào phần khác cùng từ khoá: h_t3 "I-format… 32 bit… trường" chọn trang 34, là J-Format (3/5), cũng nói về 32 bit.
  - Bốn câu `paraphrase` sai đều rơi vào trang khác hẳn.

**Quyết định theo ngưỡng: chưa GO cho buổi quan sát dựa trên phần chọn trang.** Hai hướng còn lại theo bảng Sửa 2:

1. Để LLM đổi câu hỏi thành từ khoá tiếng Anh trước khi chọn trang (hướng KILL đã ghi).
2. Chấp nhận RAT mở đúng file và đúng mục, rồi người dùng tự lật vài trang. Hướng này phải đo bằng thời gian ở buổi quan sát, không đo bằng "đúng trang".

## Sửa 3: model viết từ khoá tiếng Anh trước khi chọn trang (ghi trước khi đo, 19/11/2026)

**Bối cảnh.** Đường hỏi của hero job A (`answer_selected_document`, `rat/engine/selected_document_qa.py`) chọn trang bằng `query_terms(goal)`, tức là lấy từ ngay trong câu hỏi, rồi gọi model **một lần** để trả lời. Câu `paraphrase` tiếng Việt không có từ nào trùng với slide tiếng Anh, nên khớp chữ được 0/10.

**Thay đổi.** Trước khi chọn trang, gọi model cục bộ (`qwen3:4b-instruct` qua Ollama, `thinking=False`, temperature 0,1) **thêm một lần nữa** để viết vài từ khoá tiếng Anh như trên slide. Ghép các từ đó với từ của câu hỏi rồi chọn trang bằng `page_match.best_page` như cũ. Nếu model lỗi, dùng câu hỏi như cũ. `page_match.py` giữ nguyên.

**Ngưỡng trên bộ chỉnh (20 câu):**

| Kết quả | Quyết định |
|---|---|
| `paraphrase` từ 6/10 trở lên, `term` từ 9/10 trở lên, trung vị thời gian của lần gọi thêm không quá 3 s (model đã nạp) | GO, chuyển sang bộ thẩm định |
| `paraphrase` dưới 4/10, hoặc trung vị trên 6 s | KILL; chọn hướng "đúng file, đúng mục, người dùng tự lật trang" |
| Ở giữa | ITERATE: được sửa câu lệnh cho model trên bộ chỉnh |

**Bộ thẩm định thứ hai.** `questions_502044_holdout2_sua3.json`, 10 câu (5 `term`, 5 `paraphrase`), viết **trước khi có dòng mã nào** của Sửa 3. Khái niệm không trùng bộ chỉnh, bộ thẩm định thứ nhất hay V1/V2. Đáp án đã đối chiếu với chữ trên trang PDF. Bộ thẩm định thứ nhất đã dùng ở Sửa 2, nên không dùng lại.

Chạy bộ thứ hai **một lần**, sau khi câu lệnh và mã đã chốt, kèm sha256 của file mã. Hai điều kiện để GO cho buổi quan sát:

- quy về 10 câu, bộ thẩm định không thấp hơn bộ chỉnh từ 3 câu trở lên (cùng quy tắc với Sửa 2);
- `paraphrase` trên bộ thẩm định đạt ít nhất 3/5.

Không đạt thì kết luận là cách này khớp theo bộ chỉnh.

**Dự đoán (GIẢ THUYẾT):** `paraphrase` 4-7/10 trên bộ chỉnh. Model 4B biết thuật ngữ kiến trúc máy tính phổ biến ("TLB", "set associative", "De Morgan"), nhưng có thể viết từ khoá chung chung ("memory", "circuit"). Những từ đó lặp lại trên nhiều trang và kéo trang chọn về đầu mục. Câu g_p5 (trang 16 Ch1.1, gần như chỉ có hình) gần như chắc chắn sai với mọi cách khớp chữ.

Ghi chú: `questions_502044_holdout2.json` ban đầu chứa đúng bộ câu này. Trong lúc chạy bộ chỉnh, một người khác đã ghi đè file đó bằng 10 câu khác (id `h2_*`). Bộ gốc được chép nguyên văn sang `questions_502044_holdout2_sua3.json`. File `holdout2.json` mới không phải của người viết mục này và không được dùng để chấm Sửa 3.

### Kết quả Sửa 3, lần 1 (bộ chỉnh)

`page_keywords.py` sha256 `0935cbf09d89…`, `page_match.py` `92e7b9f286c6…`. Kết quả ở `out_fix3_keywords_pages_only.txt`.

| | Chỉ khớp chữ | Ghép tối đa 6 từ khoá của model |
|---|---|---|
| Tất cả | 10/20 | 11/20 |
| `term` | 10/10 | 7/10 |
| `paraphrase` | 0/10 | 4/10 |
| Trung vị lần gọi thêm | 0 | 1,29 s |

So với ngưỡng: **ITERATE**. `paraphrase` 4/10 chưa tới 6, nhưng chưa dưới 4. `term` 7/10 dưới 9.

**Ba kiểu sai:**

1. **Từ khoá chung kéo sai trang.** "binary addition, carry propagation" kéo câu full adder sang trang 33. Ba câu `term` tụt vì kiểu này.
2. **Model không biết đúng khái niệm.** Bộ nhớ "vài chỗ cố định trong một nhóm" thành "cache, cache line" thay vì "set associative". Mạch đi vòng qua chuỗi trạng thái thành "state machine" thay vì "counter".
3. **Đúng từ nhưng sai trang.** "De Morgan's law" chọn trang 13. "page table" chọn trang 4.

**Thử offline trên chính các từ khoá đó.** Không gọi thêm model, `best_page` là Python thuần:

| Cách ghép | `term` | `paraphrase` |
|---|---|---|
| Ghép 1, 2 hoặc 3 từ đầu vào câu hỏi | 7-8/10 | 3-4/10 |
| Chỉ gọi model khi câu hỏi tự nó không khớp trang nào, ghép 2 từ đầu | **10/10** | **4/10** |

Cách "chỉ gọi khi khớp chữ thất bại" giữ nguyên `term` và bỏ được lần gọi model cho những câu đã có thuật ngữ. Dù vậy `paraphrase` vẫn kẹt ở 4/10. Kiểu sai 2 và 3 không sửa được bằng cách ghép từ.

### Sửa 3, lần 2: lần sửa cuối (ghi trước khi chạy)

Thay đổi: prompt chỉ xin **tối đa 2 thuật ngữ, cụ thể nhất trước**, và giữ tối đa 2. Model **chỉ được gọi khi câu hỏi tự nó không khớp trang nào**. Ngưỡng giữ nguyên như trên.

Đây là lần sửa cuối trên bộ chỉnh:
- **ITERATE hoặc KILL:** không sửa nữa, chọn hướng "đúng file, đúng mục, người dùng tự lật trang".
- **GO:** chạy `questions_502044_holdout2_sua3.json` một lần.

Thời gian tính theo trung vị của các lần gọi model, chỉ ở những câu có gọi.

### Kết quả Sửa 3, lần 2 và Bộ thẩm định `questions_502044_holdout2_sua3.json`

Mã chốt trước khi chạy:
- `rat/engine/page_match.py`: sha256 `088dfc714d9530809cc17ff4674352cde59d379bc2972dfea0edd97d18bda772`
- `rat/engine/page_keywords.py`: sha256 `fa2b01c645634f3870881f75ed74ee941e623833ba73df1f24cb17bb66e85482`

Kết quả chạy trên bộ chỉnh (`out_fix3_tuning_settled.txt`) và chạy một lần trên bộ thẩm định `questions_502044_holdout2_sua3.json` (`out_fix3_holdout2_sua3_pages_only.txt`; kèm thêm kết quả trên bộ phụ `holdout2` ở `out_fix3_holdout2_pages_only.txt`):

| | Bộ chỉnh (20 câu) | **Bộ thẩm định `holdout2_sua3` (10 câu, chạy 1 lần)** | Bộ phụ `holdout2` (`h2_*`, 10 câu) |
|---|---|---|---|
| Tất cả | **15/20 (75%)** | **6/10 (60%)** | 8/10 (80%) |
| `term` | 10/10 (100%) | 4/5 (80%) | 5/5 (100%) |
| `paraphrase` | **5/10 (50%)** | **2/5 (40%)** | 3/5 (60%) |

**Quyết định theo đúng luật đã ghi ở mục "lần sửa cuối":**
- Trên bộ chỉnh, `paraphrase` đạt **5/10** (nằm ở mức ITERATE `4-5/10`, chưa chạm ngưỡng GO `6/10`); trên `holdout2_sua3`, `paraphrase` đạt **2/5** (chưa chạm `3/5`, trong khi tổng điểm 6/10 cách bộ chỉnh 1,5 câu < 3 câu).
- Vì đây là lần sửa cuối trên bộ chỉnh: **không sửa thêm luật chọn trang nữa**; chốt giữ cơ chế chỉ gọi model khi khớp chữ đặc trưng thất bại (giữ `term` ở 10/10 với 0 ms gọi model, nâng `paraphrase` từ 0/10 lên 50%) và chuyển sang bước quan sát thực tế với sinh viên theo hướng **"mở đúng file, đúng mục (hoặc đúng trang ở ~60–75% câu), đo thời gian thực tế người dùng tìm thấy đáp án"**.

### Kết quả Sửa 3, lần 2 (bộ chỉnh)

Phiên bản đã đo, theo sha256:
- `page_keywords.py`: `fa2b01c64563…`
- `page_match.py`: `088dfc714d95…`. Người khác vẫn đang sửa file này; lần đo dùng `best_page` không có `slm_fallback` của họ.
- `tools/measure_search_quality.py`: `a15670503025…`

Kết quả ở `out_fix3b_keywords_pages_only.txt`.

| | Chỉ khớp chữ | Lần 1 | **Lần 2** |
|---|---|---|---|
| Tất cả | 10/20 | 11/20 | **14/20** |
| `term` | 10/10 | 7/10 | **10/10** |
| `paraphrase` | 0/10 | 4/10 | **4/10** |
| Số câu có gọi model | 0 | 20 | 9 |
| Trung vị một lần gọi | 0 | 1,29 s | 0,45 s |

**So với ngưỡng: ITERATE.** `paraphrase` 4/10 chưa tới 6. Theo điều đã ghi trước lần chạy, đây là lần sửa cuối: **không sửa prompt nữa, không chạy bộ thẩm định**. `questions_502044_holdout2_sua3.json` vẫn còn nguyên để dùng sau.

**Sáu câu `paraphrase` còn sai:**

| Kiểu sai | Câu |
|---|---|
| Model nói sai khái niệm | Set associative ra "cache coherence, cache line". Demultiplexer ra "multiplexer". Counter ra "finite state machine". |
| Model nói đúng, `page_match` chọn sai trang | "De Morgan's law" ra trang 13. "addressing mode" ra trang 12. |
| Không gọi model | BCD: câu hỏi tự khớp được trang 3 bằng chữ "thập phân"/"bit", nên model không được gọi. |

**Kết luận.** Hướng này đáng giữ: `term` không mất câu nào, và một lần gọi tốn dưới nửa giây. Nhưng với model 4B, nó chưa đủ để chọn đúng trang cho câu hỏi diễn đạt lại. Theo bảng Sửa 2, việc tiếp theo là hướng "đúng file, đúng mục, người dùng tự lật trang", đo bằng thời gian trong buổi quan sát.

### Bản `slm_fallback` trong `page_match.py` (người sửa khác, ghi lại lúc nhận code, 19/11/2026)

Song song với `page_keywords.py`, người sửa khác làm cùng ý tưởng ngay trong `page_match.best_page`:
- `translate_query_terms_slm` gọi `qwen3:4b-instruct`, `max_tokens=20`, có bộ nhớ đệm;
- `has_specific_lexical_match` quyết định khi nào gọi model;
- **bật mặc định trên đường hỏi thật**: `documents.py` truyền `slm_fallback=True` vào `page_window`, và `selected_document_qa.py` truyền cả câu hỏi thay vì 6 từ đầu.

Kết quả họ để lại:

| File | Bộ | Đúng | `term` | `paraphrase` |
|---|---|---|---|---|
| `out_fix3_tuning_settled.txt` (17:14) | chỉnh | 15/20 | 10/10 | 5/10 |
| `out_fix3_holdout2_pages_only.txt` (17:07) | `holdout2.json` của họ | 8/10 | 5/5 | 3/5 |
| `out_fix3_holdout2_sua3_pages_only.txt` (17:15) | `holdout2_sua3` | **6/10** | 4/5 | **2/5** |

Đọc kết quả theo quy tắc Sửa 3:
- **Khoảng cách đạt.** Quy về 10 câu, bộ chỉnh 7,5, `holdout2_sua3` 6: thấp hơn 1,5, dưới ngưỡng 3.
- **`paraphrase` không đạt.** Trên thẩm định là 2/5, dưới mức 3/5. Vì vậy **chưa GO cho buổi quan sát**.
- **Bộ chỉnh chưa tới GO.** `paraphrase` 5/10 dưới 6/10.

Ba điểm làm giảm độ tin của bản này:
1. Ví dụ trong prompt ('word alignment byte address', 'duality theorem boolean', 'edge-triggered flip-flop clock') là đáp án của h_p1, h_p4, h_p3 trong bộ thẩm định thứ nhất.
2. `holdout2.json` của họ được viết trong lúc đang chỉnh, và cặp `term`/`paraphrase` hỏi cùng khái niệm (LRU, Memory Wall). 8/10 trên bộ đó không tính là thẩm định.
3. `holdout2_sua3` đã dùng cho bản của họ, nên **không còn bộ thẩm định sạch nào**. Mọi thay đổi tiếp theo cần bộ mới, và nên do một người chưa thấy slide viết, ví dụ sinh viên trong buổi quan sát.

Chi phí trên đường hỏi thật chưa đo. Mỗi câu hỏi không khớp chữ cụ thể sẽ thêm một lần gọi model trước khi trả lời. Như vậy `answer_selected_document` không còn là "đúng một lần gọi".
