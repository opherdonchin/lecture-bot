# Tutor Prompt History

This archive tracks snapshots of `prompts/tutor_prompt.md`. Entries before this file was created were inferred from the archived prompt files, prompt diffs, and matching commit history where available.

## 2026-04-16.md

- Source: existing archive snapshot
- Best guess: This is an early runtime tutor prompt retained from before the structured tutor specification and backend contract work became the source of truth.

## 2026-04-21_1.md

- Source: existing archive snapshot
- Note: This archived file is empty. It appears to preserve an intermediate absent or blank prompt state from the 2026-04-21 prompt transition.

## 2026-04-21_2.md

- Commit: `e36f67d92f522b808eea56a95a8202886789e23b`
- Subject: `Add backend–tutor contract and generator prompts`
- Best guess: This introduced the contract-oriented runtime tutor prompt alongside backend-tutor contract and generator prompt work.

## 2026-04-21_3.md

- Commit: `6ce37cc4e51aec710c6c7f2808f77255e425215f`
- Subject: `Refactor documentation and prompts`
- Best guess: This clarified the runtime tutor prompt's pedagogical role and structured output requirements while the docs folder was reorganized.

## 2026-04-24_1.md

- Commit: `fbd06fa6907dd691886ee968d23780c7833b889b`
- Subject: `Refactor admin and student server scripts to support dynamic root paths and reload options`
- Best guess: This aligned the runtime prompt with backend-owned state, runtime rendering, and private-artifact boundaries emerging in the same period.

## 2026-04-24_2.md

- Commit: `c02ecb4f77622629c3a3f35ec2df23e56e48de93`
- Subject: `Refactor private artifact schema to streamline properties and enhance clarity`
- Best guess: This adjusted the tutor prompt around the private artifact schema so the model could emit backend-facing reasoning artifacts without mixing them into visible tutoring state.

## 2026-04-26_1.md

- Commit: `a5edd2b94ca60819eba433993f1cea35755197dc`
- Subject: `More tutor prompt fiddling`
- Best guess: This patched repetition, repair, and latest-message evidence handling so the tutor would stop treating procedural pushback or repeated answers as fresh mastery evidence.

## 2026-04-26_2.md

- Commit: `45fb80ff24ce805596159703ae1e0e6b042195f4`
- Subject: `Finalize tutor prompt updates`
- Best guess: This consolidated the assessment strategy around current characterization, question value, latest-message roles, and avoiding low-value reconfirmation loops.

## 2026-05-03.md

- Commit: `53ff74aeb78be89e9bef79ac9e5f5df54b450f17`
- Subject: `Update tutor specification and regenerate runtime tutor`
- Best guess: This regenerated the runtime prompt from the adaptive conceptual review tutor specification, including AI-rich learning stance, adaptive challenge, canonical topic compliance, and clearer backend ownership.

## 2026-05-03_1.md

- Source: current working tree snapshot before the next tutor prompt update
- Based on: `prompts/tutor_prompt.md`
- Note: Content-identical to `2026-05-03.md`; retained as an explicit pre-update archive point before editing the live tutor prompt again.

## 2026-05-11.md

- Source: current working tree snapshot under the current archiving rules
- Based on: `prompts/tutor_prompt.md`
- Best guess: This runtime prompt reflects the revised adaptive conceptual review tutor specification. It foregrounds strict JSON output, backend-owned state boundaries, sparse state deltas, private-artifact separation, full-characterization continuation, grade-improvement process guidance, time/lifecycle constraints, and stronger repair behavior after low-traction or copied turns.

## 2026-05-11_1.md

- Source: current working tree snapshot before the next tutor prompt/specification revision
- Based on: `prompts/tutor_prompt.md`
- Best guess: This runtime prompt reflects the active post-investigation prompt after score-improvement and mastery-frontier adjustments. It keeps the strict JSON/runtime contract and backend ownership rules while strengthening student-requested continuation, grade-improvement response, breadth/depth selection, coverage transparency, adaptive challenge, and high-value follow-up behavior for strong engaged students.
