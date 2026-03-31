let sessionId = null;

const studentIdInput = document.getElementById("studentId");
const lectureIdInput = document.getElementById("lectureId");
const startSessionBtn = document.getElementById("startSessionBtn");

const messageInput = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");

const transcript = document.getElementById("transcript");
const errorBox = document.getElementById("errorBox");
const sessionInfo = document.getElementById("sessionInfo");

const gradeBtn = document.getElementById("gradeBtn");
const reportBtn = document.getElementById("reportBtn");
const restartBtn = document.getElementById("restartBtn");

function showError(msg) {
  errorBox.textContent = msg;
  errorBox.classList.remove("hidden");
}

function clearError() {
  errorBox.textContent = "";
  errorBox.classList.add("hidden");
}

function appendMessage(role, content) {
  const row = document.createElement("div");
  row.className = "msg " + role;

  const who = document.createElement("strong");
  who.textContent = role === "user" ? "You" : "Assistant";

  const text = document.createElement("span");
  text.textContent = ": " + content;

  row.appendChild(who);
  row.appendChild(text);
  transcript.appendChild(row);
  transcript.scrollTop = transcript.scrollHeight;
}

async function startSession() {
  clearError();

  const student_id = studentIdInput.value.trim();
  const lecture_id = lectureIdInput.value.trim() || "lecture_01";

  if (!student_id) {
    showError("Student ID is required.");
    return;
  }

  try {
    const res = await fetch("/start_session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ student_id, lecture_id }),
    });

    if (!res.ok) {
      const body = await res.text();
      showError("Failed to start session (" + res.status + "): " + body);
      return;
    }

    const data = await res.json();
    sessionId = data.session_id;
    sessionInfo.textContent = "Active session: " + sessionId;

    // Clear any previous transcript before starting fresh
    transcript.innerHTML = "";

    messageInput.disabled = false;
    sendBtn.disabled = false;
    messageInput.focus();

    if (data.message) {
      appendMessage("assistant", data.message);
    }
  } catch (err) {
    showError("Network error while starting session: " + err.message);
  }
}

async function sendMessage() {
  clearError();

  if (!sessionId) {
    showError("Start a session first.");
    return;
  }

  const message = messageInput.value.trim();
  if (!message) return;

  // Clear input immediately for UX, but only append to transcript after success
  messageInput.value = "";
  sendBtn.disabled = true;

  try {
    const res = await fetch("/send_message", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message }),
    });

    if (!res.ok) {
      const body = await res.text();
      messageInput.value = message; // restore on failure
      showError("Failed to send message (" + res.status + "): " + body);
      return;
    }

    const data = await res.json();
    appendMessage("user", message);
    appendMessage("assistant", data.message || "[no reply]");
  } catch (err) {
    messageInput.value = message; // restore on failure
    showError("Network error while sending message: " + err.message);
  } finally {
    sendBtn.disabled = false;
    messageInput.focus();
  }
}

async function getGrade() {
  clearError();
  if (!sessionId) { showError("Start a session first."); return; }

  try {
    const res = await fetch("/get_grade", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });
    if (!res.ok) {
      const body = await res.text();
      showError("Failed to get grade (" + res.status + "): " + body);
      return;
    }
    const data = await res.json();
    const lines = [
      "Current grade: " + data.grade + "/100",
      data.explanation,
      data.missing_topics && data.missing_topics.length
        ? "Missing topics: " + data.missing_topics.join(", ")
        : "No missing topics identified.",
    ];
    appendMessage("assistant", lines.join(" | "));
  } catch (err) {
    showError("Network error: " + err.message);
  }
}

async function generateReport() {
  clearError();
  if (!sessionId) { showError("Start a session first."); return; }

  try {
    const res = await fetch("/generate_report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });
    if (!res.ok) {
      const body = await res.text();
      showError("Failed to generate report (" + res.status + "): " + body);
      return;
    }
    const data = await res.json();
    appendMessage("assistant", data.report_text || "[No report text returned]");
  } catch (err) {
    showError("Network error: " + err.message);
  }
}

async function restartSession() {
  clearError();
  if (!sessionId) { showError("No active session to restart."); return; }

  try {
    const res = await fetch("/restart_session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        student_id: studentIdInput.value.trim(),
        lecture_id: lectureIdInput.value.trim() || "lecture_01",
      }),
    });
    if (!res.ok) {
      const body = await res.text();
      showError("Failed to restart session (" + res.status + "): " + body);
      return;
    }
    const data = await res.json();
    sessionId = data.session_id;
    sessionInfo.textContent = "Active session: " + sessionId;

    // Clear transcript for fresh start
    transcript.innerHTML = "";
    if (data.message) appendMessage("assistant", data.message);
  } catch (err) {
    showError("Network error: " + err.message);
  }
}

startSessionBtn.addEventListener("click", startSession);
sendBtn.addEventListener("click", sendMessage);
messageInput.addEventListener("keydown", function (e) {
  if (e.key === "Enter") sendMessage();
});
gradeBtn.addEventListener("click", getGrade);
reportBtn.addEventListener("click", generateReport);
restartBtn.addEventListener("click", restartSession);
