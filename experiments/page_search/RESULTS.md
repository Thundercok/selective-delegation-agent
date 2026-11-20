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

## Thời gian chờ thêm của `slm_fallback` trên đường hỏi (ghi trước khi đo, 19/11/2026)

Mã đo: `page_window(content, query_terms(q), 3000, question=q, slm_fallback=…)`. Đây đúng là lời gọi mà `expand_document_context` thực hiện khi `answer_selected_document` đọc lại một tài liệu bị cắt. Lần gọi model để trả lời giống nhau ở cả hai cách, nên không tính.

Cách đo:
- **Thời gian thêm** = thời gian khi bật trừ thời gian khi tắt, tính riêng từng câu.
- Bộ nhớ đệm từ khoá được xoá trước mỗi câu.
- Model đã nạp sẵn, vì ngay sau đó lần gọi trả lời cũng dùng `qwen3:4b-instruct`.
- Chữ của file được trích trước, không tính vào thời gian.
- Dùng 20 câu của bộ chỉnh. Phép đo này không chấm độ đúng, nên không cần bộ thẩm định.

| Kết quả | Quyết định |
|---|---|
| Trung vị thời gian thêm không quá 3 s **và** p90 không quá 6 s | GO: giữ `slm_fallback` bật mặc định |
| Trung vị trên 6 s | KILL: tắt mặc định |
| Ở giữa | Giữ bật, nhưng hiện "Đang tìm trang…" trong lúc chờ |

Dự đoán (GIẢ THUYẾT): trung vị dưới 1 s, vì một lần gọi ở Sửa 3 lần 2 mất 0,45 s. Các câu `term` gần như không tốn thêm, vì `has_specific_lexical_match` không gọi model cho chúng.

### Kết quả (`out_time_fallback.txt`, `time_fallback.py`)

Phiên bản đo: `page_match.py` `088dfc714d95…`, `page_keywords.py` `fa2b01c64563…`.

| | Trung vị | p90 | Lâu nhất |
|---|---|---|---|
| Thời gian thêm, cả 20 câu | **0,78 s** | **3,23 s** | 3,64 s |
| Chỉ 10 câu có gọi model | 2,29 s | 3,27 s | 3,64 s |

**So với ngưỡng: GO.** Giữ `slm_fallback` bật mặc định.

Đọc kỹ hơn:
- **Trung vị cả 20 câu thấp là nhờ 10 câu `term` không gọi model**, chỉ tốn thêm dưới 0,02 s. Người hỏi bằng lời của mình sẽ chờ thêm khoảng 1,5-3,6 s.
- **Mỗi lần gọi ở đây chậm hơn nhiều so với 0,45 s đo ở Sửa 3 lần 2**, dù cùng prompt và cùng model. Chưa rõ vì sao. Có thể máy đang sạc ở 20% pin nên chạy chậm lại, hoặc Ollama đang tải thêm việc khác (GIẢ THUYẾT).
- **Ở p05 và p09, model được gọi nhưng vẫn không ra trang nào.** Người dùng chờ thêm khoảng 3,5 s mà không được gì. Hai câu này rơi về cách tìm chuỗi cũ trong `documents.py`.
- **Không có câu `term` nào đổi trang khi bật.**

## Chạy thử cả đường hỏi (ghi trước khi chạy, 19/11/2026)

`dry_run_ask.py` gọi `answer_selected_document` đúng như app (`execution_service.py`):
- `AssistantRuntime` mặc định, trả lời bằng Ollama `qwen3:4b-instruct`;
- `selected_document_path` là file đã chọn.

Ba câu từ bộ chỉnh, chọn theo kiểu lỗi, không dùng V1/V2:

| Câu | Vì sao chọn |
|---|---|
| t04 | TLB, `term`, đúng trang khi chỉ khớp chữ |
| p04 | branch prediction, `paraphrase`, đúng trang sau khi gọi model |
| p05 | set associative, `paraphrase`, gọi model mà vẫn không ra trang |

Ngưỡng:

