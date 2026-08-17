const state = {
  apiBase: localStorage.getItem("ragApiBase") || "http://127.0.0.1:8056",
  documentId: localStorage.getItem("ragDocumentId") || "",
  socket: null,
  statusTimer: null,
  currentUploadId: null,
};

const $ = (id) => document.getElementById(id);

const els = {
  apiBase: $("apiBase"),
  documentId: $("documentId"),
  saveConfigBtn: $("saveConfigBtn"),
  connectBtn: $("connectBtn"),
  disconnectBtn: $("disconnectBtn"),
  uploadForm: $("uploadForm"),
  pdfFile: $("pdfFile"),
  clearUploadBtn: $("clearUploadBtn"),
  uploadState: $("uploadState"),
  uploadLog: $("uploadLog"),
  uploadedName: $("uploadedName"),
  pageCount: $("pageCount"),
  chunkCount: $("chunkCount"),
  progressBar: $("progressBar"),
  chatState: $("chatState"),
  chatFeed: $("chatFeed"),
  chatForm: $("chatForm"),
  questionInput: $("questionInput"),
  sourcesList: $("sourcesList"),
  connectionChip: $("connectionChip"),
};

function setStatusChip(el, text, tone = "neutral") {
  el.textContent = text;
  el.dataset.tone = tone;
}

function logUpload(message) {
  els.uploadLog.textContent = `${new Date().toLocaleTimeString()}  ${message}\n${els.uploadLog.textContent}`;
}

function scrollToBottom(node) {
  node.scrollTop = node.scrollHeight;
}

function appendMessage(role, title, body) {
  const item = document.createElement("article");
  item.className = `message ${role}`;
  item.innerHTML = `
    <div class="message-meta">
      <span>${title}</span>
      <span>${new Date().toLocaleTimeString()}</span>
    </div>
    <div class="message-body"></div>
  `;
  item.querySelector(".message-body").textContent = body;
  els.chatFeed.appendChild(item);
  scrollToBottom(els.chatFeed);
}

function renderSources(sources = []) {
  els.sourcesList.innerHTML = "";
  if (!sources.length) {
    els.sourcesList.innerHTML = `<div class="source-item"><p>No sources returned.</p></div>`;
    return;
  }

  for (const source of sources) {
    const card = document.createElement("div");
    card.className = "source-item";
    card.innerHTML = `
      <strong>${source.source_id} | ${source.filename} | page ${source.page_number ?? "?"} | chunk ${source.chunk_index}</strong>
      <p>${source.text}</p>
    `;
    els.sourcesList.appendChild(card);
  }
}

function apiUrl(path) {
  return new URL(path, state.apiBase).toString();
}

function wsUrl(path) {
  const url = new URL(state.apiBase);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = path;
  url.search = "";
  url.hash = "";
  return url.toString();
}

function saveConfig() {
  state.apiBase = els.apiBase.value.trim() || "http://127.0.0.1:8056";
  state.documentId = els.documentId.value.trim();
  localStorage.setItem("ragApiBase", state.apiBase);
  localStorage.setItem("ragDocumentId", state.documentId);
  logUpload(`Saved API base ${state.apiBase}`);
}

