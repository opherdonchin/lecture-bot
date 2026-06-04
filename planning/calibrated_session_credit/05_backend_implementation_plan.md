# 05 — Backend implementation plan

All changes are concentrated in `app/bot_engine.py` (mechanics + strategic
guidance) and `app/main.py` (payloads). No DB migration is required.

## 1. Constants (`bot_engine.py`)

```python
_GRADE_POLICY_ID = "ranked-target-saturation-v1"        # was "fixed-four-topic-v1"
_GRADE_WEIGHTS = [55, 25, 13, 7]                         # unchanged
_GRADE_FULL_CREDIT_TARGETS = [90, 82, 74, 62]           # NEW
```

Keep `_SCORE_IF_SUCCESS` (the concave projection ladder) unchanged — it models
how raw mastery jumps on a successful probe and is still correct.

## 2. Grade computation

Replace the raw weighted sum with the calibrated sum. Recommended: keep the
public name `compute_weighted_grade` (many call sites + tests reference it) but
make it calibrated, and rename the private helper for clarity.

```python
def _calibrated_grade_from_scores(scores: list[int]) -> int:
    ranked = sorted(scores, reverse=True)[:len(_GRADE_WEIGHTS)]
    padded = (ranked + [0] * len(_GRADE_WEIGHTS))[:len(_GRADE_WEIGHTS)]
    total = 0.0
    for weight, raw, target in zip(_GRADE_WEIGHTS, padded, _GRADE_FULL_CREDIT_TARGETS):
        completion = min(raw / target, 1.0) if target > 0 else 0.0
        total += weight * completion
    return math_.floor(total)

def _grade_from_scores(scores: dict[str, int]) -> int:
    return _calibrated_grade_from_scores(list(scores.values()))

def compute_weighted_grade(topic_scores: list[dict]) -> int:
    """Calibrated student-facing grade (policy ranked-target-saturation-v1)."""
    return _calibrated_grade_from_scores([ts["score"] for ts in topic_scores])
```

> Naming note: the word "weighted" is now slightly inaccurate, but keeping the
> symbol avoids churn across `main.py`, exports, and tests. Add a docstring
> making the calibration explicit. (Optionally add
> `compute_calibrated_grade = compute_weighted_grade` alias.)

## 3. Policy snapshot

```python
def grade_policy_snapshot() -> dict:
    return {
        "policy_id": _GRADE_POLICY_ID,
        "ranked_topic_weights": list(_GRADE_WEIGHTS),
        "ranked_full_credit_targets": list(_GRADE_FULL_CREDIT_TARGETS),  # NEW
    }
```

## 4. Ranked credit state (new helper)

A single helper computes the per-ranked-slot credit breakdown and the session
status. It is the source of truth for both strategic guidance and diagnostics.

```python
def compute_ranked_credit_state(best_mastery: dict[str, int]) -> dict:
    """Return ranked credit breakdown + session_credit_status.

    Ranks topics by raw mastery descending; assigns weights/targets by rank.
    Only the top len(_GRADE_WEIGHTS) occupied slots get a weight/target.
    """
    ranked = sorted(
        ((tid, score) for tid, score in best_mastery.items() if score > 0),
        key=lambda kv: (-kv[1], kv[0]),
    )
    rows = []
    for rank, (weight, target) in enumerate(zip(_GRADE_WEIGHTS, _GRADE_FULL_CREDIT_TARGETS)):
        if rank < len(ranked):
            tid, raw = ranked[rank]
        else:
            tid, raw = None, 0
        completion = min(raw / target, 1.0) if target > 0 else 0.0
        rows.append({
            "topic_id": tid,
            "raw_mastery": raw,
            "rank": rank + 1,
            "target_for_full_credit": target,
            "credit_completion": round(completion, 4),
            "credit_contribution": round(weight * completion, 4),
            "grade_delta_to_target": max(0, target - raw),
            "status": "full_credit_satisfied" if raw >= target else "below_target",
        })
    grade = math_.floor(sum(r["credit_contribution"] for r in rows))
    all_slots_filled = all(r["topic_id"] is not None for r in rows)
    full_credit = all_slots_filled and all(r["status"] == "full_credit_satisfied" for r in rows)
    return {
        "grade_policy": grade_policy_snapshot(),
        "ranked_credit_state": rows,
        "session_credit_status": "full_credit_reached" if full_credit else "in_progress",
    }
```

> `grade` here equals `compute_weighted_grade` over the same scores (cross-check
> in a test). `full_credit_reached` requires all four ranked slots occupied AND
> at/above target — i.e. exactly the condition under which `grade == 100`.

## 5. Calibrated grade-impact deltas (changed)

Rework `compute_grade_impact_deltas` to use the calibrated grade and to return 0
for target-satisfied slots. Also expose the grade-relevant next move.

