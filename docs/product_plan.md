# Kế hoạch sản phẩm: RAT (Selective Delegation Agent)

**Cập nhật:** 14/11/2026

Các mục ghi `[CẦN ĐIỀN]` chưa có dữ liệu. Không điền bằng số phỏng đoán.

---

## 1. Bản quyền và dọn dẹp trước khi phát hành

- [x] `_archive_book/` (sách Molnar) và `work/` không còn trong cây hiện tại lẫn lịch sử git local (kiểm tra 16/11/2026, `git log --all` trống).
- [ ] Bản cache các commit cũ trên GitHub vẫn có thể còn: chủ repo phải tự gửi yêu cầu xoá cho GitHub Support.
- [x] Đã gỡ bỏ hoàn toàn tính năng lá số (`rat/astrology/`) và phụ thuộc `pyswisseph` (AGPL) khỏi bản phân phối (quyết định 17/11/2026). RAT tập trung đúng định vị cốt lõi: tìm tệp, đọc PDF, hỏi đáp học tập, dịch thuật và thời khóa biểu.
- [x] Giấy phép: mã nguồn không còn chứa thư viện AGPL của Swiss Ephemeris. (PyQt6 mã nguồn mở theo GPL-3.0).
- [x] Không còn binary bên thứ ba trong `rat/bin/` (đã gỡ `spider`), không cần kèm thông báo bản quyền MIT riêng cho binary crawler ngoài.
- [x] Ghi công mô hình dịch (OPUS-MT và Argos, CC-BY-4.0): đã có trong README, `ATTRIBUTION.txt` đi kèm bundle, và thẻ "Giới thiệu & Bản quyền" trong Cài đặt (`SettingsView.qml`).
- [ ] Kiểm tra giấy phép của model SLM và sprite linh vật.

## 2. Định vị

**Mục tiêu cuối:** giảm ma sát khi dùng máy tính. Mọi tính năng được đánh giá bằng việc nó bớt được bao nhiêu bước, bao nhiêu lần chuyển cửa sổ và bao nhiêu thời gian chờ trong một việc có thật.

**Một câu:** RAT biến những việc nhiều bước trên Mac (tìm tệp, đọc và hỏi tài liệu, dịch, xem lịch, mở đúng thứ cần mở) thành một phím tắt và một câu tiếng Việt, ngay tại chỗ đang làm.

**Khách hàng đầu tiên:** sinh viên TDTU dùng MacBook Apple Silicon. Chọn nhóm này vì việc học của họ lặp lại nhiều thao tác giống nhau, dễ đo. Đây là thị trường đầu tiên, không phải giới hạn của sản phẩm. Giảng viên, người đi làm và người dùng Windows là bước mở rộng sau khi có dữ liệu.

**Lĩnh vực đăng ký:** Giáo dục.

**Vấn đề (cần xác nhận bằng khảo sát ở mục 6):**
1. Một việc nhỏ tốn nhiều bước: mở Finder tìm tệp, mở PDF, sao chép đoạn văn, chuyển sang tab chat, dán, chờ, chép kết quả về.
2. Mỗi lần chuyển cửa sổ làm đứt mạch đang học.
3. Ràng buộc đi kèm: tài liệu học tập và đồ án không nên phải gửi lên dịch vụ bên ngoài để được giúp, và chi phí phải vừa túi tiền sinh viên.

**Không định vị là:** "chatbot chạy cục bộ" hay "chat với PDF". Đối thủ ở mục 4 đã làm việc đó. Chạy trên máy là cách RAT giảm ma sát mà không đổi lấy rủi ro dữ liệu, không phải sản phẩm.

## 3. Sản phẩm hiện có và chất lượng kỹ thuật

Trạng thái lấy từ code ngày 10/11/2026. "Có trong code" chưa có nghĩa là đã kiểm tra trên bản build; luồng nào đưa vào bản phát hành hoặc demo phải chạy thử trước.