| Kết quả | Quyết định |
|---|---|
| Cả 3 câu có câu trả lời tiếng Việt, không lỗi, mỗi câu không quá 20 s. Với p05, RAT nói rõ là không thấy, hoặc dẫn đúng trang 9-10. | GO cho buổi quan sát |
| Có câu lỗi, câu trả lời rỗng, mất trên 40 s, hoặc p05 khẳng định một trang sai như thể đúng | Sửa trước khi mời người |
| Ở giữa | Ghi lại, sửa nếu rẻ |

### Kết quả chạy thử (`out_dry_run_ask.txt`)

| Câu | Trang RAT dẫn | Lần 1 | Lần 2 | Lần gọi model trả lời (lần 2) |
|---|---|---|---|---|
| t04 | 11 ✓ | 34,2 s | 21,9 s | 18,4 s, 875 token vào, 73 ra |
| p04 | 85 ✓ | 36,9 s | 10,5 s | 7,3 s |
| p05 | "slide 10" ✓, nhưng xem dưới | 38,4 s | 9,3 s | 6,7 s |

**So với ngưỡng: Ở GIỮA.** Không có lỗi, có câu trả lời tiếng Việt, trang dẫn đều nằm trong trang chấp nhận. Nhưng chưa có lần chạy nào cả 3 câu đều không quá 20 s.

Bốn điều nhận ra:

1. **Gần như toàn bộ thời gian là lần gọi model để trả lời.** Gọi model để dịch từ khoá chỉ mất khoảng 2 s. Câu đầu của mỗi lần chạy chậm nhất. Lần 1 chậm hơn lần 2 khoảng 3 lần, dù cùng code và cùng câu. GIẢ THUYẾT: Ollama nạp lại model (cold start), hoặc máy đang chịu tải khác.
2. **p05 đúng nhờ vị trí của đáp án, không nhờ cách chọn trang.** Model dịch ra "cache coherence, cache line" nên không ra trang nào. `expand_document_context` quay về đầu file (trang 1-11), và đáp án tình cờ nằm ở trang 9-10. Nếu đáp án ở cuối file, RAT sẽ không thấy. Ngưỡng được đặt theo chữ trên câu trả lời, nên câu này vẫn tính là đạt.
3. **p04 chỉ nhắc lại câu hỏi** ("…được nói ở trang 85"), không giải thích gì. Trang đúng, nhưng câu trả lời không có giá trị. Ngưỡng không đo chất lượng câu trả lời; buổi quan sát sẽ đo.
4. **t04 nhắc tới "trang 13 đến 14".** Hai trang này nằm trong đoạn đã đọc (trang 11-18), nhưng chưa kiểm xem nội dung có đúng không.

### Các số đo thời gian bị nhiễm (ghi lúc 17:47, 19/11/2026)

Từ khoảng 17:28, máy (M1, 16 GB) chạy song song một job huấn luyện `mlx_lm lora` trên Qwen3-8B. Job đó không thuộc phép đo này. Lúc kiểm tra:
- swap đã dùng 9,6/10 GB, RAM trống còn 14%;
- `llama-server` của Ollama chỉ còn 1,28/3,8 GB trong RAM.

Thử cùng một lần gọi model trả lời (821 token vào, 120 ra), lúc model chưa nạp và lúc đã nạp:

| | Nạp model | Xử lý prompt | Sinh chữ | Tổng |
|---|---|---|---|---|
| Chưa nạp | 4,7 s / 2,4 s | 19,0 s / 12,0 s | 38,2 s / 16,9 s | 61,9 s / 31,4 s |
| Đã nạp | 0 | 0,2 s / 0,1 s | 29,3 s / 15,6 s | 29,6 s / 15,8 s |

Ở dòng "đã nạp", Ollama dùng lại phần prompt đã xử lý của lần trước. Câu hỏi mới thì không được như vậy, nên xử lý prompt vẫn mất khoảng 12-19 s.

