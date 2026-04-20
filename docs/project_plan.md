# Project Plan — Lecture Bot

## Purpose

Build a lecture-specific educational chatbot for a Bayesian statistics course.

* Primary: graded weekly review tool
* Secondary: optional study tool

Each lecture will eventually have its own bot. This repo builds the first prototype.

---

## Pedagogical Principles

* Feels like teaching, not testing
* Short-answer, conceptual dialogue
* Socratic when helpful
* Handles partial/uncertain answers productively
* Redirects off-topic questions back to lecture

---

## Interaction Model

* Chat-first UI
* English only
* No progress bar or question counter
* Grade is shown on request

### Control Actions (allowed in v1)

* Get current grade
* Generate final report
* Restart session

These may be implemented as minimal buttons (preferred) or commands.

---

## Grading Model

* One-pass live grading
* Student can request current grade anytime and continue
* Current grade = “If you stopped now, what would your final grade be?”

### Topic-weighted scoring

Top 5 topics only:

* Best: 55
* Second: 25
* Third: 13
* Fourth: 4
* Fifth: 3

Rules:

* Topics scored independently
* Final grade = sum of best demonstrated topics
* Round down
* Full 100 requires mastery down to the 5th topic

---

## Session / Submission Model

* Student enters **student ID only**
* No login, no tokens
* Unlimited sessions
* No graded/practice distinction

System stores:

* session_id
* student_id
* timestamp
* transcript
* grade

Student submits chosen session in Moodle.

Minimal validation:

* session exists
* belongs to student
* grade matches

---

## Lecture Package Model

Each lecture contains:

* rubric.md
* slides.md
* handout.md
* minutes.json
* lecture_config.json
* optional bot_notes.md
* optional notebook.md and transcript.md for build/admin workflows

Rules:

* Markdown/text only
* Figures ignored in v1
* Full rubric passed to model
* Runtime lecture context is selected by `lectures/config.json`

---

## Infrastructure

Current target:

* Ubuntu 24.04 LTS server
* systemd + Uvicorn + Nginx
* SQLite database
* repo-default student path `/bot`
* repo-default admin path `/bot-admin`
* production student path intended as `/stats`
* production admin path intended as `/stats-admin`

Important deployment note:

* Prefix-aware URLs are supported through `LECTURE_BOT_STUDENT_ROOT_PATH`, `LECTURE_BOT_ADMIN_ROOT_PATH`, and matching Uvicorn `--root-path` values.

---

## Repository Strategy

* Public repo for code/spec
* Private/local only:

  * .env / API keys
  * student roster
  * logs / exports

---

## Development Approach

* Prototype first
* Iterate quickly
* Refactor later if needed

Workflow:

* Spec defined here
* Implementation via Codex
* Review via ChatGPT

---

## Milestones

1. App skeleton running
2. Session + logging working
3. Bot interaction working (Lecture 1)
4. Deployment on server
5. Lecture 2 added

---

## Risks

* Grading feels arbitrary
* Bot becomes evaluative instead of pedagogical
* Content pipeline messy
* Deployment friction

Mitigation: iterate quickly and test manually early

---

## Timeline

* First 2 lectures ready before end of Passover
* Third lecture following week
