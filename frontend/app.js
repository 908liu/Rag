const API_BASE = 'http://localhost:8000';
const LOGIN_PAGE_URL = './login-template/animatedlogin-main/index.html?v=workbench';

const state = {
  token: localStorage.getItem('token') || '',
  user: JSON.parse(localStorage.getItem('user') || 'null'),
  authenticated: false,
  docs: [],
  messages: [],
  conversationId: null,
};

const usernameInput = document.getElementById('username');
const passwordInput = document.getElementById('password');
const statusText = document.getElementById('statusText');
const appStatusText = document.getElementById('appStatusText');
const loginScreen = document.getElementById('loginScreen');
const appShell = document.getElementById('appShell');
const docList = document.getElementById('docList');
const fileInput = document.getElementById('fileInput');
const messagesBox = document.getElementById('messages');
const questionInput = document.getElementById('questionInput');
const loginBtn = document.getElementById('loginBtn');
const registerBtn = document.getElementById('registerBtn');
const logoutBtn = document.getElementById('logoutBtn');
const sendBtn = document.getElementById('sendBtn');
const authPanel = document.getElementById('authPanel');
const userPanel = document.getElementById('userPanel');
const userAvatar = document.getElementById('userAvatar');
const userName = document.getElementById('userName');
const welcomeEyebrow = document.getElementById('welcomeEyebrow');
const uploadBox = document.getElementById('uploadBox');
const uploadLabelText = document.getElementById('uploadLabelText');

function setStatus(text, isError = false) {
  const primaryColor = isError ? '#d34a4a' : '#677489';
  if (statusText) {
    statusText.textContent = text;
    statusText.style.color = isError ? '#ffd9d9' : '#dfe7ff';
  }
  if (appStatusText) {
    appStatusText.textContent = text;
    appStatusText.style.color = primaryColor;
  }
}

function saveSession() {
  localStorage.setItem('token', state.token);
  localStorage.setItem('user', JSON.stringify(state.user));
}

function renderAuthState() {
  const isAuthenticated = Boolean(state.authenticated && state.token && state.token !== 'demo-token' && state.user);
  if (loginScreen) {
    loginScreen.hidden = isAuthenticated;
  }
  if (appShell) {
    appShell.hidden = !isAuthenticated;
  }
  if (authPanel) {
    authPanel.hidden = isAuthenticated;
  }
  userPanel.hidden = !isAuthenticated;
  logoutBtn.hidden = !isAuthenticated;
  fileInput.disabled = !isAuthenticated;
  questionInput.disabled = !isAuthenticated;
  sendBtn.disabled = !isAuthenticated;
  uploadBox.classList.toggle('is-disabled', !isAuthenticated);
  uploadBox.setAttribute('aria-disabled', String(!isAuthenticated));
  uploadBox.title = isAuthenticated ? '上传 PDF、TXT 或 MD 文档' : '请先登录后上传文档';
  uploadLabelText.textContent = isAuthenticated ? '点击上传文档' : '登录后上传文档';
  questionInput.placeholder = isAuthenticated ? '请输入你的问题，例如：项目的部署流程是什么？' : '请先登录后提问';

  if (isAuthenticated) {
    const username = state.user.username || '用户';
    userName.textContent = username;
    userAvatar.textContent = Array.from(username)[0] || 'U';
    welcomeEyebrow.textContent = `欢迎回来，${username}`;
  } else {
    welcomeEyebrow.textContent = '智能文档问答';
  }
}

function renderDocs() {
  if (!state.docs.length) {
    docList.innerHTML = '<li class="doc-item"><span class="doc-name">还没有上传文档</span></li>';
    return;
  }

  docList.innerHTML = state.docs
    .map(
      (doc) => `
        <li class="doc-item">
          <div class="doc-info">
            <span class="doc-name">${escapeHtml(doc.name)}</span>
            <span class="doc-status">${escapeHtml(doc.status)}</span>
          </div>
          <button class="doc-delete" type="button" data-document-id="${doc.id}" title="删除文档" aria-label="删除 ${escapeHtml(doc.name)}">删除</button>
        </li>
      `
    )
    .join('');
}