Kết luận:
- **Nạp sẵn model chỉ bỏ được 2-5 s.** Phần chậm chính là sinh chữ, ở 3-8 token/s, dao động gấp đôi giữa các lần chạy. Rất có thể đó là do thiếu RAM (GIẢ THUYẾT mạnh: swap gần đầy và model bị đẩy ra khỏi RAM).
- `out_time_fallback.txt` và `out_dry_run_ask.txt` đều được đo sau 17:28, nên đều đo trong lúc máy đang chịu tải này. Quyết định GO cho `slm_fallback` và mức "ở giữa" của lần chạy thử cần đo lại khi máy không chạy job huấn luyện.

## Đo lại lần chạy thử trên máy rảnh (ghi trước khi chạy, 20/11/2026)

Code: sau `6c313b6`. Với file có trang, khi không tìm ra trang thì RAT nói không tìm thấy, không gọi model. Cùng 3 câu, cùng ngưỡng như mục "Chạy thử cả đường hỏi", không đổi ngưỡng sau khi có số liệu.

- **Máy rảnh nghĩa là:** không còn job huấn luyện nào (`mlx_lm`, `structured_llm`, `run.sh`). Ghi lại swap và RAM trống ngay trước khi chạy.
- **Chạy 2 lần liên tiếp.** "Mỗi câu không quá 20 s" áp dụng cho **mọi câu ở cả hai lần**, kể cả câu đầu của lần 1 (lúc model có thể chưa được nạp). Người dùng ở buổi quan sát cũng gặp câu đầu như vậy.
- **p05 dự kiến trả lời "không tìm thấy".** Theo ngưỡng, như vậy là đạt. Nếu p05 lại dẫn một trang cụ thể thì phải xem vì sao trước khi kết luận.

### Kết quả đo lại (`out_dry_run_ask_idle.txt`, 20/11/2026 03:45)

Trước khi chạy: không còn job huấn luyện, RAM trống 63%, swap vẫn dùng 7,2/8 GB (phần còn lại từ job huấn luyện; macOS không thu swap về ngay). Code `22bdaab`.

| Câu | Trang RAT dẫn | Lần 1 | Lần 2 |
|---|---|---|---|
| t04 | 11 ✓ | 18,8 s | **37,2 s** |
| p04 | 85 ✓ | **34,8 s** | **50,9 s** |
| p05 | "không tìm thấy" ✓ (không gọi model) | 13,6 s | 20,3 s |

**So với ngưỡng: SỬA TRƯỚC KHI MỜI NGƯỜI.** p04 lần 2 mất 50,9 s, quá mốc 40 s. Không có lỗi, cả 3 câu trả lời bằng tiếng Việt, trang dẫn đều đúng, p05 nói rõ là không thấy. Vậy chỉ có thời gian là không đạt.

Đọc kỹ hơn:
1. **Lần 2 chậm hơn lần 1 ở cả 3 câu.** Ngược với giả thuyết cold start ở lần chạy trước (lần 1 chậm vì model chưa nạp). Vậy nạp sẵn model không cứu được.
2. **p05 vẫn mất 13-20 s dù không gọi model trả lời.** Thời gian đó là `read_document` cộng lần gọi model để dịch từ khoá (`slm_fallback`). Lần đo trước, phần dịch chỉ mất khoảng 2-3,6 s. Chưa tách được từng phần.
3. **p04 vẫn chỉ nhắc lại câu hỏi.** Câu trả lời dài một câu mà mất 35-51 s. Nếu thời gian nằm ở lần gọi model, thì phần chậm là xử lý prompt chứ không phải sinh chữ (GIẢ THUYẾT, chưa đo).
4. **Máy chưa thật sự "sạch".** Ngoài Ollama (3,7 GB), lúc đó còn một VM và một app Windows chạy qua lớp giả lập. Định nghĩa "máy rảnh" ở trên chỉ đòi không có job huấn luyện, nên lần đo này vẫn tính. Nhưng không loại được tải khác.

Bước tiếp, trước khi mời người: đo tốc độ của chính Ollama (`prompt_eval_duration`, `eval_duration` trong response của `/api/chat`) cho đúng prompt của p04, để biết 35-51 s nằm ở đâu.

