import unittest.mock as mock

import app.db as db_module
import app.models as models
from app.main import app
from app.turn_reconstruction import reconstruct_session_turn_inputs


def start_session(client):
    response = client.post(
        "/start_session",
        json={"student_id": "student_001", "lecture_id": "lecture_01"},
    )
    assert response.status_code == 200, response.text
    return response.json()["session_id"]


def _mock_openai_dialogue(reply_text="Test reply."):
    import json as j

    classifier_resp = mock.MagicMock()
    classifier_resp.choices[0].message.content = j.dumps({
        "top_classification": "content_answer",
        "class_probabilities": {
            "content_answer": 0.80,
            "content_question": 0.10,
            "technical_request": 0.05,
            "meta_request": 0.03,
            "off_task": 0.02,
        },
        "recommended_policy": "respond",
        "policy_confidence": 0.80,
        "short_reason": "Student is answering lecture content.",
    })

    dialogue_resp = mock.MagicMock()
    dialogue_resp.choices[0].message.content = j.dumps({
        "assistant_message": reply_text,
        "updated_state": {"topics_covered": [], "mastery": {}, "evidence_notes": {}, "turn_count": 1},
    })

    mock_client = mock.MagicMock()
    mock_client.chat.completions.create.side_effect = [classifier_resp, dialogue_resp] * 5
    return mock.patch("openai.OpenAI", return_value=mock_client)


def test_reconstruct_session_turn_inputs_uses_exact_audit_when_available(client):
    session_id = start_session(client)
    with _mock_openai_dialogue():
        client.post("/send_message", json={"session_id": session_id, "message": "Hello"})

    db = next(app.dependency_overrides[db_module.get_db]())
    packet = reconstruct_session_turn_inputs(db, session_id)

    assert len(packet["turns"]) == 1
    turn = packet["turns"][0]
    assert turn["prompt_reconstruction_kind"] == "exact_from_audit"
    assert turn["prompt_template_name"] == "tutor_prompt.md"
    assert turn["user_message"] == "Hello"
    assert turn["unrecoverable_prompt_fields"] == []


def test_reconstruct_session_turn_inputs_turn_zero_is_exact_without_audit(client):
    session_id = start_session(client)
    with _mock_openai_dialogue():
        client.post("/send_message", json={"session_id": session_id, "message": "Hello"})

    db = next(app.dependency_overrides[db_module.get_db]())
    db.query(models.DialogueTurnAuditModel).filter(
        models.DialogueTurnAuditModel.session_id == session_id
    ).delete()
    db.commit()

    packet = reconstruct_session_turn_inputs(db, session_id)

    assert len(packet["turns"]) == 1
    turn = packet["turns"][0]
    assert turn["prompt_reconstruction_kind"] == "exact_initial_turn"
    assert turn["routing_state_before_turn_exact"]["turn_count"] == 0
    assert "Recent conversation:" in turn["rendered_system_prompt"]
