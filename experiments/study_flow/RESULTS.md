# Study flow on documents other than page 4 (2026-11-19)

Every fix to the ask → quiz → note flow (page_match, the quiz instruction, key_supported_by_quote)
was measured on one page: ly-thuyet-giua-ky-502044.pdf page 4, logic gates. This run checks whether
they hold on three documents unlike it. `probe.py` drives QuickPDFController offscreen with the real
local model (qwen3:4b-instruct), as a student would type, and writes `out/<doc>.json`.

| Doc | Pages | Kind | Question | Expected answer, page |
|---|---|---|---|---|
| wiki | 14 | Vietnamese prose, economics | Đến năm 2017 có bao nhiêu nước công nhận Việt Nam là nền kinh tế thị trường? | 69 nước, page 3 |
| dsa | 1 | dense tables and Java code | Quick sort trường hợp xấu nhất có độ phức tạp bao nhiêu? | n², page 1 |
| toeic | 4 | English-learning notes | Tranh chỉ có đồ vật, không có người thì đáp án đúng thường dùng cấu trúc gì? | is placed / has been arranged / is located, page 2 |

Then "Tạo 5 câu trắc nghiệm từ phần này" and "Lưu thành ghi chú".

Thresholds, fixed before running. Quiz questions are graded under "Chọn phát biểu đúng và đầy
đủ nhất" (bad = wrong key, or another option at least as complete and true, or ill-posed):
- GO: the answer is right and cites the expected page on 3/3; each quiz has at most 1/5 bad;
  no quiz falls back to extracted questions; every note file holds the questions and the page.
- KILL: 2/5 or more bad on at least 2 documents. Then quiz quality was specific to page 4, and
  the next step is the model, not more rules.
- Otherwise: iterate on what failed, by document.

Labels by Claude only, who also wrote the code under test.

## Results

| Doc | Ask (s) | Answer, page | Quiz (s) | Questions | Bad | Note |
|---|---|---|---|---|---|---|
| wiki | 12.7 | right, page 3 | 60.2 | 5/5, model | 1 (Q4: all four organisations are true) | questions, page 3 |
| dsa | 8.8 | right, page 1 | 67.0 | **2/5**, model | 0 | questions, page 1 |
| toeic | 10.5 | right, page 2 | 60.7 | 5/5, model | 1 (Q3, strict: "above, below" are also position words) | questions, page 2 |

Against the pre-set thresholds: GO as written. Page grounding held on 3/3, no quiz had more
than 1/5 bad, none fell back, and every note kept its questions and page. KILL (2/5 bad on two
documents) was not met.

What the thresholds did not cover, found while checking the DSA quiz:

- **Code pages starve the quiz.** Two more DSA runs (same page, same settings) gave 0 usable
  items: the model asked "which function does X" and copied the key's code into all three
  distractors, so the duplicate check dropped every item (`no_grounded_items`). The probe run's
  2/5 was the lucky draw.
- **The extract fallback writes questions where every option is true.** Its distractors are other
  sentences from the same page, and the stem asks which one "phù hợp với tài liệu", so all four
  fit. The card says the questions were lifted from the page, but it does not say none can be
  answered. This is the worst quiz RAT can show, and it is shown exactly when the model fails.
- `key_supported_by_quote` dropped a one-word key ("n²" from the Big-O table); it now needs
  min(2, key words) shared. Re-measured on the 60 from runs 4-5: unchanged (5 dropped, 55 kept).
  A computed key ("recur(3,2)" -> "9") is still dropped, since the quote does not state it.
- Wiki Q4 is a new kind of bad item: a list on the page ("thành viên của A, B, C, D") turned into
  "which one", where all are members.
- Each note file is named after the request ("Tạo 5 câu trắc nghiệm từ phần này"), not the topic.
