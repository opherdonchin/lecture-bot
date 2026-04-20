let sessionId = null;

function renderMath(el) {
  if (typeof renderMathInElement !== "undefined") {
    renderMathInElement(el, {
      delimiters: [
        { left: "\\(", right: "\\)", display: false },
        { left: "\\[", right: "\\]", display: true },
        { left: "$$", right: "$$", display: true },
      ],
      throwOnError: false,
    });
  }
}

const studentIdInput = document.getElementById("studentId");
const lectureIdInput = document.getElementById("lectureId");

// Populate lecture dropdown on load
fetch("/lectures")
  .then(r => r.json())
  .then(lectures => {
    lectures.forEach(id => {
      const opt = document.createElement("option");
      opt.value = id;
      opt.textContent = id.replace(/_/g, " ");
      lectureIdInput.appendChild(opt);
    });
  })
  .catch(() => {
    const opt = document.createElement("option");
    opt.value = "lecture_01";
    opt.textContent = "lecture 01";
    lectureIdInput.appendChild(opt);
  });
const startSessionBtn = document.getElementById("startSessionBtn");

const messageInput = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");

// Enter submits; Shift+Enter or Ctrl+Enter inserts a newline
messageInput.addEventListener("keydown", function (e) {
  if (e.key === "Enter" && !e.shiftKey && !e.ctrlKey) {
    e.preventDefault();
    sendMessage();
  }
});

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

function setSessionActive(active) {
  messageInput.disabled = !active;
  sendBtn.disabled = !active;
  gradeBtn.disabled = !active;
  reportBtn.disabled = !active;
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
  renderMath(row);
  transcript.scrollTop = transcript.scrollHeight;
  return row;
}

function appendThinking() {
  const row = document.createElement("div");
  row.className = "msg assistant thinking";
  const who = document.createElement("strong");
  who.textContent = "Assistant";
  const text = document.createElement("span");
  const dots = ["", ".", "..", "..."];
  let i = 0;
  text.textContent = ": thinking";
  const timer = setInterval(() => {
    i = (i + 1) % dots.length;
    text.textContent = ": thinking" + dots[i];
  }, 400);
  row._thinkingTimer = timer;
  row.appendChild(who);
  row.appendChild(text);
  transcript.appendChild(row);
  transcript.scrollTop = transcript.scrollHeight;
  const origRemove = row.remove.bind(row);
  row.remove = () => { clearInterval(timer); origRemove(); };
  return row;
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
    setSessionActive(true);
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

  // Show user message immediately before waiting for the response
  messageInput.value = "";
  sendBtn.disabled = true;
  const userRow = appendMessage("user", message);
  const thinkingRow = appendThinking();

  try {
    const res = await fetch("/send_message", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message }),
    });

    if (!res.ok) {
      const body = await res.text();
      thinkingRow.remove();
      userRow.remove();
      messageInput.value = message; // restore on failure
      showError("Failed to send message (" + res.status + "): " + body);
      return;
    }

    const data = await res.json();
    thinkingRow.remove();
    appendMessage("assistant", data.message || "[no reply]");
    if (data.final_report) {
      appendReportMessage(data.final_report);
    }
    if (data.session_active === false) {
      setSessionActive(false);
    }
  } catch (err) {
    thinkingRow.remove();
    userRow.remove();
    messageInput.value = message; // restore on failure
    showError("Network error while sending message: " + err.message);
  } finally {
    if (sessionId && !messageInput.disabled) {
      sendBtn.disabled = false;
    }
    messageInput.focus();
  }
}

async function getGrade() {
  clearError();
  if (!sessionId) { showError("Start a session first."); return; }

  appendMessage("user", "Get current grade");
  const thinkingRow = appendThinking();

  try {
    const res = await fetch("/get_grade", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });
    if (!res.ok) {
      const body = await res.text();
      thinkingRow.remove();
      showError("Failed to get grade (" + res.status + "): " + body);
      return;
    }
    const data = await res.json();
    thinkingRow.remove();
    appendGradeMessage(data);
  } catch (err) {
    thinkingRow.remove();
    showError("Network error: " + err.message);
  }
}

function appendGradeMessage(data) {
  const row = document.createElement("div");
  row.className = "msg assistant grade-card";

  const header = document.createElement("div");
  header.className = "grade-header";
  header.innerHTML = "Current grade: <strong>" + data.grade + " / 100</strong>";
  row.appendChild(header);

  if (data.explanation) {
    const exp = document.createElement("p");
    exp.className = "grade-explanation";
    exp.textContent = data.explanation;
    row.appendChild(exp);
  }

  appendInfoList(
    row,
    "Stronger areas",
    data.scored_topics || [],
    "No strong footholds yet."
  );
  appendInfoList(
    row,
    "Still to cover",
    data.missing_topics || [],
    "All sampled topics have some coverage."
  );

  transcript.appendChild(row);
  renderMath(row);
  transcript.scrollTop = transcript.scrollHeight;
}

