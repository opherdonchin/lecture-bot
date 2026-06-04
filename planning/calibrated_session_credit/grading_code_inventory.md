# Grading code inventory (current, for reviewers without repo access)

Verbatim excerpts of the grading-relevant code as it exists today. Paths and
line ranges are approximate at time of writing.

## `app/bot_engine.py` — constants + grade computation

```python
_GRADE_POLICY_ID = "fixed-four-topic-v1"
_GRADE_WEIGHTS = [55, 25, 13, 7]

_SCORE_IF_SUCCESS = [
    (0,   0,   45),
    (1,   30,  42),
    (31,  54,  62),
    (55,  71,  77),
    (72,  87,  92),
    (88,  99, 100),   # robust but below perfect — project to 100
    (100, 100, None), # already at perfect mastery — no gain possible
]

def grade_policy_snapshot() -> dict:
    return {
        "policy_id": _GRADE_POLICY_ID,
        "ranked_topic_weights": list(_GRADE_WEIGHTS),
    }

def _weighted_grade_from_scores(scores: list[int]) -> int:
    ranked = sorted(scores, reverse=True)[:len(_GRADE_WEIGHTS)]
    padded = (ranked + [0] * len(_GRADE_WEIGHTS))[:len(_GRADE_WEIGHTS)]
    return math_.floor(sum(w * s / 100 for w, s in zip(_GRADE_WEIGHTS, padded)))

def _grade_from_scores(scores: dict[str, int]) -> int:
    return _weighted_grade_from_scores(list(scores.values()))

def compute_grade_impact_deltas(sampled_topic_ids, best_mastery) -> dict[str, int]:
    base_scores = {tid: best_mastery.get(tid, 0) for tid in sampled_topic_ids}
    current = _grade_from_scores(base_scores)
    deltas = {}
    for tid in sampled_topic_ids:
        cur = base_scores[tid]
        sif = next((s for lo, hi, s in _SCORE_IF_SUCCESS if lo <= cur <= hi), None)
        if sif is None:
            deltas[tid] = 0
        else:
            trial = dict(base_scores); trial[tid] = sif
            deltas[tid] = _grade_from_scores(trial) - current
    return deltas

def compute_weighted_grade(topic_scores: list[dict]) -> int:
    return _weighted_grade_from_scores([ts["score"] for ts in topic_scores])
```

## `app/bot_engine.py` — prompt injection (state surfaced to tutor)

```python
best_mastery = dict(state.get("best_mastery", {}))
current_state = {
    "topics_sampled": list(sampled_topic_ids),
    "topics_covered": list(state.get("topics_covered", [])),
    "mastery": dict(state.get("mastery", {})),
    "best_mastery": best_mastery,
    "evidence_notes": dict(state.get("evidence_notes", {})),
    "current_topic_id": state.get("current_topic_id"),
    "tutor_comment": state.get("tutor_comment", ""),
    "turn_count": state.get("turn_count", 0) + 1,
    "grade_impact_deltas": compute_grade_impact_deltas(list(sampled_topic_ids), best_mastery),
}
```

## `app/main.py` — backend grade update (monotone)

```python
def _update_backend_grade_state(db, *, session, state, lecture_package) -> None:
    ...
    for topic_id, score in current_mastery.items():
        best_mastery[topic_id] = max(best_mastery.get(topic_id, 0), score)
    best_mastery = {tid: s for tid, s in best_mastery.items() if s > 0}
    topic_scores = [{"topic_id": tid, "score": s} for tid, s in best_mastery.items()]
    current_grade = float(bot_engine.compute_weighted_grade(topic_scores))
    state["mastery"] = current_mastery
    state["best_mastery"] = best_mastery
    state["current_grade"] = current_grade
    session.current_grade = max(float(session.current_grade or 0.0), current_grade)
```

## `app/main.py` — grade event recording (policy snapshot injected)

```python
def _record_grade_event(db, *, session_id, event_type, grade, payload) -> None:
    event_payload = dict(payload)
    event_payload.setdefault("grade_policy", bot_engine.grade_policy_snapshot())
    db.add(models.GradeEventModel(
        session_id=session_id, event_type=event_type,
        grade=float(grade), payload_json=j_.dumps(event_payload, ensure_ascii=False),
    ))
```

## Models (no DDL change needed)

```python
class SessionModel(...):
    current_grade: Mapped[float | None] = mapped_column(sa.Float, nullable=True)

class GradeEventModel(...):
    event_type: Mapped[str]               # "grade" | "report"
    grade: Mapped[float]
    payload_json: Mapped[str | None]      # free-form JSON — new fields ride here
```

## Verified arithmetic (current vs proposed)

| Raw top-4 | Current (raw weighted) | Proposed (calibrated, targets `[90,82,74,62]`) |
|---|---|---|
| `[90,82,78,74]` (teacher) | **85** | **100** |
| `[90,82,74,62]` | 83 | **100** |
| `[90]` | 49 | **55** |
| `[90,82]` | 70 | **80** |
| `[90,82,74]` | 79 | **93** |
| `[100,100,100,100]` | 100 | **100** |
| `[45,45,45,45]` | — | **54** |
| `[62,62,62,62]` | — | **74** |