### Lần đo lại lúc 03:45 bị nhiễm: hai client gọi Ollama xen kẽ (ghi 20/11/2026 03:55)

Từ 03:46 đến 03:48, `~/.ollama/logs/server.log` ghi 16 lần `POST /api/chat`. `dry_run_ask.py` (2 lần chạy) chỉ gửi 8 lần. 8 lần còn lại đến từ một script đo khác chạy cùng lúc (`cold_warm.py`, nằm ngoài repo). Script đó không đặt `num_ctx`, nên Ollama dùng mặc định `-c 4096`, còn RAT luôn gửi `num_ctx: 8192` (`rat/engine/slm.py`, `chat_with_meta`).

Mỗi khi `num_ctx` đổi, Ollama tắt llama-server rồi khởi động lại. Trong 12 lần khởi động gần nhất, có 6 lần `-c 4096` và 6 lần `-c 8192`, xen kẽ nhau. Ở các lần gọi "đã nạp" của script kia, `load_duration` lên tới 13-17 s. Vì vậy t04 37,2 s và p04 50,9 s ở `out_dry_run_ask_idle.txt` gồm cả thời gian nạp lại model do client kia gây ra. Kết luận "SỬA TRƯỚC KHI MỜI NGƯỜI" dựa trên lần đo này không dùng được. Ngưỡng giữ nguyên. Chỉ lần đo là phải làm lại.

### Đo lại lần nữa, không có client nào khác (`out_dry_run_ask_clean.txt`, 20/11/2026 03:53)

Cùng code (`4ae0aa1`), cùng 3 câu, cùng ngưỡng, 2 lần chạy liên tiếp. Trước lần 1, model đã được gỡ (`keep_alive: 0`), nên lần 1 bắt đầu từ lúc model chưa nạp. Trước khi chạy: không có job huấn luyện, RAM trống 33%, swap 7,4/8 GB (phần còn lại từ job cũ). Một app Windows chạy qua lớp giả lập vẫn dùng khoảng 100-130% CPU. Log Ollama trong lúc chạy: đúng 8 lần `/api/chat` (khớp số lần RAT gọi), 1 lần khởi động llama-server (lần nạp đầu).

| Câu | Trang RAT dẫn | Lần 1 | Lần 2 |
|---|---|---|---|
| t04 | 11 ✓ | 15,3 s | 7,7 s |
| p04 | 85 ✓ | 14,6 s | 4,2 s |
| p05 | "không tìm thấy" ✓ (không gọi model trả lời) | 1,1 s | 1,0 s |

**So với ngưỡng: GO cho buổi quan sát.** Cả 3 câu trả lời tiếng Việt, không lỗi, mọi câu ở cả hai lần đều dưới 20 s, và p05 nói rõ là không thấy.

Đọc kỹ hơn:
1. **Lần 2 nhanh hơn chủ yếu vì Ollama dùng lại prompt y hệt lần 1.** Người thật sẽ hỏi câu mới, nên lần 1 mới là con số đại diện: khoảng 15 s cho mỗi câu có trả lời.
2. **Thời gian nằm ở đâu** (`cold_warm.py`, cùng `num_ctx` 8192, không có client khác): nạp model 1,0-1,3 s; xử lý prompt 4,4-7,8 s cho 722-1.213 token (khoảng 150 token/s); sinh chữ 10-13 token/s. Nạp sẵn model chỉ bớt được khoảng 1 s trên máy không chịu tải. **Không làm.**
3. **`slm_fallback`** (`out_time_fallback_clean.txt`): trên 20 câu, thời gian chờ thêm trung vị 0,34 s, p90 0,96 s, tối đa 1,30 s. Số đo cũ (0,78 / 3,23 s, đo lúc máy thiếu RAM) đã cho GO; lần này tốt hơn, nên GO vẫn giữ.
4. **p04 vẫn chỉ nhắc lại câu hỏi** ("... được nói ở trang 85."). Trang đúng, nhưng chưa giải thích gì. Đây là vấn đề chất lượng câu trả lời, không phải thời gian. Ngưỡng không bắt lỗi này.

