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

  appendMessage("user", message);
  messageInput.value = "";

  try {
    const res = await fetch("/send_message", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message }),
    });

    if (!res.ok) {
      const body = await res.text();
      showError("Failed to send message (" + res.status + "): " + body);
      return;
    }

    const data = await res.json();
    appendMessage("assistant", data.message || "[no reply]");
  } catch (err) {
    showError("Network error while sending message: " + err.message);
  }
}

startSessionBtn.addEventListener("click", startSession);
sendBtn.addEventListener("click", sendMessage);
messageInput.addEventListener("keydown", function (e) {
  if (e.key === "Enter") sendMessage();
});

gradeBtn.addEventListener("click", function () {
  alert("Get current grade is not implemented yet.");
});
reportBtn.addEventListener("click", function () {
  alert("Generate final report is not implemented yet.");
});
restartBtn.addEventListener("click", function () {
  alert("Restart session is not implemented yet.");
});
