# Lecture Bot Thin Interface Project Plan

## Current locked decisions

### Product scope

* First build is a prototype for **one lecture bot**, but the architecture should later support one bot per lecture across the course.
* Primary goal: **graded weekly review tool**.
* Secondary goal: optional study tool.
* Students may keep using the bot outside the Moodle grading window; Moodle remains authoritative for deadlines, penalties, and which submission counts.

### Interaction model

* English only.
* Chat-window experience, not quiz-form experience.
* Short-answer conceptual dialogue.
* The bot should feel like it is **teaching**, not merely judging.
* It may answer brief side questions, but should redirect back to the current lecture review.
* No explicit UI buttons in v1; special chat commands will have privileged meaning.
* No visible progress bar or question counter in v1.
* Grade shown only on request.

### Grading model

* One-pass live grading.
* Student can request current grade at any time and continue working afterward.
* Current grade means: **if the session ended now, what final grade would this session receive?**
* Final report should include:

  * grade
  * material covered
  * extent of mastery
  * suggestions for review
* The bot should sample topics randomly from the lecture rubric.
* Desired flow: work toward mastery, but move on if progress stalls or the user asks to move on.
* No hard stop in v1; prefer grade saturation over strict turn limits.
* Rough expected interaction length: around 20-30 exchanges, to be refined through testing.

### Session / submission model

* Student enters **student ID only**.
* No login.
* No token system in v1.
* No distinction between graded and practice mode in v1.
* Students may do unlimited sessions at any time.
* The system logs each session.
* The student submits the session of their choosing in Moodle.
* Minimal anti-cheating check is:

  * submitted session exists
  * submitted session belongs to that student ID
  * submitted grade matches stored session result
* Therefore the final report must include at least:

  * student ID
  * session ID
  * timestamp
  * grade

### Lecture package model

* Each lecture bot is driven by:

  * slides
  * handout
  * notebook
  * mastery rubric
* App reads **processed markdown/text files only**.
* v1 is **text-only**.
* Figures are ignored in v1 unless manually represented in text.
* Lecture folder format:

  * `lecture_config.json`
  * `rubric.md`
  * `slides.md`
  * `handout.md`
  * `notebook.md`
  * optional `bot_notes.md`
* Pass the **entire rubric** to the model.
* Pass the **full concatenated lecture material** to the model.
* Keep at least partial **explicit session state** in code.

### Infrastructure / operations

* Server: Fedora 43 Linux machine at university.
* Access: over VPN.
* User has sudo.
* Working directly on the Linux server is acceptable and preferred for speed.
* Command-line administration is acceptable in v1.
* No admin web UI required in v1.
* Logs retained for current semester only.
* Full transcripts may be stored on the machine.
* Session restart allowed freely.
* Interrupted sessions should not resume in v1; timeout should lead to restart/new session behavior.

### Development approach

* Prototype first, refactor later if successful.
* Likely private GitHub repository.
* Main coding by user with Codex/Copilot support.
* Dev/staging mode desirable before student rollout.
* Automated tests are useful when they help implementation stay on track.
* Near-term deployment target: first two lecture bots ready before end of Passover holiday; third lecture the following week.

## Working notes on source prompts

* Existing `mastery_rubric_prompt.md` already assumes short-session assessable clusters, evidence standards, and sampled-session grading.
* Existing `educational_bot_prompt.md` already assumes full-rubric use, Socratic short-answer dialogue, explicit internal mastery state, sampled topics, current-grade reporting, and structured final report.
* These prompts can therefore serve as conceptual grounding for the implementation, even though the deployed system will not be a GPT-builder package.

## Immediate next stages

1. Update the canvas to reflect locked decisions.
2. Create a repository that can hold the plan and later the living implementation spec.
3. Start building the living implementation spec inside that repository and this canvas.

## 1. Project purpose

Build the first working prototype of a **lecture-specific educational chatbot** for the Bayesian statistics course.

This first bot is a prototype for a family of lecture bots. In the full course, each lecture will eventually have its own bot. The first implementation should therefore be built as:

* a **working prototype for Lecture 1**
* but with an internal structure that can later support Lecture 2, Lecture 3, and so on

Primary goal:

* a **graded weekly review tool**

Secondary goal:

* an **optional study tool** that students may continue using outside the main grading window

Pedagogical goal:

* the experience should feel like a **real chatbot that teaches**, not like a disguised quiz form
* interaction should be **short-answer, conceptual, helpful, and Socratic when useful**
* the bot should be able to grade, but grading should not dominate the feel of the interaction

Deployment goal:

* get a **working prototype running quickly** on the university Linux machine
* prioritize a usable prototype over architecture perfection

---

## 2. Product decisions already made

### 2.1 Interaction model

* Chat window interface
* English only
* Short-answer interaction only
* No explicit quiz buttons in v1
* No visible progress bar
* No visible remaining question count
* Grade shown only when the student asks for it
* Special chat commands will be interpreted by the system

### 2.2 Grading model

* One-pass live grading
* Student can ask for current grade during the session
* Meaning of current grade:

  * **If you stopped now, what would the final report grade be?**
* Student may continue after asking for grade
* Session should exhibit **grade saturation** rather than a hard stop
* Material should be sampled randomly from the lecture rubric
* The bot should be forgiving and pedagogically helpful when students answer partially, vaguely, or unevenly

### 2.3 Final report contents

The final report should include:

* grade
* material covered
* extent of mastery
* suggestions for review

### 2.4 Lecture content package

Each lecture bot will be built from:

* slides
* handout
* notebook
* mastery rubric

For now, the rubric will be prepared separately and supplied as an input.

### 2.5 Operations and access

* students access the app over VPN
* server runs on Fedora 43 Linux machine at the university
* you have sudo access
* command-line administration is acceptable for v1
* no admin web UI required in v1
* storage should be kept only for the current semester
* transcripts and logs may be stored on the machine
* session restart is allowed, freely
* no resume of interrupted sessions in v1
* Moodle will remain the authoritative grading system
* this system mainly needs to generate logs/results that can be transferred into Moodle

### 2.6 Development style

* prototype first
* work directly on Linux server
* use GitHub private repo
* coding mostly by you with Codex/Copilot support
* dev/staging mode is desirable
* automated tests should exist when useful, mainly to keep implementation on track

---

## 3. Open design decisions to settle early

These must be decided during the requirements/spec phase before too much coding.

### 3.1 Gating model

We have **not yet decided** the final gating mechanism.

Main options:

#### Option A: student ID only

Pros:

* simplest user experience
* no token distribution process
* naturally matches Moodle identities

Cons:

* easy impersonation if someone knows another student's ID
* no clean distinction between graded window and open practice access

#### Option B: token + student ID

Pros:

* supports graded attempt windows cleanly
* can separate official and unofficial sessions
* gives more control over lecture/week availability

Cons:

* more admin work
* token sharing is still possible
* more moving parts

#### Option C: token only

Pros:

* easiest to implement as gated sessions

Cons:

* poor identity integrity unless separately tied back to student ID

**Provisional recommendation for v1:**

* keep design compatible with either
* but implement **student ID + session mode** first
* session mode could be something like `graded` vs `practice`
* later, tokens can be layered on if needed

### 3.2 Storage format for lecture content

Need to decide how lecture bots load their inputs.

Practical v1 recommendation:

* store each lecture as a folder containing:

  * `lecture_config.json`
  * `rubric.md`
  * `slides.txt` or extracted markdown/text
  * `handout.txt` or markdown
  * `notebook.txt` or markdown summary
  * optional prompt fragments

This is simpler than trying to parse PowerPoint or notebook formats live.

### 3.3 Official grading flow

Since Moodle is authoritative, define whether the bot should output:

* a final numeric grade only
* or a structured result file / CSV / JSON record to import into Moodle manually

**Provisional recommendation for v1:**

* store structured session results in SQLite
* write an export script that produces CSV suitable for Moodle or manual upload

---

## 4. Recommended v1 architecture

## 4.1 High-level architecture

Recommended stack:

* **FastAPI** backend
* **simple chat-style frontend** served by the backend
* **SQLite** database for session logs and results
* **OpenAI API** as the only model backend for v1
* **uvicorn** application server
* **systemd** for process management
* **Nginx** as reverse proxy
* optional **Docker later**, not required for first working version

## 4.2 Why this architecture

### FastAPI

Use FastAPI because:

* the app is fundamentally request/response based
* structured JSON endpoints are natural for session handling
* it is lightweight but more disciplined than Flask
* it is still small enough for a prototype

### SQLite

Use SQLite because:

* no separate DB server required
* enough for this project scale
* easy to inspect manually
* easy to back up
* simple deployment

### Backend-served frontend

Use a minimal backend-served web UI because:

* simplest deployment
* no separate frontend build chain needed initially
* still allows a chat-like experience

### Nginx + systemd

Use Nginx + systemd because:

* normal, stable Linux deployment pattern
* works well on a university Linux machine
* easy to manage once set up

---

## 5. Target v1 feature set

## 5.1 Student-facing features

### Required for v1

* enter student ID
* select or receive lecture bot context (probably one lecture only in v1)
* chat with the lecture bot
* bot gives short conceptual prompts and follow-up questions
* bot grades progressively in the background
* student may type special commands such as:

  * `Give current grade`
  * `Produce final report`
  * `Restart session`
* bot answers brief content side-questions and returns to task
* bot creates full final report

### Not required for v1

* multi-lecture menu
* visual progress bar
* instructor dashboard
* resume interrupted session
* polished analytics UI
* SSO
* automatic Moodle integration

## 5.2 Instructor/admin features

### Required for v1

* create lecture package folder/files
* register a lecture package with the app
* inspect logs in SQLite or exported CSV
* export grades/results/transcripts
* run in dev and prod mode
* reset/delete stored session data manually

### Not required for v1

* web-based admin interface
* token generation UI
* automatic lecture upload via browser

---

## 6. Session and grading behavior specification

## 6.1 Session structure

Each session should have:

* student ID
* lecture ID
* mode (`graded` or `practice`, even if only one mode is used initially)
* start timestamp
* end timestamp
* transcript log
* internal mastery state
* current grade estimate
* final report state

## 6.2 Desired grading behavior

The grading system should:

* estimate mastery from the conversation as it evolves
* use **coverage + demonstrated understanding**, not just correctness of isolated answers
* saturate rather than requiring a fixed number of turns
* allow improvement after mistakes
* allow a meaningful grade estimate midstream
* behave helpfully when the student is partial or uncertain

## 6.3 Special command behavior

At minimum support these:

### `Give current grade`

Return:

* current estimated final grade
* brief note about what has and has not yet been demonstrated

### `Produce final report`

Return:

* final grade
* material covered
* extent of mastery
* suggestions for review
* note that this report reflects current conversation only

### `Restart session`

Behavior:

* discard current conversation state
* start a fresh new session row/log
* preserve prior old session logs in database

---

## 7. Data model for v1

## 7.1 Database tables

### `lectures`

Fields:

* id
* lecture_code
* title
* content_path
* active
* created_at
* updated_at

### `sessions`

Fields:

* id
* student_id
* lecture_id
* mode
* status
* started_at
* ended_at
* current_grade_estimate
* final_grade
* final_report_text
* dev_flag

### `messages`

Fields:

* id
* session_id
* role (`system`, `user`, `assistant`, `internal`)
* content
* created_at
* metadata_json

### `session_state`

Fields:

* session_id
* state_json
* updated_at

### optional `exports`

Fields:

* id
* export_type
* path
* created_at

## 7.2 State JSON contents

Suggested `state_json` contents:

* sampled rubric topics
* covered topics
* mastery estimates by topic
* internal notes for grading
* flags for report produced
* count of substantive turns
* saturation indicators

---

## 8. Project phases

# Phase 0. Define exact goals and constraints

## Goal

Turn current decisions into an implementation-ready specification.

## Tasks

1. Confirm architecture decisions

   * FastAPI
   * SQLite
   * simple backend-served frontend
   * Nginx + systemd
2. Decide provisional gating model for v1

   * recommendation: student ID only + mode field
3. Define the initial command vocabulary
4. Define lecture package file structure
5. Define what counts as a graded session in v1
6. Define export format for Moodle/manual grade transfer
7. Define dev vs prod behavior

## Deliverables

* short requirements spec
* lecture package format spec
* session flow spec
* command spec

---

# Phase 1. Prepare the Linux server environment

## Goal

Create a safe, reproducible development and deployment environment on the Fedora machine.