function renderMessages() {
  if (!state.messages.length) {
    const greeting = state.user?.username
      ? `你好，${escapeHtml(state.user.username)}！欢迎回来。上传文档后，就可以开始向知识库提问。`
      : '你好！请先注册或登录，上传文档后即可开始提问。';
    messagesBox.innerHTML = `
      <div class="message assistant">
        <span class="meta">AI 助手</span>
        ${greeting}
      </div>
    `;
    return;
  }

  messagesBox.innerHTML = state.messages
    .map((msg) => {
      const sources = (msg.sources || []).map((source) => `
        <li>
          <strong>${escapeHtml(source.filename)}</strong>
          <p>${escapeHtml(source.excerpt)}</p>
        </li>
      `).join('');
      const sourceSection = sources
        ? `<details class="message-sources"><summary>参考来源（${msg.sources.length}）</summary><ul>${sources}</ul></details>`
        : '';
      return `
        <div class="message ${msg.role}">
          <span class="meta">${msg.role === 'user' ? '你' : 'AI 助手'}</span>
          ${escapeHtml(msg.content)}
          ${sourceSection}
        </div>
      `;
    })
    .join('');

  messagesBox.scrollTop = messagesBox.scrollHeight;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  })[character]);
}

function addMessage(role, content, sources = []) {
  state.messages.push({ role, content, sources });
  renderMessages();
}

function responseErrorMessage(data, fallback) {
  if (Array.isArray(data.detail)) {
    return data.detail.map((item) => {
      const field = item.loc?.[item.loc.length - 1];
      const label = field === 'username' ? '用户名' : field === 'password' ? '密码' : '输入内容';
      if (item.type === 'string_too_short') {
        return `${label}至少需要 ${item.ctx?.min_length ?? ''} 个字符`;
      }
      if (item.type === 'string_too_long') {
        return `${label}最多只能有 ${item.ctx?.max_length ?? ''} 个字符`;
      }
      return `${label}校验失败`;
    }).join('；');
  }

  return typeof data.detail === 'string' ? data.detail : fallback;
}

async function authRequest(path, payload) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
  } catch {
    throw new Error('无法连接后端，请确认服务运行在 http://localhost:8000');
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(responseErrorMessage(data, '请求失败'));
  }

  return data;
}

async function loadDocuments() {
  const response = await fetch(`${API_BASE}/api/v1/documents`, {
    headers: { Authorization: `Bearer ${state.token}` },
  });
  const data = await response.json().catch(() => ({}));
  if (response.status === 401) {
    clearSession();
    setStatus('登录状态已失效，请重新登录。', true);
    return;
  }
  if (!response.ok) {
    throw new Error(responseErrorMessage(data, '无法加载文档列表'));
  }

  state.authenticated = true;
  renderAuthState();
  state.docs = data.map((item) => ({
    id: item.id,
    name: item.name || item.filename,
    status: item.status === 'processed' ? '已处理' : item.status === 'index_failed' ? '向量索引失败' : item.status,
  }));
  renderDocs();
}

async function login(action) {
  const username = usernameInput.value.trim();
  const password = passwordInput.value.trim();

  if (username.length < 3 || username.length > 64) {
    setStatus('用户名长度需要在 3 到 64 个字符之间。', true);
    return;
  }
  if (password.length < 3 || password.length > 128) {
    setStatus('密码长度需要在 3 到 128 个字符之间。', true);
    return;
  }

  try {
    const result = await authRequest(`/api/v1/auth/${action}`, { username, password });
    state.token = result.token;
    state.user = result.user || { username };
    saveSession();
    passwordInput.value = '';
    renderAuthState();
    renderMessages();
    await loadDocuments();
    setStatus(action === 'login' ? `登录成功：${username}` : `注册成功，已自动登录：${username}`);
  } catch (error) {
    setStatus(`${action === 'login' ? '登录' : '注册'}失败：${error.message}`, true);
  }
}

