# Generative views: first run (2026-11-16)

Question: can a model compose a usable screen on demand from a fixed block catalog
(`views_catalog.py`), with data bound by reference only?

Setup: `qwen3:4b-instruct` via Ollama 0.40.14, temperature 0.3, seeds 1-3, JSON-schema
constrained output. Three requests: tarot 3-card spread (draw done by code), electricity
bill tracker (6 synthetic bills, no PDF extraction), 10-question quiz from page 4
("3. Cổng logic") of `ly-thuyet-giua-ky-502044.pdf`. Renders are HTML stand-ins for QML.
The strong-model arm was not run: no Gemini/OpenAI/Anthropic key is configured.

| Task | Passes structural check | Usable without fixing (manual read) | Compose time |
|---|---|---|---|
| Tarot | 3/3 | 1/3. Seed 1 hides the card name, seed 2 hides the meaning; `reversed` ignored 3/3 | 13-19 s |
| Bills | 3/3 | 0/3. Same 7 blocks every time, including a nonsense quiz over bill months; `next_due` (asked for) never shown | 31-38 s |
| Quiz view | 3/3 | 3/3 for the layout | 12-16 s |
| Quiz content (seed 1) | 10/10 have 4 choices and cite page 4 | 6/10 answer keys right, 1 ambiguous, 3 wrong (one has no correct option, one has two identical choices) | 60-172 s |

Findings:

1. The structural validator passed 9/9 specs, yet only the quiz layout was usable as is.
   Structure checks catch broken references, not wrong choices (which field is the title,
   which blocks belong on the screen).
2. Composition failures are cheap to fix in the catalog and prompt (enum for `face`,
   "use only blocks the request needs", a required "what must be visible" list per request).
3. Content generation is the unreliable part: 3-4 wrong answer keys out of 10 would teach
   wrong facts. This is the "data must be reliable" side and needs verification or a
   stronger model, not a better layout.

4. `invented_numbers` (scored later on the saved specs, no recompose): 0 invented numbers
   in 9/9 specs. This is weak evidence. There were 18 literal number tokens across 8 specs (bills seed 1 had
   none), nearly all repeats of the same counts ("3 lá", "10 câu", "6 hoá đơn") and one date ("10/12/2026", which matches
   `next_due` 2026-12-10). Binding by reference left the model almost nothing to invent.
   The check also has two blind spots. It tests day, month and year one by one, so a
   swapped date passes. And the quiz payload is model-generated (stage A), so "backed by
   the payload" says nothing about whether a quiz number matches the PDF.

# Run 2: are the composition failures cheap to fix? (2026-11-16)

Rescoring run 1 with stricter checks (quiz `choices_key` must point at lists,
`metric_chart` values must be numbers, `face` is up/down) fails all 3 bills specs,
so run 1's "9/9 structural pass" overstated the result. Two of the failures were
the catalog's fault, not the model's: `stat` accepted only numbers (no way to
show `next_due`), and `card_grid` had no slot for `reversed`. Both are fixed.

Pass means: no structural errors, every `MUST_SHOW` field on screen, no noise block.
`MUST_SHOW` is the experimenter's judgement. One repair turn with validator errors.
Quiz questions are reused from run 1, so content is held fixed.

Thresholds, fixed before running (final pass, out of 9 per arm):
- Arm A (catalog + prompt) >= 8/9: model composition is viable at 4B; next, test it on new requests.
- Only arm B >= 8/9: a "what must be shown" step is the missing piece; next, test whether the model can write that list itself.
- Both arms <= 6/9: drop on-demand composition for the 4B model; use fixed templates per intent.
- Anything in between: inconclusive at this sample size; say so rather than pick.

## Run 2 results

| Task | Arm A pass (first / after repair) | Arm B pass (first / after repair) |
|---|---|---|
| Tarot | 0/3 / 0/3 | 1/3 / 1/3 |
| Bills | 0/3 / 0/3 | 0/3 / 0/3 |
| Quiz view | 3/3 / 3/3 | 3/3 / 3/3 |
| **Total** | **3/9** | **4/9** |

Verdict against the pre-set thresholds: both arms are at or below 6/9, so on-demand
composition with `qwen3:4b-instruct` is dropped. Use fixed templates per intent.