| Năng lực | Trạng thái |
|---|---|
| Gọi bằng phím tắt (mặc định `⌥⇧Space`) | Đã đăng ký thử với helper native ngày 14/11/2026; chưa thử bấm phím thật trên bản build |
| Tìm kiếm lai tài liệu cục bộ (FTS5 và vector) | Có trong code |
| Đọc PDF, DOCX, PPTX, XLSX; OCR | Có trong code |
| Hỏi đáp bằng SLM chạy trên máy (Ollama/MLX) | Đã chạy `main.py status` với `qwen2.5:1.5b` |
| Dịch Anh-Việt offline | Có trong code, mô hình nằm trên máy dev, chưa kiểm tra trên máy sạch |
| Thời khóa biểu, xếp lịch nhóm, tìm phòng TDTU | Có trong code |
| Tác tử gọi 39 tool (mở tệp, mở app, ghi chú, xếp lịch...) | Có trong code |
| Chặn hành động do nội dung tệp tự yêu cầu (`untrusted_gate`) | Đã nối lại, có test tự động |
| Kéo thả PDF | Có `DropArea` trong `PDFDesk.qml`, chưa kiểm tra |
| Kéo thả ảnh | Đã nối vào desk chính (`QuickPDFController` + `PDFDesk.qml` + `Composer.qml`), có test tự động trên `QuickPDFController` và `PDFDesk.qml`: thả/chọn ảnh khi ô trống sẽ OCR và gắn ngữ cảnh kèm 3 gợi ý nhanh (Dịch / Tóm tắt / Giải thích); thả khi đã gõ lệnh sẽ chạy ngay |
| Cài đặt bằng `.app` / `.dmg` cho người không biết kỹ thuật | Chưa kiểm tra, rủi ro lớn nhất khi phát hành |

**Chất lượng hiện tại:** ngày 15/11/2026 toàn bộ suite chạy xanh trên máy dev: 1531 passed, 1 skipped, 3 xfailed. Các lỗi trước đó là code bị thụt lùi khi gộp từ repo nghiên cứu (đã khôi phục chọn model trợ lý, tìm theo nghĩa, bỏ qua bước duyệt tên tệp khi đã có chỉ mục nghĩa, tìm ứng dụng, định tuyến mục tiêu, kiểm tra tham chiếu lượt trước, chặn câu trả lời sai ngôn ngữ và câu trả lời bị cắt) và lỗi xếp hạng: tệp chỉ khớp từ loại tài liệu ("slides") vẫn nhận điểm cộng tài liệu học và ngang điểm với tài liệu đúng môn, vì điểm bị chặn ở 100 rồi mới sắp xếp (nay chỉ cộng khi khớp chủ đề và sắp theo điểm chưa chặn). Thả ảnh vào Mini desk cũng từng luôn báo lỗi do gắn sai nhãn nguồn; đã sửa, nhưng Mini desk chưa được khởi chạy từ đâu nên người dùng chưa gặp lỗi này, và test của nó mang dấu `unlaunched_surface`. Cửa sổ `lab` (Reasoning Lab) và `measured_ladder.py` đã bị xóa vì import từ `research_scoring` đã gỡ nên không mở được; các nhánh `answer_type` chết trong `reasoning_strategies.py` cũng đã bỏ. `tests/test_imports_resolve.py` nay import mọi module trong `rat/`, `reasoning/`, `document_intake/` và đọc mã nguồn để bắt import first-party trỏ vào module không tồn tại, kể cả import nằm trong thân hàm (chỉ bắt được tên first-party hoặc tên trong danh sách module đã xóa, không bắt gói bên thứ ba bị thiếu). CI đã chuyển sang chạy toàn bộ suite, chưa có kết quả trên CI.

### Cách truyền thông trung thực về năng lực