async function uploadFiles(files) {
  if (!files || files.length === 0) {
    return;
  }

  if (!state.token || state.token === 'demo-token') {
    setStatus('请先注册或登录，再上传文档。', true);
    return;
  }

  try {
    const formData = new FormData();
    Array.from(files).forEach((file) => formData.append('files', file));

    const response = await fetch(`${API_BASE}/api/v1/documents/upload`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${state.token}`,
      },
      body: formData,
    });

    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail || '上传失败');
    }

    const uploaded = (result.documents || []).map((item) => ({
      id: item.id,
      name: item.name || item.filename,
      status: item.status === 'processed' ? '已处理' : item.status === 'index_failed' ? '向量索引失败' : item.status,
    }));
    state.docs = [...uploaded, ...state.docs];
    renderDocs();
    const duplicates = result.duplicates || [];
    setStatus(
      duplicates.length
        ? `${uploaded.length ? '新文档已上传；' : ''}重复文件已跳过：${duplicates.join('、')}`
        : '文档上传成功。'
    );
  } catch (error) {
    setStatus(`上传失败：${error.message}`, true);
  }
}

async function deleteDocument(documentId) {
  const document = state.docs.find((item) => item.id === documentId);
  if (!document || !window.confirm(`确定删除文档“${document.name}”吗？该文档的文件和向量索引也会删除。`)) {
    return;
  }

  try {
    const response = await fetch(`${API_BASE}/api/v1/documents/${documentId}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${state.token}` },
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(responseErrorMessage(data, '删除失败'));
    }

    state.docs = state.docs.filter((item) => item.id !== documentId);
    renderDocs();
    setStatus(`已删除文档：${document.name}`);
  } catch (error) {
    setStatus(`删除失败：${error.message}`, true);
  }
}

async function sendQuestion() {
  const question = questionInput.value.trim();
  if (!question) {
    return;
  }
  if (!state.token || state.token === 'demo-token') {
    setStatus('请先注册或登录，再向知识库提问。', true);
    return;
  }

  addMessage('user', question);
  questionInput.value = '';

  try {
    const response = await fetch(`${API_BASE}/api/v1/chat/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${state.token}`,
      },
      body: JSON.stringify({
        question,
        conversation_id: state.conversationId,
      }),
    });

    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail || '请求失败');
    }

    if (result.conversation_id) {
      state.conversationId = result.conversation_id;
    }

    const answer = result.answer || '暂时没有返回有效答案。';
    addMessage('assistant', answer, result.sources || []);
    setStatus('问答成功。');
  } catch (error) {
    addMessage('assistant', `抱歉，当前无法获取答案：${error.message}`);
    setStatus(`请求失败：${error.message}`, true);
  }
}

function bindEvents() {
  loginBtn.addEventListener('click', () => login('login'));
  registerBtn.addEventListener('click', () => login('register'));
  sendBtn.addEventListener('click', sendQuestion);
  docList.addEventListener('click', (event) => {
    const button = event.target.closest('[data-document-id]');
    if (button) {
      deleteDocument(Number(button.dataset.documentId));
    }
  });
  logoutBtn.addEventListener('click', () => {
    clearSession();
  });

  questionInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendQuestion();
    }
  });

  fileInput.addEventListener('change', (event) => {
    const files = event.target.files;
    uploadFiles(files);
    fileInput.value = '';
  });
}

function clearSession() {
  state.token = '';
  state.user = null;
  state.authenticated = false;
  state.docs = [];
  state.messages = [];
  state.conversationId = null;
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  window.location.replace(LOGIN_PAGE_URL);
}

function init() {
  bindEvents();

  if (state.token === 'demo-token') {
    state.token = '';
    state.user = null;
    state.authenticated = false;
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  }

  if (!state.token || !state.user) {
    window.location.replace(LOGIN_PAGE_URL);
    return;
  }

  renderMessages();
  renderDocs();

  usernameInput.value = state.user.username || '';
  setStatus('正在验证登录状态…');
  loadDocuments().catch((error) => setStatus(`文档加载失败：${error.message}`, true));
}

init();
