# Diagnostics Workflow

This branch adds a lightweight diagnostics layer for the remaining tutor issues:

- false escalation after "harder / gets points"
- disguised repeats
- weak stop conditions
- source drift
- switch-request handling
- technical-request re-entry into content

## Main files

- [app/diagnostics.py](/home/opher/Repositories/lecture-bot/app/diagnostics.py:1)
- [scripts/run_session_diagnostics.py](/home/opher/Repositories/lecture-bot/scripts/run_session_diagnostics.py:1)
- [tests/test_diagnostics.py](/home/opher/Repositories/lecture-bot/tests/test_diagnostics.py:1)

## How it works

For a stored session, the diagnostics module:

1. Reconstructs per-turn records from:
   - `messages`
   - `classification_logs`
   - `dialogue_turn_audits`
2. Extracts concrete case types from real turns.
3. Scores each case as `pass` or `fail`.
4. Attributes likely cause as:
   - `backend_action_hint`
   - `tutor_realization`
   - `none`

The central design idea is to separate:

- wrong backend next-move choice
- right backend choice but weak realized tutor reply

## Run it

Single session:

```bash
pixi run python scripts/run_session_diagnostics.py SESSION_ID
```

Multiple sessions:

```bash
pixi run python scripts/run_session_diagnostics.py SESSION_A SESSION_B SESSION_C
```

Outputs go to:

- `exports/diagnostics/session_<shortid>_diagnostics.json`
- `exports/diagnostics/session_<shortid>_diagnostics.md`

## What to look at first

1. `case_counts`
   This shows which failure types are dominating.

2. `cause_counts`
   This tells us whether the dominant problem is:
   - backend action choice
   - realized tutor behavior

3. `harder_request` cases
   These are the best quick check for whether the system is really honoring value-per-turn and the difficulty ladder.

4. `near_duplicate_followup` and `weak_stop_condition`
   These show whether loop behavior is mostly structural or mostly model realization.

5. `source_drift`
   This is intentionally conservative. It only flags a small set of known external terms unless the student or lecture materials already used them.

## Current limitation

The diagnostics are intentionally lightweight and heuristic. They are meant to make failure analysis more evidence-based and repeatable, not to serve as a perfect semantic judge.