## Step-by-step

### 1. Inspect current server state

Run and record:

* hostname
* available domain/VPN hostname
* whether Nginx is installed
* whether Docker is installed
* whether Python is system-wide available
* whether pixi is available and current version
* open ports currently in use

Commands to run:

* `hostnamectl`
* `ip addr`
* `ss -tulpn`
* `which nginx`
* `which docker`
* `python --version`
* `pixi --version`

### 2. Create project directory structure

Suggested layout:

```text
/opt/lecture-bot/
  app/
  data/
  lectures/
  scripts/
  logs/
  backups/
  .env
```

Alternative if you prefer home-directory deployment:

```text
~/projects/lecture-bot/
```

### 3. Create Git repository

* create private GitHub repo
* clone to server
* create branches:

  * `main`
  * `dev`

### 4. Create Python environment

Prefer v1 with **pixi** if convenient for you.

Decide whether to use:

* pixi environment
* or Python venv

Recommended packages likely needed:

* fastapi
* uvicorn
* jinja2
* sqlalchemy
* aiosqlite or sqlite support through SQLAlchemy
* pydantic
* python-dotenv
* openai
* pytest
* httpx

### 5. Add secret management

* create `.env`
* store OpenAI API key there
* never commit it
* confirm app can read it

### 6. Create `.gitignore`

Include:

* `.env`
* `__pycache__/`
* `.pytest_cache/`
* local database files
* logs
* generated exports

## Deliverables

* working project directory
* Git repo connected to GitHub
* runnable environment on server
* API key loaded securely

---

# Phase 2. Define the v1 app skeleton

## Goal

Create the minimal runnable application structure before adding bot logic.

## Tasks

### 1. Backend package layout

Suggested structure:

```text
app/
  main.py
  config.py
  db.py
  models.py
  schemas.py
  lecture_loader.py
  session_manager.py
  bot_engine.py
  prompts.py
  commands.py
  routes/
    web.py
    api.py
  templates/
    chat.html
  static/
    style.css
    chat.js
```

### 2. Add basic FastAPI app

Must support:

* health endpoint
* root route
* simple chat page route
* API endpoint for sending a message

### 3. Add config system

Settings should include:

* app mode (`dev`, `prod`)
* database path
* OpenAI API key
* lecture content root path
* session timeout
* logging settings

### 4. Add database initialization code

* create SQLite database
* create tables automatically
* add a script to initialize/reset DB

## Deliverables

* app starts locally on server
* homepage loads
* database initializes successfully

---

# Phase 3. Create lecture package format and loader

## Goal

Make lecture-specific bots possible without hardcoding lecture content into Python.

## Tasks

### 1. Define lecture folder structure

Suggested:

```text
lectures/
  lecture_01/
    lecture_config.json
    rubric.md
    slides.md
    handout.md
    notebook.md
    system_notes.md
```

### 2. Define `lecture_config.json`

Should include:

* lecture id
* lecture title
* course code
* active status
* command behavior flags
* optional grading weights
* prompt settings

### 3. Implement lecture loader

Loader should:

* read lecture package files
* validate required files exist
* convert them into an internal lecture object
* fail clearly when package is incomplete

### 4. Create first lecture package manually

Start with Lecture 1 only.
Use converted/clean text inputs, not live document parsing.

## Deliverables

* one lecture package on disk
* lecture loader test passes
* lecture metadata can be registered in DB

---

# Phase 4. Implement session creation and chat logging

## Goal

Support real sessions before any AI behavior is added.

## Tasks

### 1. Session start flow

Student opens page and enters:

* student ID

System then:

* creates new session row
* associates lecture ID
* writes initial state
* logs system startup messages

### 2. Message storage

Each message sent/received is written to `messages`

### 3. Session timeout logic

Since sessions should not resume after interruption:

* define timeout threshold, e.g. 15-20 minutes of inactivity
* if exceeded, new message triggers a new session or asks student to restart

### 4. Restart behavior

Implement restart command as:

* close current session
* create new session
* preserve old log

## Deliverables

* working session creation
* message persistence
* timeout/restart logic skeleton

---

# Phase 5. Implement the frontend chat interface

## Goal

Create a minimal but usable chatbot-like web UI.

## Tasks

### 1. Build initial HTML page