Rủi ro còn lại, chưa đo: trong RAT, `generate_with_meta` và `generate_stream` (`slm.py`) không đặt `num_ctx`, còn `chat_with_meta` đặt 8192. Một đường trong app gọi cả hai kiểu (ví dụ `qa_engine`, `hyde`, `meta_reasoner` dùng `generate`) sẽ khiến model phải nạp lại mỗi lần đổi kiểu gọi. Đường hỏi tài liệu đã chọn chỉ dùng `chat_with_meta`, nên không bị.

### Tách thời gian từng bước (`time_ask_stages.py`, `out_time_ask_stages.txt`, 20/11/2026 04:05)

Đây là lần đo **chẩn đoán**, không ghi trước, nên **không thay** verdict ở trên. Cùng code, cùng 3 câu, khoảng 20 phút sau lần đo lại. Lúc chạy: RAM trống 68%, swap 5,6/7 GB, không có job huấn luyện. Cache từ khoá được xoá trước mỗi câu.

| Câu | Lần 1 | Lần 2 | Lần đo lại lúc 03:45 (lần 1 / lần 2) |
|---|---|---|---|
| t04 | 17,8 s | 5,7 s | 18,8 / 37,2 s |
| p04 | 11,8 s | 3,3 s | 34,8 / 50,9 s |
| p05 | 0,9 s | 1,4 s | 13,6 / 20,3 s |

Ollama tự báo thời gian từng pha. Với lần gọi trả lời ở lần 1:

| Câu | Nạp model | Xử lý prompt | Sinh chữ |
|---|---|---|---|
| t04 | 3,6 s | 5,3 s (875 token, ~165 token/s) | 7,7 s (74 token, ~10 token/s) |
| p04 | 0 | 7,3 s (1316 token, ~180 token/s) | 2,1 s (28 token) |

Đọc:
1. **Lần đo lại lúc 03:45 chậm vì trạng thái máy, không phải vì code** (ỦNG HỘ MẠNH). Cùng code mà nhanh hơn 3-15 lần, và chậm cả ở các bước không gọi model trả lời: p05 lúc đó mất 13-20 s, giờ còn dưới 1,5 s. Lần đo lại bắt đầu chỉ 2 phút sau khi job huấn luyện dừng, lúc macOS có lẽ còn đang kéo dữ liệu từ swap về RAM (GIẢ THUYẾT, chưa đo trực tiếp).
2. **Dịch từ khoá chỉ tốn 0,6-1,2 s.** `read_document` dưới 1,1 s. Gần như toàn bộ thời gian còn lại là lần gọi model trả lời.
3. **Ở lần 2, xử lý prompt gần như bằng 0 (0,08 s)** vì Ollama dùng lại phần đã xử lý của cùng prompt ở lần 1. Người dùng thật hỏi câu mới, nên **lần 1 mới là con số đúng** cho buổi quan sát.
4. **Câu đầu tiên sát ngưỡng:** t04 mất 17,8 s, trong đó 3,6 s là nạp lại model (Ollama đã đẩy model ra sau vài phút không dùng). Biên còn khoảng 2 s.

Hệ quả cho cổng quyết định: không đổi verdict sau khi có số liệu. Phần cần sửa trước khi mời người là **điều kiện chạy**, không phải code. Trước buổi quan sát #1, ghi trước một lần chạy cuối với điều kiện:
- job huấn luyện đã dừng ít nhất 15 phút;
- model được nạp sẵn (một lần gọi khởi động trước khi người dùng hỏi câu đầu);
- cùng 3 câu, cùng ngưỡng ≤ 20 s, chạy 2 lần.

### Ghi chú: hai cách giải thích lần đo lúc 03:45 (ghi 20/11/2026 04:15)

