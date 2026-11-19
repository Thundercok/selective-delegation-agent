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

# Fill-in-the-blank fallback (2026-11-19)

`extract_fallback_quiz` used to offer four sentences from the page and ask which one "phù hợp với
tài liệu", so every option was true. It now blanks one rare word of a page sentence and offers
three words of the same kind from elsewhere on the page. Code keeps an item only if no distractor,
put in the blank, gives a sentence that is on the page. No model is called.

Measured on four pages, 5 questions each (20): ly-thuyet-giua-ky-502044 page 4, wiki page 3,
dsa page 1, toeic page 2. Bad = a distractor that also makes a true statement, a blank that
cannot be told from the sentence (e.g. a function word), or an unreadable stem.

Thresholds, fixed before building:
- GO: at most 2/20 bad, and every page yields 5 questions.
- KILL: 6/20 bad or more.
- Otherwise: iterate on the kind of blank that failed.

## Result: KILL (6/20 bad)

Run with `uv run python experiments/study_flow/cloze_probe.py`; questions in `out/cloze.json`,
labels in `cloze_labels.json` (by Claude, not blind, and I built the generator). Every page gave
5 questions. Bad: gates 1, wiki 1, dsa 3, toeic 1, so 6/20, which is the KILL line.

The six come from three mechanical causes:
- Sentences are split at line breaks, so a sentence that wraps becomes a fragment (dsa Q4,
  toeic Q2).
- The blank is one item of a list on the page, and the distractors are the other items, which are
  just as true (dsa Q2, Q3).
- The blank lands on page furniture: a table header (gates Q1) or a citation number (wiki Q4).

The check "no distractor rebuilds a sentence on the page" catches a wrong word in a fixed sentence,
not a word that is true in another sentence's slot. The cloze code is not shipped. Fixing these
three causes and re-measuring on these same 20 questions would tune to them; a re-test needs
other pages.

## Fill-in-the-blank, round 2 (2026-11-19)

Fixes, one per cause above: join wrapped lines before splitting sentences; skip a blank that sits
in a comma list; skip citation marks `[n]` and lines that are mostly numbers or header words.

Re-test on pages never used before, chosen by rule (page 3) before reading them:
computer-organization-502044-midterm-notes, lo-trinh-toeic-8-tuan,
Student_Research_Proposal_Guide_TDTU_2026, Interpretable_Machine_Learning_Book. Five questions
each, 20 in all; same definition of bad.

Thresholds, unchanged from round 1:
- GO: at most 2/20 bad, and every page yields 5 questions.
- KILL: 6/20 bad or more. On KILL the fallback is removed: with no model, RAT says it cannot write
  questions now.
- Otherwise: one more look, then decide between GO and removal.

## Result, round 2: KILL (10/20 bad). The fallback is removed.

`uv run python experiments/study_flow/cloze_probe.py round2`; questions in `out/cloze_round2.json`,
labels in `cloze_labels_round2.json` (Claude, not blind). Every page gave 5 questions. Bad:
orgnotes 2, toeic8 3, proposal 3, imlbook 2. Leaving out the three proposal questions whose text
came out of the PDF broken ("echnically", "Incorporat") still leaves 7/20, over the line.

The round-1 fixes worked on the round-1 pages. While making them, two more causes and one crash
showed up there, and were fixed before round 2: Vietnamese syllables without marks ("tham") and
Vietnamese words in capitals ("KHÔNG") taken as English words or acronyms, and `int("①")`
raising because `"①".isdigit()` is true.

The new pages failed in new ways: headings and contents lines ("9.1 9.2 9.3 9.4 9.5 ____ ."), a
table header, a stem whose "This" points at a line it does not show, text the PDF reader broke
into pieces, and one distractor that is true from outside the page (TOEIC Part 4 also has
questions to read first). Each rule fixes the pages it was written on. Page layouts have more
kinds of furniture than rules written from four pages can name.

As fixed before the round, RAT now has no quiz without a model. `generate_quiz_from_text` returns
no questions with `generator: "none"` and the reason, and the desk and the `generate_quiz`
capability say why (`quiz_failure_message`: the model is not running, or it wrote nothing that
holds up on this page). The cloze code lives in `cloze.py` here, so both rounds can be rebuilt.