Should show:

* lecture title
* student ID
* scrolling chat area
* text input box
* send action

### 2. Build minimal JS behavior

* submit message asynchronously
* append user message
* append bot message
* preserve chat in current page session
* display errors gracefully

### 3. Keep styling minimal

* simple chat bubble structure
* readable typography
* no overdesign

### 4. Add initial system greeting

Should explain:

* purpose of the bot
* that it is a lecture review assistant
* that special commands are available
* that it can provide current grade and final report on request

## Deliverables

* usable chat page
* asynchronous message flow works end-to-end

---

# Phase 6. Implement command parsing

## Goal

Support privileged phrases with special system behavior.

## Commands for v1

* `Give current grade`
* `Produce final report`
* `Restart session`

## Tasks

### 1. Implement command detector

* exact-match first
* optionally case-insensitive normalized matching

### 2. Route commands separately from normal content

* current grade handler
* final report handler
* restart handler

### 3. Make non-command input go through normal bot flow

## Deliverables

* commands recognized reliably
* command unit tests pass

---

# Phase 7. Implement the bot engine

## Goal

Create the lecture-review behavior and live grading logic.

## Design principle

The bot engine should be split into two parts:

### A. Session orchestration layer

Responsible for:

* current lecture context
* current sampled topics
* current mastery state
* deciding what kind of move comes next

### B. LLM call layer

Responsible for:

* generating the next assistant message
* updating mastery estimate from dialogue
* generating reports

## Tasks

### 1. Define internal prompt architecture

Suggested prompt components:

* core system prompt for course bot behavior
* lecture-specific context from lecture package
* rubric summary
* current session state summary
* recent transcript window
* specific task instruction for this turn

### 2. Implement topic sampling

At session start:

* sample subset of rubric topics
* store sampled topics in session state

### 3. Implement mastery state update

After each student response, update internal state for:

* coverage
* demonstrated understanding
* misconceptions observed
* confidence of grade estimate

### 4. Implement response behavior

Bot should:

* be brief
* be helpful
* respond to what student actually said
* ask the next useful conceptual question
* redirect digressions back to lecture topic

### 5. Implement current-grade generation

Should return:

* current numeric estimate
* concise rationale
* missing areas not yet shown

### 6. Implement final-report generation

Should synthesize:

* grade
* covered material
* extent of mastery
* suggestions for review

## Deliverables

* bot can conduct a full session for one lecture
* current grade works
* final report works

---

# Phase 8. Add testing

## Goal

Add enough testing to keep implementation trustworthy and editable.

## Test categories

### 1. Unit tests

* lecture loader
* command parser
* session timeout logic
* restart behavior
* state update helpers

### 2. Integration tests

* start session
* send normal message
* request current grade
* request final report
* restart session

### 3. Manual pedagogical tests

Performed by you and TA:

* does it feel like teaching?
* does it stay on lecture scope?
* do grades feel sensible?
* does it avoid feeling like a cloze quiz in disguise?

### 4. Logging tests

* transcript written correctly
* final report saved correctly
* export script outputs valid CSV

## Deliverables

* basic test suite
* manual acceptance checklist

---

# Phase 9. Deployment on the Fedora server

## Goal

Run the app reliably behind a reverse proxy.

## Tasks

### 1. Run app locally first

* launch uvicorn bound to localhost
* test with browser over SSH tunnel or local VPN access

### 2. Create systemd service

Example conceptual service responsibilities:

* starts app on boot
* restarts on failure
* points to project environment
* writes logs to journal

### 3. Configure Nginx

* reverse proxy from public/VPN hostname to uvicorn localhost port
* serve static assets if desired
* configure request size/timeouts conservatively

### 4. Decide HTTP vs HTTPS

Since students connect over VPN, plain HTTP may work technically, but HTTPS is still preferable if feasible.
Need to inspect what hostnames and certificates are possible on university infrastructure.

### 5. Firewall/network coordination

If needed, ask IT to open the required service path/port.

## Deliverables

* bot accessible in browser over VPN
* process survives reboot
* logs inspectable

---

# Phase 10. Export and operations scripts

## Goal

Support practical course use without an admin UI.

## Scripts to create

### 1. `register_lecture.py`

* register lecture package from folder path

### 2. `export_results.py`

