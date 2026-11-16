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

Not yet scored: `invented_numbers` (literal numbers not backed by the payload).