Mục trên giải thích rằng lần đo lại chậm do trạng thái máy, vì swap đang được kéo về RAM. Đó vẫn là GIẢ THUYẾT. Log Ollama có một nguyên nhân thấy trực tiếp (SỰ THẬT, từ `server.log`):
- trong 03:46-03:48 có 16 lần `/api/chat`, còn `dry_run_ask.py` chỉ gửi 8;
- llama-server khởi động lại xen kẽ giữa `-c 4096` và `-c 8192`;
- `load_duration` lên tới 13-17 s.

Cách này cũng giải thích được vì sao p05 mất 13-20 s dù không gọi model trả lời: lần gọi dịch từ khoá của p05 cũng dùng `chat_with_meta` (8192). Nếu ngay trước đó script kia vừa gọi với 4096, Ollama phải nạp lại model. Hai nguyên nhân có thể cùng xảy ra. Nhưng chỉ riêng việc nạp lại model đã đủ giải thích phần thời gian thừa.

Sửa trong code (cùng ngày): `slm.py` có hằng `NUM_CTX = 8192`. `chat_with_meta`, `generate_with_meta`, `generate_stream` và `LLMClient.query_ollama` đều gửi giá trị này. Test `test_every_ollama_request_sends_the_same_context_size` giữ điều đó. Sửa này không đổi đường hỏi tài liệu đã chọn, vì đường đó vốn chỉ dùng 8192. Nó chặn trường hợp hai phần của RAT tự làm Ollama nạp lại model khi gọi xen nhau. Script đo nằm ngoài RAT vẫn cần đặt `num_ctx: 8192`, nếu không sẽ gây lại đúng lỗi này.

## Lần chạy cổng trước buổi quan sát #1 (ghi trước khi chạy, 20/11/2026 09:12)

Điều kiện lấy từ mục "Tách thời gian từng bước", không đổi:
- job huấn luyện đã dừng ít nhất 15 phút (dừng lúc 03:42);
- model được nạp sẵn bằng một lần gọi khởi động qua `SLMEngine.chat_with_meta`;
- cùng 3 câu, chạy 2 lần;
- cùng ngưỡng của mục "Chạy thử cả đường hỏi".

Code `880b940`, đã có `NUM_CTX`.

Thêm một điều kiện để lần chạy được tính, dựa trên `~/.ollama/logs/server.log` trong lúc chạy:
- đúng 9 lần `/api/chat`: 1 lần khởi động và 8 lần của 2 lượt chạy;
- llama-server khởi động nhiều nhất 1 lần, và chỉ ở lần gọi khởi động.

Nếu một trong hai điều trên sai thì lần chạy bị nhiễm và không được tính. Khi đó phải chạy lại.

### Kết quả lần chạy cổng (`out_dry_run_ask_gate.txt`, 20/11/2026 09:11)

Lần chạy được tính. Log ghi đúng 9 lần `/api/chat`. llama-server chỉ khởi động 1 lần, ở lần gọi khởi động (mất 3,5 s), sau đó không khởi động lại lần nào. Lúc chạy: RAM trống 77%, swap 4,4/6 GB, không có job huấn luyện, app Windows đã tắt.

| Câu | Trang RAT dẫn | Lần 1 | Lần 2 |
|---|---|---|---|
| t04 | 11 ✓ | 8,6 s | 4,4 s |
| p04 | 85 ✓ | 9,7 s | 2,5 s |
| p05 | "không tìm thấy" ✓ | 0,7 s | 0,7 s |

**So với ngưỡng: GO cho buổi quan sát #1.** Cả 3 câu trả lời tiếng Việt, không lỗi, mọi câu dưới 20 s, p05 nói rõ là không thấy.

Còn lại, ngưỡng này không đo:
- **p04 chỉ nhắc lại câu hỏi.** Trang dẫn đúng, nhưng câu trả lời không có nội dung nào từ slide. Buổi quan sát sẽ cho biết sinh viên có coi như vậy là đủ không, vì họ còn mở trang 85 ra xem được.
- **Thời gian là của model đã nạp sẵn.** Ollama gỡ model sau 5 phút không dùng. Trong buổi quan sát, gọi khởi động ngay trước câu đầu, nếu không câu đầu sẽ mất thêm khoảng 1-4 s.