What failed:

1. The repair turn fixed nothing (0 of 9 failing specs passed after it). With bills,
   the model repeated the same error after being told what it was.
2. Bills never passed. Arm B wrote a column label into a key slot (`title_key: "Tháng"`)
   3/3 times. Arm A still added a quiz block over bills (seed 1) despite rule 2.
3. Tarot: even when told the 4 fields to show (arm B), the model left a free slot
   unused and dropped the card name in 2/3 (e.g. `title_key: position`, no `subtitle_key`).
4. The quiz view passes every time, but it is a one-to-one mapping (one list, one
   block, field names that match the block's keys). It is the easiest case, not
   evidence that composition works.
5. 0 invented numbers in all 18, as in run 1.

Limits: 3 seeds per cell, one 4B model, `MUST_SHOW` written by the experimenter.
A stronger model was not tested (no API key), so this verdict is about 4B, not the idea.

# Run 3: can a second pass catch wrong quiz answers? (2026-11-16)

Relabelling all 30 run 1 questions (`quiz_labels.json`, labelled by Claude, no second
labeller): 16 right, 10 wrong key, 4 ambiguous. Run 1's "3/10 wrong" was seed 1 only;
over three seeds, 14/30 questions should not reach a student.

A checker sees page 4 and the question, never the key. V1 solves the question
(answer or NONE, plus any other correct options). V2 marks each option true or false
against the page. A question is flagged if the checker disagrees with the key or finds
zero or several correct options. Both also flag identical options, in code.

Thresholds, fixed before running (per checker, seed 1, 30 questions):
- GO: at most 1 bad question left among those that pass, and at least 8 of 16 right ones pass.
- KILL: 4 or more bad questions pass. A 4B checker cannot guard quiz content; quiz
  needs a stronger model or answer keys taken from the material, not generated.
- In between: iterate (e.g. ensemble of seeds), and say it is not yet good enough.

## Run 3 results

| Checker | Bad questions that pass (of 14) | Right questions that pass (of 16) | Same flags on all 3 seeds |
|---|---|---|---|
| V1 (solve blind) | 0 | 16 | 30/30 |
| V2 (judge each option) | 0 | 16 | 30/30 |

Verdict against the pre-set thresholds: GO. On these 30 questions a blind second pass by the
same 4B model removes every bad question and keeps every right one.

Why it works, and why that limits the result: the generator's errors were mostly a wrong
letter. The content held a correct option, but the key pointed at another one (10 of 14). When
the same model is asked to solve the question instead of writing it, it finds the right option
every time (V1 answered B for seed 1 Q1 and Q9, NONE for Q2). So the failure is binding a letter
while generating, not knowing the material.

Limits: one page, one topic (logic gates, where a truth table answers most questions), labels
by Claude only, 30 questions. The questions came from this experiment's naive generator (the
model writes four options and a letter). RAT's `rat/engine/quiz_generator.py` already avoids the
letter step: the model writes the correct answer as text and code shuffles the options. Next:
run that generator and check whether it still needs this pass.

# Run 4: RAT's own generator, then the same checker (2026-11-16)

`run4.py` calls `rat/engine/quiz_generator.generate_quiz_from_text` on page 4 with RAT's
SLM settings (temperature 0.1, num_ctx 8192) and seeds 1-3, 10 questions each, about 190 s
per quiz. All 30 quotes were grounded. Labels in `quiz_labels_rat.json` (Claude only).

| | Count of 30 |
|---|---|
| Wrong key | 0 |
| Several options true (Q1 in every seed: true statements about different gates; seed 1 Q1 is also ill-posed) | 3 |
| A distractor is a true sufficient condition (e.g. "XNOR is 1 when both inputs are 1") | 9 |
| Right | 18 |

The wrong-letter failure from run 1 is gone: the model writes the answer as text and code
assigns the letter. The remaining failure is distractors that are true. The model treats
"output is 1 when ..." as asking for the defining condition, so a true special case counts as
"wrong" to it. Whether that is a defect depends on the reading. Under the strict reading
(a student who picks a true statement should not lose the point) it is 12/30 bad. If only the
defining condition counts as the answer, it is 3/30 bad.

Checker (`verify.py --src out4`), against run 3's thresholds:

| Checker | Bad that pass (of 12) | Right that pass (of 18) |
|---|---|---|
| V1 (solve blind) | 11 | 18 |
| V2 (judge each option) | 9 | 18 |

KILL for this failure: the 4B checker shares the generator's reading, so it does not see a
true special case as true. V2 caught Q1 in seeds 2 and 3 (it marked all four options true)
and seed 3 Q4, nothing else. Run 3's GO only holds for wrong-letter errors, which RAT's
generator no longer makes.

What this means for RAT's quiz: no answer key was wrong in 30 questions. The open problem is
question wording, not facts. The cheap next test is a generator prompt change: ask for stems
that request the complete condition ("phát biểu nào mô tả đầy đủ ...") and for distractors that
are false in every case. Then relabel 30 questions and compare 12/30. A second 4B pass is not
the fix.

# Run 5: one-correct-answer prompt (2026-11-19)

`QUIZ_SYSTEM_PROMPT` in `rat/engine/quiz_generator.py` adds rules: every option is about the
subject the question names, distractors are false by the page, and no true special case or true
identity is used as a distractor. Otherwise the same as run 4: `run5.py`, page 4, seeds 1-3,
10 questions each. Labels in `quiz_labels_rat5.json`, under the same strict reading (Claude only,
who also wrote the prompt, so they are not blind).

Thresholds, fixed before running, against run 4's 12/30 bad:
- GO: at most 4/30 bad (ambiguous or wrong), wrong keys at most 1, at least 27 grounded questions,
  and a mean of at most 250 s per quiz (run 4: about 190 s).
- KILL for prompt-only: 9/30 or more bad. Next would be a per-distractor field that says why it is false.
- In between: keep the prompt, say it is not enough, and test the per-distractor field.

## Run 5 results

| | Run 4 (old prompt) | Run 5 (new prompt) |
|---|---|---|
| Wrong key | 0 | 0 |
| Bad (ambiguous or ill-posed) | 12 | 11 |
| Grounded | 30 | 30 |
| Seconds per quiz | about 190 | 212, 136, 135 |

Verdict against the pre-set thresholds: KILL for prompt-only. The 4B model reads the rules and
still offers "cả hai đầu vào bằng 1" against XNOR and "các đầu vào đều bằng 1" against OR. The
bad questions are the same ones in every seed: Q1 (the table header, no gate named) 3/3, OR 3/3,
XNOR 3/3, NAND 2/3. So the failure is the question type ("gate X outputs 1 when ..."), not chance.
The prompt was reverted, so its rules are quoted here:

> Câu hỏi nói rõ đối tượng ... Mỗi phương án nhiễu phải SAI theo tài liệu ... Không dùng một
> trường hợp riêng vẫn đúng làm phương án nhiễu ... Không dùng đẳng thức, định luật hay tính
> chất đúng làm phương án nhiễu.

Run 3 already showed that a second 4B pass shares this reading, and a per-distractor "why it is
false" field asks the same model for the same judgement, so it is not the next test either.

# Run 6: "đầy đủ nhất" and a key-quote check, no model change (2026-11-19)

Two changes in `rat/engine/quiz_generator.py`, measured on the 60 labelled questions of runs 4-5
without calling the model again:

- Each quiz carries `QUIZ_INSTRUCTION`, "Chọn phát biểu đúng và đầy đủ nhất.", shown on the card
  and in saved notes. Under that reading a true special case is a wrong answer, and the 17
  sufficient-condition questions become right.
- `key_supported_by_quote` drops an item whose key shares fewer than 2 content words with its
  quote (page_match STOPWORDS removed, digits ignored).

Thresholds, fixed before applying the check: GO if it drops all 6 Q1s and keeps at least 53 of the other 54.

| | Count of 60 |
|---|---|
| Dropped, all Q1 (table header) | 6 |
| Kept, right under the strict reading | 37 |
| Kept, right only under "đầy đủ nhất" | 17 |
| Kept, wrong key | 0 |

GO. Limits: one page of one course, labels by Claude only. The gap is 1 shared word for the
dropped and 3+ for the kept, so 2 is not a tuned edge, but a key made only of numbers ("8 ô")
is now always dropped. A student who picks a true special case still loses the point; the
instruction says why.