```python
def compute_grade_impact_deltas(
    sampled_topic_ids: list[str],
    best_mastery: dict[str, int],
) -> dict[str, int]:
    """Calibrated ΔGrade per sampled topic if its next probe succeeds.

    A topic whose ranked slot is already at/above target yields 0, even if raw
    mastery could still rise. Topics at raw 100 also yield 0.
    """
    base_scores = {tid: best_mastery.get(tid, 0) for tid in sampled_topic_ids}
    current = _grade_from_scores(base_scores)
    deltas: dict[str, int] = {}
    for tid in sampled_topic_ids:
        cur = base_scores[tid]
        projected = next((s for lo, hi, s in _SCORE_IF_SUCCESS if lo <= cur <= hi), None)
        if projected is None:
            deltas[tid] = 0
            continue
        trial = dict(base_scores)
        trial[tid] = projected
        deltas[tid] = max(0, _grade_from_scores(trial) - current)
    return deltas
```

Because `_grade_from_scores` is now calibrated, a topic already past its ranked
target contributes nothing extra to the calibrated grade when projected upward,
so its delta is naturally 0 — no special-casing of targets is required beyond the
`max(0, …)` guard. (Add a test asserting this.)

New helper for the next-move signal:

```python
def grade_relevant_next_move(
    sampled_topic_ids: list[str],
    best_mastery: dict[str, int],
) -> str | None:
    deltas = compute_grade_impact_deltas(sampled_topic_ids, best_mastery)
    best = max(deltas.items(), key=lambda kv: (kv[1], -ord(kv[0][1:2] or "0")), default=None)
    if best is None or best[1] <= 0:
        return None
    return best[0]
```

> Keep the tie-break simple and deterministic (highest delta, then lowest topic
> id). Implementation can refine the tie-break; the contract only requires
> `null` when no positive delta exists.

## 6. Prompt injection (`build_dialogue_system_prompt`)

Augment `current_state` so the tutor sees calibrated guidance:

```python
credit = compute_ranked_credit_state(best_mastery)
current_state = {
    ...,
    "grade_impact_deltas": compute_grade_impact_deltas(sampled_topic_ids, best_mastery),
    "session_credit_status": credit["session_credit_status"],
    "grade_relevant_next_move": grade_relevant_next_move(sampled_topic_ids, best_mastery),
    # Optional richer block for the tutor; keep compact to protect prompt cache:
    "ranked_credit_state": credit["ranked_credit_state"],
}
```

Cache note: this block sits in the **dynamic suffix**
(`_build_dynamic_dialogue_prompt_suffix`), not the cache-stable prefix, so it
does not harm prompt caching.

## 7. Payload / grade event changes (`main.py`)

- `_record_grade_event` already injects `grade_policy` via `grade_policy_snapshot`
  → now includes targets automatically.
- In `_build_grade_snapshot_from_state`, add the credit block to the payload for
  diagnostics:
  ```python
  credit = bot_engine.compute_ranked_credit_state(best_mastery)
  payload["ranked_credit_state"] = credit["ranked_credit_state"]
  payload["session_credit_status"] = credit["session_credit_status"]
  ```
- Verify `grade` in the snapshot equals `floor` of the credit contributions
  (consistency assert in a test).
- Review the hand-written `explanation` strings so they don't imply raw-100 is
  required. (Wording-only.)

## 8. Report generation changes (`bot_engine.generate_report`)

- The report prompt currently injects `Final grade earned: {final_grade}/100` and
  topic scores. Add guidance to the system prompt:
  > Raw topic scores are diagnostic depth (0–100), not grade gaps. If the student
  > reached full session credit, frame remaining headroom as optional enrichment,
  > not as required work for the grade.
- No structural change to `report_json`. (Optionally include
  `session_credit_status` in `report_json` later — additive.)

## 9. Backward compatibility

- Old `grade_events` rows keep `policy_id = "fixed-four-topic-v1"` and lack
  targets — readers must treat targets as absent for old events. No rewrite.
- `sessions.current_grade` for old sessions remains the old raw-weighted number;
  not recomputed (see migration plan). Mixed policies coexist; each grade event
  is self-describing via its `grade_policy` snapshot.

## 10. Failure modes to guard

- **Division by zero**: guard `target > 0` (targets are fixed positive, but keep
  the guard).
- **Empty `best_mastery`**: `compute_ranked_credit_state` returns all-zero rows,
  grade 0, `in_progress`. OK.
- **Fewer than four topics**: padded slots have `topic_id=None`, contribution 0,
  status `below_target`; `full_credit_reached` stays False. OK (matches
  "padding with zeroes").
- **Monotone regression**: a later candidate grade lower than the accepted grade
  must not lower `sessions.current_grade` (the existing `max(...)` rule holds;
  add a regression test). See `09` Q13.
- **NaN/serialization**: `round(...)` keeps payload JSON-clean; deltas are ints.