function appendInfoList(container, label, items, emptyText) {
  const block = document.createElement("div");
  block.className = "info-block";

  const title = document.createElement("div");
  title.className = "info-title";
  title.textContent = label;
  block.appendChild(title);

  if (items && items.length > 0) {
    const list = document.createElement("ul");
    list.className = "info-list";
    for (const item of items) {
      const li = document.createElement("li");
      li.textContent = item;
      list.appendChild(li);
    }
    block.appendChild(list);
  } else {
    const empty = document.createElement("p");
    empty.className = "info-empty";
    empty.textContent = emptyText;
    block.appendChild(empty);
  }

  container.appendChild(block);
}

function appendStructuredReportText(container, reportText) {
  const lines = reportText.split(/\r?\n/);
  let currentList = null;

  function closeList() {
    currentList = null;
  }

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) {
      closeList();
      continue;
    }

    if (/^[-*]\s+/.test(line)) {
      if (!currentList) {
        currentList = document.createElement("ul");
        currentList.className = "report-list";
        container.appendChild(currentList);
      }
      const li = document.createElement("li");
      li.textContent = line.replace(/^[-*]\s+/, "");
      currentList.appendChild(li);
      continue;
    }

    closeList();
    const block = document.createElement("div");
    block.className = /:\s*$/.test(line) ? "report-section-title" : "report-line";
    block.textContent = line;
    container.appendChild(block);
  }
}

async function generateReport() {
  clearError();
  if (!sessionId) { showError("Start a session first."); return; }

  appendMessage("user", "Generate final report");
  const thinkingRow = appendThinking();

  try {
    const res = await fetch("/generate_report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });
    if (!res.ok) {
      const body = await res.text();
      thinkingRow.remove();
      showError("Failed to generate report (" + res.status + "): " + body);
      return;
    }
    const data = await res.json();
    thinkingRow.remove();
    appendReportMessage(data);
  } catch (err) {
    thinkingRow.remove();
    showError("Network error: " + err.message);
  }
}

function appendReportMessage(data) {
  const row = document.createElement("div");
  row.className = "msg assistant report-card";

  const header = document.createElement("div");
  header.className = "report-header";
  header.innerHTML = "Final Report &mdash; <strong>" + (data.report_json && data.report_json.final_grade != null ? data.report_json.final_grade + " / 100" : "") + "</strong>";
  row.appendChild(header);

  const reportText = data.report_text || "[No report text returned]";
  appendStructuredReportText(row, reportText);

  // Download button
  const dl = document.createElement("button");
  dl.className = "download-btn";
  dl.textContent = "Download report";
  dl.addEventListener("click", function () {
    const rj = data.report_json || {};
    const grade = rj.final_grade != null ? rj.final_grade : "?";
    const student = rj.student_id || studentIdInput.value.trim() || "student";
    const lecture = rj.lecture_id || lectureIdInput.value || "lecture";
    const startedAt = rj.started_at || "";
    const generatedAt = rj.timestamp || new Date().toISOString();
    let durationStr = "";
    if (startedAt) {
      const mins = Math.round((new Date(generatedAt) - new Date(startedAt)) / 60000);
      durationStr = "Duration: " + mins + " minutes";
    }
    const lines = [
      "=== Lecture Bot Session Report ===",
      "Session ID: " + (rj.session_id || sessionId || "unknown"),
      "Student ID: " + student,
      "Lecture: " + lecture,
      "Grade: " + grade + " / 100",
      "Session started: " + startedAt,
      "Report generated: " + generatedAt,
    ];
    if (durationStr) lines.push(durationStr);
    lines.push("--- Report ---", "", reportText);
    const blob = new Blob([lines.join("\n")], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = student + "_" + lecture + "_report.txt";
    a.click();
    URL.revokeObjectURL(url);
  });
  row.appendChild(dl);

  const notice = document.createElement("p");
  notice.className = "report-upload-notice";
  notice.textContent = "Please upload this file to the appropriate assignment in Moodle. If you do not upload the file, you will not be able to get credit for the assignment.";
  row.appendChild(notice);

  transcript.appendChild(row);
  renderMath(row);
  transcript.scrollTop = transcript.scrollHeight;
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
    setSessionActive(true);
    if (data.message) appendMessage("assistant", data.message);
  } catch (err) {
    showError("Network error: " + err.message);
  }
}

startSessionBtn.addEventListener("click", startSession);
sendBtn.addEventListener("click", sendMessage);
gradeBtn.addEventListener("click", getGrade);
reportBtn.addEventListener("click", generateReport);
restartBtn.addEventListener("click", restartSession);
