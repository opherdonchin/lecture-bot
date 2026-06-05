# Tutor Packet Replay: gpt-5.4-mini

- Created: 2026-06-05T05:01:40.808304+00:00
- Source database: `data/lecture_bot.db`
- Result database: `reports/tutor_packet_replay_20260605.sqlite`
- Sample: 20 random `gpt-5.4` audit packets, seed `20260605`
- Target model: `gpt-5.4-mini`

## Speed And Token Summary

- Successful target calls: 20/20
- Parsed JSON assistant messages: 20/20
- Target latency mean: 3.78 s
- Target latency median: 3.47 s
- Target latency min/max: 1.78 / 6.75 s
- Original response latency: not available in the source schema/log rows inspected
- Original total tokens mean: 24680
- Target total tokens mean: 24567

## Quality Read

- Question/statement ending matched the stored original in 19/20 successful calls.
- All 20 mini responses preserved the JSON contract and produced a parseable `assistant_message`.
- All 20 stayed in English and kept the tutor posture: brief feedback plus a next question or next-step prompt. None dumped a full answer in a way that would obviously break the tutoring flow.
- The main quality difference is curriculum steering. In several rows the mini response gave a good local reply but chose a different next probe than the original `gpt-5.4` response. That is usually acceptable for chat flow, but it can matter if the hidden state is trying to cover specific remaining lecture gaps.
- Mini was more concise: average completion usage was 349 tokens versus 463 original completion tokens, about 25% lower. This helps speed and readability, but it sometimes drops the original's more precise refinement.
- One row involved the student objecting to a language false positive. Mini handled it reasonably, but with a slightly odd "I misread that" phrasing; this is a reminder to keep deterministic language-policy handling outside the model where possible.
- No original response-time data was available in the audited schema/log rows, so this replay proves mini latency on these packets but cannot compute a measured before/after speedup from local logs.

## Sample Rows

| audit_id | turn | target_s | orig_tokens | target_tokens | note |
| --- | ---: | ---: | ---: | ---: | --- |
| 4308 | 8 | 5.88 | 26095 | 26070 | matches question/statement ending; similar length |
| 3983 | 23 | 3.12 | 20588 | 20483 | differs in question/statement ending; similar length |
| 3095 | 16 | 4.80 | 28400 | 28381 | matches question/statement ending; much shorter |
| 3377 | 20 | 4.48 | 26895 | 26890 | matches question/statement ending; similar length |
| 3035 | 14 | 2.72 | 20859 | 20589 | matches question/statement ending; similar length |
| 3203 | 19 | 6.75 | 21548 | 21548 | matches question/statement ending; similar length |
| 2934 | 22 | 4.55 | 26425 | 26201 | matches question/statement ending; similar length |
| 4155 | 17 | 3.05 | 27351 | 27215 | matches question/statement ending; similar length |
| 3077 | 12 | 1.78 | 20433 | 20136 | matches question/statement ending; similar length |
| 3488 | 28 | 3.32 | 27495 | 27492 | matches question/statement ending; similar length |
| 4010 | 8 | 2.77 | 26710 | 26586 | matches question/statement ending; similar length |
| 4366 | 4 | 4.02 | 25692 | 25645 | matches question/statement ending; similar length |
| 3492 | 32 | 3.79 | 27404 | 27436 | matches question/statement ending; similar length |
| 3007 | 23 | 5.89 | 20779 | 20768 | matches question/statement ending; similar length |
| 3009 | 25 | 3.76 | 20767 | 20762 | matches question/statement ending; similar length |
| 3599 | 2 | 1.82 | 25282 | 24951 | matches question/statement ending; similar length |
| 3775 | 12 | 2.97 | 26135 | 26122 | matches question/statement ending; similar length |
| 4166 | 9 | 3.20 | 26857 | 26671 | matches question/statement ending; much shorter |
| 2903 | 15 | 3.49 | 20489 | 20140 | matches question/statement ending; much shorter |
| 4343 | 10 | 3.46 | 27406 | 27253 | matches question/statement ending; similar length |

## Recommendation

Moving ordinary dialogue turns to `gpt-5.4-mini` looks wise as a controlled rollout, not as a blind full replacement. The 20 replayed packets show strong API compatibility, low observed latency, and generally sound tutor responses. I would use mini for normal back-and-forth tutoring, keep `gpt-5.4` available for repair failures, final grading/report generation, and unusually high-stakes or state-sensitive turns, and add production response-time logging before claiming a measured speedup. The biggest thing to monitor is not correctness collapse; it is quieter drift in the next question the tutor chooses to ask.
