import json as j
import unittest.mock as mock

import app.db as db_module
from app.diagnostics import (
    DiagnosticTurnRecord,
    detect_external_terms,
    diagnose_turn_records,
    export_session_diagnostics,
    guess_question_level,
    is_near_duplicate_question,
)
from app.main import app


LECTURE_PACKAGE = {
    "lecture_id": "lecture_02",
    "config": {"title": "Lecture 2: Models"},
    "rubric": "### T1. Priors\n\n- **Description:** Priors.\n- **Importance:** core\n",
    "bot_notes": "Use lecture-native wording.",
    "slides": "Posterior is proportional to prior times likelihood, then divided by evidence.",
    "handout": "Evidence is the normalizing factor.",
    "notebook": "",
}


def _start_session(client, lecture_id="lecture_02"):
    response = client.post(
        "/start_session",
        json={"student_id": "student_001", "lecture_id": lecture_id},
    )
    assert response.status_code == 200, response.text
    return response.json()["session_id"]


def _mock_openai_dialogue(
    *,
    top_classification="technical_request",
    recommended_policy="provide_technical_support",
    reply_text="Which of these are continuous, categorical, and ordinal?",
):
    classifier_resp = mock.MagicMock()
    probs = {
        "content_answer": 0.05,
        "content_question": 0.05,
        "technical_request": 0.85,
        "meta_request": 0.03,
        "off_task": 0.02,
    }
    probs[top_classification] = 0.85
    classifier_resp.choices[0].message.content = j.dumps({
        "top_classification": top_classification,
        "class_probabilities": probs,
        "recommended_policy": recommended_policy,
        "policy_confidence": 0.80,
        "short_reason": "Mocked for diagnostics.",
    })

    dialogue_resp = mock.MagicMock()
    dialogue_resp.choices[0].message.content = j.dumps({
        "assistant_message": reply_text,
        "updated_state": {"topics_covered": [], "mastery": {}, "evidence_notes": {}, "current_line_status": "productive"},
    })

    mock_client = mock.MagicMock()
    mock_client.chat.completions.create.side_effect = [classifier_resp, dialogue_resp] * 10
    return mock.patch("openai.OpenAI", return_value=mock_client)


def test_guess_question_level_and_near_duplicate():
    assert guess_question_level("If a study changes the measurement, how would the conclusion change?") == 5
    assert guess_question_level("Which of these are continuous, categorical, and ordinal?") == 1
    assert is_near_duplicate_question(
        "Which of these are continuous, categorical, and ordinal?",
        "Which variables are continuous, categorical, and ordinal?"
    ) is True


def test_detect_external_terms_flags_known_source_drift():
    assistant = "The posterior kernel is prior times likelihood before normalization."
    user = "Can you explain that?"
    assert detect_external_terms(assistant, user, LECTURE_PACKAGE) == ["posterior kernel"]


def test_diagnose_harder_request_attributes_realization_failure():
    record = DiagnosticTurnRecord(
        session_id="s1",
        lecture_id="lecture_02",
        lecture_title="Lecture 2: Models",
        turn_index=0,
        user_message="That is too easy. Ask me something harder that gets points.",
        assistant_message="Which of these are continuous, categorical, and ordinal?",
        recent_messages=[],
        classifier={"top_classification": "technical_request"},
        policy_decision={"effective_policy": "provide_technical_support"},
        effective_policy="provide_technical_support",
        prompt_template_name="tutor_prompt.md",
        tutor_mode="technical_request",
        action_hint={"recommended_action": "escalate", "challenge_level": 5, "reason_code": "student_requested_harder"},
        challenge_level=5,
        current_topic_id="T1",
        target_topic_id="T1",
        ended_with_content_question=True,
        repetition_complaint=False,
        switched_topics=False,
    )

    report = diagnose_turn_records(LECTURE_PACKAGE, [record])

    harder_cases = [case for case in report.cases if case.kind == "harder_request"]
    assert len(harder_cases) == 1
    assert harder_cases[0].score == "fail"
    assert harder_cases[0].likely_cause == "tutor_realization"


def test_export_session_diagnostics_writes_reports(client, tmp_path):
    session_id = _start_session(client)
    with _mock_openai_dialogue():
        response = client.post(
            "/send_message",
            json={"session_id": session_id, "message": "That is too easy. Ask me something harder that gets points."},
        )
    assert response.status_code == 200

    db = next(app.dependency_overrides[db_module.get_db]())
    try:
        report = export_session_diagnostics(
            db,
            session_id,
            output_json=tmp_path / "diag.json",
            output_markdown=tmp_path / "diag.md",
        )
    finally:
        db.close()

    assert (tmp_path / "diag.json").exists()
    assert (tmp_path / "diag.md").exists()
    assert report.case_counts["harder_request"]["fail"] == 1