## Run 6, live check and one change after it

A live quiz on page 4 (count 5, no seed) kept 3 of 6 items: the check also dropped two good
questions whose key is a value ("AND khi đầu vào 1, 1 ra bao nhiêu?" -> "1", NAND -> "0"). A
value key cannot have a second true option among other values, so it now passes when every
number in it appears in the quote. The quiz also asks the model for one spare item.

Re-measured on the 60: 5 of 6 Q1s dropped, all 54 others kept. That misses the pre-set GO
(all 6 dropped) by one: run 4 seed 1 Q1, key "00, 01, 10, 11", now passes. The trade is
deliberate: one ill-posed question of 60 against losing every value question.

## Run 7: a distractor the quote also states (offline, 2026-11-19)

Most bad questions so far have a distractor that is also true and is on the page ("ra 0 khi …"
for XOR, an organisation the page lists). Rule under test, in code, no model: drop a question if
any distractor passes `key_supported_by_quote(distractor, quote)`, the same test the key must pass.

Data: every labelled question that the current pipeline keeps (key supported by its quote):
out4 and out5 with `quiz_labels_rat.json` / `quiz_labels_rat5.json`, plus the study-flow quizzes
in `experiments/study_flow/out/` with `experiments/study_flow/labels.json`. Labels are Claude's,
written before this rule existed.

Thresholds, fixed before running:
- GO: drops at least half of the ambiguous questions and at most 2 right ones.
- KILL: drops under a third of the ambiguous questions, or 5 right ones or more.
- Otherwise: iterate on the rule once, then decide.

### Result: KILL

`uv run python experiments/generative_views/run7_distractor_check.py`. Of the 67 labelled questions
the pipeline keeps, the rule drops 13/20 ambiguous ones and 33/47 right ones. Five right ones was
the KILL line.

Why: a good distractor is meant to sound like the page, so it reuses the quote's words whether it
is true or false. "Cả hai đầu vào bằng 1" has the same words as a false option for XOR and as a
true one for OR; only the meaning of the gate decides. Exploratory, after the verdict: dropping
on the share of a distractor's words found in the quote does not separate the labels at any cut
(50%: 12/20 ambiguous, 20/47 right; 75%: 6/20 and 9/47; 90%: 1/20 and 4/47).

Code that looks at words cannot tell a true distractor from a plausible one. What is left is a
reader that understands the statement: a larger model checking each option against the quote.
The 67 labelled questions are the offline test set for it.

## Run 8: qwen3:4b with thinking checks each option (offline, 2026-11-19)

Same 67 labelled questions as run 7. For each, qwen3:4b (thinking on, local Ollama) gets the
quote, the question and the four options in their delivered order, and is not told the key. It
returns the letters of every option that is a true answer to the question, by the quote and by
correct subject knowledge. Rule under test: drop the question if the checker marks any
distractor true. Keys were never wrong in this data, so a checker that leaves the key unmarked
is noted, not counted.

Earlier this idea was set aside on reasoning alone ("same family, same reading"). It was never
measured, so it is a hypothesis.

Thresholds, the same as run 7, fixed before running:
- GO: drops at least half of the ambiguous questions and at most 2 right ones.
- KILL: drops under a third of the ambiguous questions, or 5 right ones or more.
- Otherwise: iterate on the prompt once, then decide.
Also recorded: seconds per question; a checker that adds more than about a minute to a
five-question quiz would need its own decision even on GO.

### Result: stopped on cost after one question; accuracy not measured

The first question (out4/1/Q1, ambiguous) took 550.6 s, and the checker marked only the key, so
it missed that one. A 90 s streamed probe on the second question showed why: about 9 tokens/s on
this Mac, and the thinking keeps re-checking the options ("Wait, … let me check the options
again"), about 2,900 characters in 90 s with no answer yet. At roughly nine minutes a question, a
five-question quiz would wait about 45 minutes. That is far past the one-minute bound set above,
so no accuracy result could make this checker usable here. The full 67-question run (about ten
hours) was not done. `run8_out.json` holds the one result.

Still untested, cheap: the same check with thinking off (qwen3:4b-instruct, the generator's own
model in a checker role), which should take seconds a question.