| Không dùng | Dùng |
|---|---|
| "Không ảo giác", "suy luận đáng tin cậy" | "Trả lời kèm trích dẫn trang để người dùng tự kiểm tra" (chỉ dùng sau khi demo được) |
| "Bảo mật tuyệt đối", "bảo mật 100%" | "Mặc định xử lý trên máy; chỉ gửi đi khi người dùng bật" |
| "Loại bỏ 100% rào cản" | "Một phím tắt, không cần chuyển tab" |
| "Chặn prompt injection" | "Thu hẹp nguy cơ: tác tử không tự hành động theo lệnh nằm trong tệp, trừ khi người dùng yêu cầu" |
| "MSRA Core IP" | Hướng nghiên cứu riêng, chưa tích hợp |

**Về MSRA:** nghiên cứu Qwen3-8B chưa nằm trong RAT. Kết quả hiện tại không phát hiện khác biệt độ chính xác (82,9% so với 82,4%, N=199, p=1.0). Chỉ nêu đây là năng lực nghiên cứu của đội, không phải tính năng.

## 4. Đối thủ và khác biệt

| Nhóm | Ví dụ | Mạnh | Điểm RAT cần chứng minh |
|---|---|---|---|
| Chatbot web | ChatGPT, Gemini | Model mạnh, quen thuộc | Không chuyển tab, tài liệu ở lại máy |
| Launcher có AI | Raycast AI | Thao tác nhanh | Tiếng Việt, ngữ cảnh học tập |
| App AI chạy cục bộ | [AnythingLLM](https://anythingllm.com), [Sidekick](https://github.com/johnbean393/Sidekick), [RecurseChat](https://apps.apple.com/app/id6476835702), [Sageling](https://www.everydev.ai/tools/sageling) | Miễn phí hoặc rẻ, cũng chat với tài liệu | Không chỉ chat: hành động trên máy, lịch TDTU, tiếng Việt |
| Tích hợp hệ điều hành | Apple Intelligence | Có sẵn | Làm việc sâu với tài liệu và lịch học |

"Chạy cục bộ" và "chat với PDF" không phải điểm khác biệt. Tính năng của các đối thủ trên lấy từ nguồn thứ cấp, phải kiểm tra lại trước khi đưa vào bảng so sánh chính thức.

**Luận điểm Agentic AI:** RAT nhận mục tiêu, chọn tool, đọc tài liệu rồi hành động trên máy, và có lớp chặn hành động không do người dùng yêu cầu.

## 5. Business Model Canvas (bản giả thuyết)

| Thành tố | Nội dung |
|---|---|
| Khách hàng | Sinh viên TDTU dùng Mac Apple Silicon |
| Giá trị | Ít bước hơn cho việc lặp lại hằng ngày: một phím tắt và một câu tiếng Việt thay cho chuỗi mở, tìm, sao chép, chuyển tab. Tài liệu mặc định ở lại máy; không tốn token cho phần chạy cục bộ |
| Kênh | Tải trực tiếp; CLB học thuật TDTU; cộng đồng người dùng Mac |
| Quan hệ khách hàng | Nhóm người dùng thử, góp ý trực tiếp |
| Doanh thu | Free: tra cứu, đọc PDF cơ bản, dịch, lịch. Pro: tác vụ tác tử nhiều bước, tổng hợp bài giảng ôn thi. Giá dự kiến 49k-69k/tháng, cần kiểm tra bằng khảo sát |
| Hoạt động chính | Phát triển app, kiểm thử với người dùng, cập nhật model |
| Nguồn lực | Đội ngũ `[CẦN ĐIỀN]`; code RAT; model nguồn mở |
| Đối tác | CLB ICON, Khoa CNTT |
| Chi phí | Phân phối và ký app (Apple Developer), website, truyền thông. Số liệu `[CẦN ĐIỀN]` |

Kế hoạch tài chính (nguồn vốn, duy trì, doanh thu dự kiến) phải tính từ số người dùng và tỷ lệ trả phí giả định, ghi rõ là giả định: `[CẦN ĐIỀN]`.

## 6. Kiểm chứng nhu cầu và đo ma sát

**Khảo sát 30 sinh viên TDTU:** loại laptop, công cụ AI đang dùng, số lần chuyển tab khi học, mức lo ngại về dữ liệu, mức sẵn sàng trả phí. Kết quả đưa vào mục khảo sát thị trường.

**Đo ma sát (chỉ số chính):** chọn 3 việc học lặp lại (tìm và hỏi một tài liệu, dịch một đoạn, xem lịch học hoặc phòng). Mỗi người dùng thử làm mỗi việc hai lần: theo cách quen thuộc và bằng RAT. Ghi số bước, số lần chuyển cửa sổ và thời gian. Chưa có số liệu nào trước lần đo này, nên không đưa con số "tiết kiệm X%" vào hồ sơ khi chưa đo.

Tính cả thời gian cài đặt và lần dùng đầu tiên. Nếu cài mất 20 phút để tiết kiệm 30 giây mỗi lần, đó là ma sát mới, phải ghi lại.

**Dùng thử với 3-5 sinh viên có Mac** (cài cho họ nếu cần, ghi lại chỗ vướng).

| Kết quả | Quyết định |
|---|---|
| Từ 3/5 người muốn dùng tiếp, và RAT ít bước hơn cách cũ ở ít nhất 2/3 việc | Giữ định vị |
| 1-2/5 người | Chọn lại việc trọng tâm |
| 0/5 người | Đổi hướng sản phẩm |

Nếu tỷ lệ dùng Mac trong khảo sát rất thấp, phải nói rõ quy mô thị trường ban đầu nhỏ và đưa bản Windows vào lộ trình, thay vì lờ đi.

## 7. Ưu tiên kỹ thuật tiếp theo

1. Thực hiện kế hoạch overhaul giao diện (`docs/ui_overhaul_plan.md`).
2. ~~Đưa toàn bộ test về xanh, cho CI chạy cả suite.~~ Xong trên máy dev; còn xác nhận CI xanh sau khi đẩy lên.
3. ~~Rà phần code thụt lùi khi gộp repo (so `af166b1` với bản hiện tại).~~ Xong ngày 14/11/2026. Ứng dụng thường trú nay dùng helper native `rat-hotkey` như Mini (không cần quyền Accessibility): `⌥⇧Space` mở desk, `⌥⇧R` đọc vùng chọn; pynput chỉ còn là phương án dự phòng khi thiếu helper. Phát hiện kèm theo: file `rat/bin/rat-hotkey` đã cũ hơn `BUILD` trong `mini_version.py`, nên bản trước đó không đăng ký được phím tắt (cả Mini). Đã build lại và thêm test chặn tái diễn; mỗi lần tăng `BUILD` phải chạy `zsh tools/build_rat_mini_hotkey.sh`. Nhãn phím tắt trên desk chính nay lấy từ cấu hình (trước đó là chữ cứng `⌥Space`, sai so với mặc định `⌥⇧Space`), có test. Đã nối kéo thả / chọn ảnh vào desk chính (`QuickPDFController` + `PDFDesk.qml` + `Composer.qml`): OCR và gắn ngữ cảnh kèm 3 gợi ý nhanh (Dịch / Tóm tắt / Giải thích), hoặc chạy ngay nếu đã gõ sẵn lệnh, có test tự động trên `QuickPDFController` và `PDFDesk.qml`.
4. Đóng gói `.app`/`.dmg` cài được trên máy sạch.
5. Dùng thử với người dùng thật, đo ma sát và tỷ lệ quay lại.

## 8. Công cụ phục vụ nghiên cứu NCKH (16/11/2026)

RAT chỉ **đọc** repo nghiên cứu (`RAT_RESEARCH_REPO`, mặc định `~/Documents/Github/multi-step-structured-reasoning`), không ghi vào đó. Mọi thứ RAT tạo ra nằm trong `~/.rat/`. Mục tiêu: giúp quy trình nghiên cứu mà không đổi kết quả nghiên cứu.

| Tính năng | Lệnh | Ghi chú |
|---|---|---|
| Theo dõi run | `rat runs`, `rat runs list`, `rat runs pause`, `rat runs resume`; mục 🧪 trên tray | Đọc dòng `>>> <bước> at <ngày>` trong `audit/*/run.log`. Thời gian còn lại ước từ bước cùng loại đã xong (`clean cf` → `clean plain`); không có thì ghi "chưa ước được". Tạm dừng = SIGSTOP lên cây tiến trình `caffeinate`/`run.sh` của job khớp `mlx_lm\|structured_llm`; giải phóng GPU/CPU, không giải phóng RAM |
| Chặn MLX trùng | tự động | `MLXDocumentSession.load()` từ chối nạp model MLX của RAT khi có job MLX nghiên cứu, kể cả đang tạm dừng (máy 16 GB chỉ chạy một job MLX). Bỏ chặn có chủ ý: `RAT_ALLOW_MLX_WITH_RESEARCH=1` |
| Bàn bài báo | `rat papers add <pdf...>`, `rat papers ask "<câu hỏi>"`; thả PDF vào view trên desk | PDF chép vào `~/.rat/papers/` và vào chỉ mục RAT bằng `Indexer` sẵn có; chọn bài bằng `SearchEngine`; đọc trang bằng `document_intake.pdf.read_pdf`; trả lời bằng `qa_engine` (tắt cloud). Trích dẫn là văn bản trang đã đưa cho mô hình, không phải chữ mô hình viết |
| Bàn gán nhãn mù | `rat label`, `rat label <run>`, `rat label <run> --report` | Gộp mọi `eval_*/*_interventions.jsonl` của run, xáo thứ tự, ẩn tên điều kiện, `id`, `flags` và `outcome`. **Khóa** cho tới khi `analyze.py` của run đã chạy (run.log có bước phân tích rồi kết thúc, hoặc `analyze.log` mới hơn `analyze.py`). Nhãn lưu ở `~/.rat/labels/<run>.jsonl`, không chứa outcome tự động. Báo cáo Cohen's κ và ma trận nhầm lẫn (hàng: người, cột: tự động) |
| CLI cho thao tác sẵn có | `rat tool list`, `rat tool run <thao tác> --args '{...}'` | Chạy mọi thao tác đã đăng ký trong registry (mở app, ghi chú, dịch, tìm tệp, lịch...) không cần GUI |
| CLI → UI | `rat ui <lệnh>`, hoặc gõ `/rat <lệnh>` trong ô soạn của desk | Mỗi lệnh trên trả về `ViewSpec` (khối summary/table/details/actions của kernel). Terminal in bằng rich hoặc `--json`; desk vẽ cùng spec bằng `CliView.qml`. Nút bấm mang `argv` của lệnh kế tiếp, nên lệnh CLI mới có giao diện mà không cần viết QML riêng |
| Dùng từ agent | `--json` trên mọi lệnh trên; `rat runs pause <run>`, `rat labels export <run>`, `rat labels report <run>` | In một envelope `{"schema": "rat.cli/1", ..., "data", "view"}`; agent đọc `data`. Không có prompt. Mã thoát: 0 ok, 1 lỗi, 2 sai lệnh, 3 từ chối có chủ ý (bàn nhãn khóa, run không phải run đang chạy, chặn MLX). Repo nghiên cứu không gọi RAT; RAT tự đọc `run.log` (pull), nên run chạy giống hệt dù RAT có bật hay không. Xem README, mục "Dùng từ agent" |

**Chưa kiểm tra:** tạm dừng/tiếp tục trên một run thật đang chạy (đã test bằng bảng tiến trình giả); thả PDF từ Finder vào desk trên bản build (đã test bằng `runCliDrop`); chất lượng câu trả lời của bàn bài báo (chấm trang dựa trên trùng từ khóa của `qa_engine`, PDF scan cần OCR).

**Quy tắc dùng nhãn:** nhãn người chỉ dùng để kiểm tra bộ phân loại outcome sau khi phân tích đã đăng ký trước chạy xong; không đưa vào phân tích đó. Mở `--report` giữa chừng sẽ thấy phân bố outcome tự động của các hàng đã gán, nên chỉ mở khi đã gán xong.