async function fetchJson(path) {
  const response = await fetch(apiUrl(path));
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

async function pollDocument(documentId) {
  clearInterval(state.statusTimer);
  let attempts = 0;
  state.statusTimer = setInterval(async () => {
    attempts += 1;
    try {
      const doc = await fetchJson(`/api/documents/${documentId}`);
      els.uploadedName.textContent = doc.filename || "Unknown";
      els.pageCount.textContent = doc.page_count ?? "-";
      els.chunkCount.textContent = doc.chunk_count ?? "-";

      const progress = doc.status === "processed" ? 100 : doc.status === "failed" ? 100 : Math.min(95, 15 + attempts * 12);
      els.progressBar.style.width = `${progress}%`;

      if (doc.status === "processed") {
        setStatusChip(els.uploadState, "Processed", "success");
        logUpload(`Finished processing ${doc.filename}. Chunks stored in the database.`);
        clearInterval(state.statusTimer);
      } else if (doc.status === "failed") {
        setStatusChip(els.uploadState, "Failed", "danger");
        logUpload(`Processing failed: ${doc.error_message || "Unknown error"}`);
        clearInterval(state.statusTimer);
      } else {
        setStatusChip(els.uploadState, "Processing", "warning");
      }
    } catch (error) {
      logUpload(`Status poll error: ${error.message}`);
    }
  }, 2500);
}

async function handleUpload(event) {
  event.preventDefault();
  const file = els.pdfFile.files[0];
  if (!file) {
    logUpload("Choose a PDF first.");
    return;
  }

  saveConfig();
  const formData = new FormData();
  formData.append("file", file);

  setStatusChip(els.uploadState, "Uploading", "warning");
  els.progressBar.style.width = "10%";
  logUpload(`Uploading ${file.name}...`);

  try {
    const response = await fetch(apiUrl("/api/documents/upload"), {
      method: "POST",
      body: formData,
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || `Upload failed (${response.status})`);
    }

    state.currentUploadId = data.id;
    els.documentId.value = data.id;
    state.documentId = data.id;
    localStorage.setItem("ragDocumentId", data.id);

    els.uploadedName.textContent = data.filename;
    els.pageCount.textContent = data.page_count ?? "-";
    els.chunkCount.textContent = data.chunk_count ?? "-";
    setStatusChip(els.uploadState, data.status, "warning");
    logUpload(`Upload accepted. Document ID: ${data.id}`);
    await pollDocument(data.id);
  } catch (error) {
    setStatusChip(els.uploadState, "Error", "danger");
    els.progressBar.style.width = "0%";
    logUpload(error.message);
  }
}

function connectSocket() {
  saveConfig();
  if (state.socket && state.socket.readyState === WebSocket.OPEN) {
    logUpload("Chat already connected.");
    return;
  }

  const socket = new WebSocket(wsUrl("/api/ws/chat"));
  state.socket = socket;
  setStatusChip(els.chatState, "Connecting", "warning");
  setStatusChip(els.connectionChip, "Connecting", "warning");

  socket.addEventListener("open", () => {
    setStatusChip(els.chatState, "Connected", "success");
    setStatusChip(els.connectionChip, "Connected", "success");
    appendMessage("assistant", "System", "Connected to the 3GPP websocket assistant.");
  });

  socket.addEventListener("message", (event) => {
    const payload = JSON.parse(event.data);
    if (payload.type === "ready") {
      appendMessage("assistant", "Ready", payload.message);
      return;
    }

    if (payload.type === "status") {
      appendMessage("assistant", "Status", payload.message);
      return;
    }

    if (payload.type === "answer") {
      appendMessage("assistant", "Answer", payload.answer);
      renderSources(payload.sources || []);
      return;
    }

    if (payload.type === "error") {
      appendMessage("assistant", "Error", payload.message);
      return;
    }
  });

  socket.addEventListener("close", () => {
    setStatusChip(els.chatState, "Disconnected", "neutral");
    setStatusChip(els.connectionChip, "Disconnected", "neutral");
  });

  socket.addEventListener("error", () => {
    appendMessage("assistant", "Error", "Websocket connection failed.");
    setStatusChip(els.chatState, "Error", "danger");
    setStatusChip(els.connectionChip, "Error", "danger");
  });
}

function disconnectSocket() {
  if (state.socket) {
    state.socket.close();
    state.socket = null;
  }
  setStatusChip(els.chatState, "Disconnected", "neutral");
  setStatusChip(els.connectionChip, "Disconnected", "neutral");
}

function handleChat(event) {
  event.preventDefault();
  const question = els.questionInput.value.trim();
  if (!question) {
    return;
  }

  if (!state.socket || state.socket.readyState !== WebSocket.OPEN) {
    connectSocket();
    const waitForOpen = setInterval(() => {
      if (state.socket && state.socket.readyState === WebSocket.OPEN) {
        clearInterval(waitForOpen);
        sendQuestion(question);
      }
    }, 120);
    return;
  }

  sendQuestion(question);
}

function sendQuestion(question) {
  appendMessage("user", "You", question);
  els.questionInput.value = "";

  const payload = {
    question,
    top_k: 5,
  };
  if (state.documentId) {
    payload.document_id = state.documentId;
  }

  state.socket.send(JSON.stringify(payload));
}

function init() {
  els.apiBase.value = state.apiBase;
  els.documentId.value = state.documentId;
  setStatusChip(els.uploadState, "Idle", "neutral");
  setStatusChip(els.chatState, "Disconnected", "neutral");
  setStatusChip(els.connectionChip, "Disconnected", "neutral");
  renderSources([]);

  els.saveConfigBtn.addEventListener("click", saveConfig);
  els.connectBtn.addEventListener("click", connectSocket);
  els.disconnectBtn.addEventListener("click", disconnectSocket);
  els.uploadForm.addEventListener("submit", handleUpload);
  els.chatForm.addEventListener("submit", handleChat);
  els.clearUploadBtn.addEventListener("click", () => {
    els.pdfFile.value = "";
    els.uploadLog.textContent = "Upload a PDF to begin.";
    els.uploadedName.textContent = "None";
    els.pageCount.textContent = "-";
    els.chunkCount.textContent = "-";
    els.progressBar.style.width = "0%";
    setStatusChip(els.uploadState, "Idle", "neutral");
  });
}

init();
