# Implementation Spec (v1)

This document defines the exact behavior of the lecture-bot system.
All implementation should follow this specification.

---

## 1. API (RPC-style)

### 1.1 Start Session

POST /start_session

Request:

```json
{
  "student_id": "string",
  "lecture_id": "string"
}
```

Response:

```json
{
  "session_id": "string",
  "message": "string"
}
```

Behavior:

* Create session
* Initialize state
* Sample rubric topics

---

### 1.2 Send Message

POST /send_message

Request:

```json
{
  "session_id": "string",
  "message": "string"
}
```

Response:

```json
{
  "message": "string",
  "session_active": true
}
```

Behavior:

* Check timeout
* Append message
* Run bot engine
* Update state

---

## 2. Control Actions

Triggered via UI buttons (preferred) or commands.

### 2.1 Get Current Grade

Returns:

```json
{
  "grade": 0-100,
  "explanation": "string",
  "missing_topics": ["string"]
}
```

Uses dedicated grading prompt.

---

### 2.2 Generate Final Report

Returns:

```json
{
  "report_text": "string",
  "report_json": {
    "session_id": "string",
    "student_id": "string",
    "timestamp": "ISO",
    "final_grade": number
  }
}
```

Uses dedicated grading/report prompt.

---

### 2.3 Restart Session

* Ends current session
* Creates new session

---

## 3. Session State

Stored per session:

```json
{
  "topics_sampled": [],
  "topics_covered": [],
  "mastery": {},
  "turn_count": 0,
  "confidence": 0.0
}
```

---

## 4. Grading Model

Topic-weighted scoring:

* 55
* 25
* 13
* 4
* 3

Rules:

* Select best 5 topics
* Score each independently
* Sum and round down

---

## 5. Bot Engine Contract

### Input

* system prompt
* rubric (full)
* lecture content (full)
* session state
* recent messages

### Output

```json
{
  "assistant_message": "string",
  "updated_state": {}
}
```

Responsibilities:

* Ask next question
* Evaluate answer
* Update mastery
* Move topic if needed

---

## 6. Data Model

### sessions

* session_id
* student_id
* lecture_id
* started_at
* ended_at
* current_grade

### messages

* id
* session_id
* role
* content
* timestamp

### session_state

* session_id
* state_json

### grade_events (optional)

* session_id
* timestamp
* type
* grade

---

## 7. Constraints

* No authentication
* No tokens
* No resume
* Text-only
* Full rubric each turn

---

## 8. Extensions (future)

* Token system
* Admin UI
* Multi-lecture routing
* Figure handling
* REST API