* export sessions to CSV
* filter by lecture, date, mode, student ID

### 3. `delete_session.py`

* delete session data if needed

### 4. `reset_db.py` or dev equivalent

* clear development database safely

### 5. `list_sessions.py`

* inspect current usage quickly

## Deliverables

* working operational scripts

---

# Phase 11. Dev/staging and production separation

## Goal

Allow testing before student rollout.

## Recommended approach

### Dev mode

* separate SQLite DB
* separate lecture namespace or lecture IDs
* maybe separate hostname/path if easy
* debug logging enabled

### Prod mode

* production DB
* real lecture packages only
* less verbose logging

## Deliverables

* dev config
* prod config
* clear deployment switch instructions

---

# Phase 12. Pilot evaluation and iteration

## Goal

Evaluate whether the prototype actually works pedagogically.

## Pilot sequence

1. You test alone
2. TA tests
3. Optional grader/test student tests
4. Refine prompts, lecture package format, and grading behavior
5. Deploy for student use

## Evaluate on these criteria

* Is it fun enough?
* Does it feel educational?
* Are the grades sensible?
* Does it stay within lecture scope?
* Does current grade feel informative and not arbitrary?
* Is the session length reasonable?
* Does the bot recover gracefully from partial or odd student answers?

---

## 9. Acceptance criteria for the first working prototype

The first working prototype is successful if all of the following are true:

### Functional

* one lecture package can be loaded
* a student can open the chat page and start a session
* messages are logged
* the bot responds using lecture-specific context
* `Give current grade` works
* `Produce final report` works
* `Restart session` works
* results can be exported

### Pedagogical

* the interaction feels more like teaching than judging
* the bot samples content rather than marching rigidly through a script
* grades are sensible enough for pilot use
* brief side questions are answered and redirected appropriately

### Operational

* app runs on Fedora server
* app survives restart via systemd
* app is reachable over VPN
* logs are stored and inspectable

---

## 10. Immediate build order

This is the recommended concrete order to start working.

### Step 1

Write the short implementation spec:

* confirm v1 gating model
* confirm lecture package file structure
* confirm command list
* confirm final report structure

### Step 2

Prepare repo and environment on Linux server

### Step 3

Build app skeleton + database skeleton

### Step 4

Build lecture package loader and create Lecture 1 package

### Step 5

Build session creation + logging

### Step 6

Build chat UI

### Step 7

Implement command handling

### Step 8

Implement bot engine for one lecture

### Step 9

Test manually with you

### Step 10

Deploy behind Nginx/systemd

### Step 11

Test with TA

### Step 12

Refine and clone structure for Lecture 2

---

## 11. Suggested near-term milestone plan

## Milestone A: Running shell app on server

Success means:

* FastAPI app launches
* database created
* chat page renders

## Milestone B: Real non-AI session flow

Success means:

* session starts
* messages logged
* restart works

## Milestone C: Lecture-aware bot for Lecture 1

Success means:

* bot uses lecture files and rubric
* current grade and final report work

## Milestone D: Deployment usable over VPN

Success means:

* reachable by browser on university network/VPN
* stable enough for instructor testing

## Milestone E: Lecture 2 added

Success means:

* second lecture package added without architecture changes

---

## 12. Known risks

### Risk 1: grading feels arbitrary

Mitigation:

* keep explicit internal rubric state
* test with many transcripts
* refine report wording

### Risk 2: bot becomes too judge-like

Mitigation:

* prompt strongly toward helpful short teaching dialogue
* manual pedagogical testing

### Risk 3: content pipeline becomes messy

Mitigation:

* define lecture package format early
* store processed text, not raw files

### Risk 4: networking/deployment delays

Mitigation:

* first get full app running on localhost/server
* involve IT only after local deployment works

### Risk 5: session sprawl without limits

Mitigation:

* use grade saturation logic
* later add soft nudges toward final report

---

## 13. What we should do next

The next concrete task is:

# Create the short implementation spec

That spec should settle:

1. v1 gating/access model
2. lecture package file structure
3. exact special commands
4. final report format
5. dev vs prod distinction
6. whether the first prototype uses real OpenAI API calls immediately or a stub/mock bot first

Once that is written, we should move directly to server setup and repository initialization.
