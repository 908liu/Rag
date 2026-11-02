interface FetchOptions extends Omit<RequestInit, 'body' | 'headers'> {
  data?: any;
  headers?: Record<string, string>;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

// ================================================================
//  Route mapper: template API paths → actual backend endpoints
// ================================================================
function backendUrl(path: string, method: string = "GET"): string {
  if (path === "/api/auth/token") return `${BACKEND_URL}/api/v1/auth/login`;
  if (path === "/api/auth/register") return `${BACKEND_URL}/api/v1/auth/register`;

  // Knowledge base
  if (path === "/api/knowledge-base") return `${BACKEND_URL}/api/v1/documents`;
  if (/^\/api\/knowledge-base\/\d+$/.test(path)) {
    if (method === "DELETE") return `${BACKEND_URL}/api/v1/documents/${path.split("/").pop()}`;
    return `${BACKEND_URL}/api/v1/documents`; // GET → list all docs (no single-doc endpoint)
  }
  if (/^\/api\/knowledge-base\/\d+\/documents\/upload$/.test(path)) return `${BACKEND_URL}/api/v1/documents/upload`;

  // Chat list → GET /api/v1/chat/conversations
  if (path === "/api/chat") return `${BACKEND_URL}/api/v1/chat/conversations`;
  // Chat messages stream
  if (/^\/api\/chat\/\d+\/messages$/.test(path)) return `${BACKEND_URL}/api/v1/chat/query/stream`;
  // Chat single (GET single / DELETE)
  if (/^\/api\/chat\/\d+$/.test(path)) return `${BACKEND_URL}${path.replace("/api/chat/", "/api/v1/chat/conversations/")}`;

  // API Keys
  if (path === "/api/api-keys") return `${BACKEND_URL}/api/v1/api-keys`;
  if (/^\/api\/api-keys\/\d+$/.test(path)) return `${BACKEND_URL}${path.replace("/api/", "/api/v1/")}`;

  // Evaluation datasets
  if (path === "/api/evaluation/overview") return `${BACKEND_URL}/api/v1/evaluation/overview`;
  if (path === "/api/evaluation/datasets") return `${BACKEND_URL}/api/v1/evaluation/datasets`;
  if (/^\/api\/evaluation\/datasets\/\d+$/.test(path)) return `${BACKEND_URL}${path.replace("/api/", "/api/v1/")}`;
  // Evaluation runs
  if (path === "/api/evaluation/runs") return `${BACKEND_URL}/api/v1/evaluation/runs`;
  if (/^\/api\/evaluation\/runs\/\d+$/.test(path)) return `${BACKEND_URL}${path.replace("/api/", "/api/v1/")}`;
  if (/^\/api\/evaluation\/runs\/\d+\/results$/.test(path)) return `${BACKEND_URL}${path.replace("/api/", "/api/v1/")}`;

  return `${BACKEND_URL}${path}`;
}

export async function fetchApi(fullUrl: string, options: FetchOptions = {}) {
  const { data, headers: customHeaders = {}, ...restOptions } = options;

  let token = '';
  if (typeof window !== 'undefined') {
    token = localStorage.getItem('token') || '';
  }

  // Auth: login sends form-urlencoded — convert to JSON for our backend
  let bodyData = data;
  if (fullUrl === "/api/auth/token" && data instanceof URLSearchParams) {
    const obj: Record<string, string> = {};
    data.forEach((v, k) => { obj[k] = v; });
    bodyData = obj;
    customHeaders["Content-Type"] = "application/json";
  }

  const headers: Record<string, string> = {
    ...(token && { Authorization: `Bearer ${token}` }),
    ...customHeaders,
  };
  if (!headers['Content-Type'] && bodyData && !(bodyData instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const config: RequestInit = { ...restOptions, headers };
  if (bodyData) {
    if (bodyData instanceof FormData) config.body = bodyData;
    else if (headers['Content-Type'] === 'application/json') config.body = JSON.stringify(bodyData);
    else config.body = bodyData;
  }

  // ── Streaming chat: special handling ──
  if (fullUrl.startsWith("/api/chat/") && fullUrl.endsWith("/messages")) {
    return streamChatResponse(fullUrl, bodyData, token);
  }

  try {
    const response = await fetch(backendUrl(fullUrl, config.method), config);

    if (response.status === 401) {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('token');
        window.location.href = '/login';
      }
      throw new ApiError(401, 'Unauthorized');
    }
    if (response.status === 204) return null;

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(response.status, err.detail || err.message || 'Error');
    }

    const result = await response.json();

    // ── Response adapters: backend JSON → template-expected format ──

    // Auth
    if (fullUrl === "/api/auth/token" || fullUrl === "/api/auth/register") {
      return { access_token: result.token, token_type: "bearer", user: result.user };
    }

    // Docs list → array of KB objects (list view)
    // Docs single → single KB object (detail view)
    if (fullUrl === "/api/knowledge-base" || /^\/api\/knowledge-base\/\d+$/.test(fullUrl)) {
      const docs = Array.isArray(result) ? result : [];
      const kbObject = {
        id: 1,
        name: "我的文档库",
        description: "",
        documents: docs.map((d: any) => ({
          id: d.id,
          file_name: d.name || d.filename,
          file_path: d.name || d.filename,
          file_size: 0,
          content_type: d.name || d.filename,
          status: d.status,
          created_at: new Date().toISOString(),
          processing_tasks: [{ id: d.id, status: d.status, error_message: null }],
        })),
        created_at: new Date().toISOString(),
      };
      return /^\/api\/knowledge-base\/\d+$/.test(fullUrl) ? kbObject : [kbObject];
    }

    // Upload
    if (/\/documents\/upload$/.test(fullUrl)) {
      return (result.documents || []).map((d: any) => ({
        file_name: d.name || d.filename,
        document_id: d.id,
        status: "exists",
        skip_processing: true,
        message: d.status,
      }));
    }

    // Chat conversations list → adapt to frontend format
    if (fullUrl === "/api/chat") {
      const conversations = Array.isArray(result) ? result : [];
      return conversations.map((c: any) => ({
        id: c.id,
        title: c.title,
        created_at: c.created_at,
        messages: (c.messages || []).map((m: any) => ({
          id: m.id,
          content: m.content,
          is_bot: m.role === "assistant",
          created_at: m.created_at,
        })),
        knowledge_base_ids: [],
      }));
    }

    return result;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(500, 'Network error');
  }
}

// ── SSE streaming → ReadableStream (compatible with ai/react useChat) ──
async function streamChatResponse(fullUrl: string, bodyData: any, token: string) {
  const messages = bodyData?.messages || [];
  const question = messages.length > 0 ? messages[messages.length - 1].content : '';
  const convMatch = fullUrl.match(/\/api\/chat\/(\d+)\/messages/);
  const conversationId = convMatch ? (convMatch[1] !== '0' ? Number(convMatch[1]) : null) : null;

  const response = await fetch(`${BACKEND_URL}/api/v1/chat/query/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({ question, conversation_id: conversationId }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new ApiError(response.status, err.detail || 'Stream failed');
  }

  const reader = response.body?.getReader();
  if (!reader) throw new ApiError(500, 'No stream');

  const decoder = new TextDecoder();
  let buffer = '';

  return new ReadableStream({
    async start(controller) {
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';
          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            const raw = line.slice(6).trim();
            if (!raw || raw === '[DONE]') continue;
            try {
              const event = JSON.parse(raw);
              if (event.type === 'token' && event.content) {
                controller.enqueue(new TextEncoder().encode(event.content));
              }
            } catch { /* skip */ }
          }
        }
      } finally {
        controller.close();
      }
    },
  });
}

// ── Helpers ──
export const api = {
  get:    (url: string, opts?: Omit<FetchOptions, 'method'>) => fetchApi(url, { ...opts, method: 'GET' }),
  post:   (url: string, data?: any, opts?: Omit<FetchOptions, 'method'>) => fetchApi(url, { ...opts, method: 'POST', data }),
  put:    (url: string, data?: any, opts?: Omit<FetchOptions, 'method'>) => fetchApi(url, { ...opts, method: 'PUT', data }),
  delete: (url: string, opts?: Omit<FetchOptions, 'method'>) => fetchApi(url, { ...opts, method: 'DELETE' }),
  patch:  (url: string, data?: any, opts?: Omit<FetchOptions, 'method'>) => fetchApi(url, { ...opts, method: 'PATCH', data }),
};