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

function backendUrl(path: string): string {
  if (path === "/api/auth/token") return `${BACKEND_URL}/api/v1/auth/login`;
  if (path === "/api/auth/register") return `${BACKEND_URL}/api/v1/auth/register`;
  if (path === "/api/knowledge-base") return `${BACKEND_URL}/api/v1/documents`;
  if (path.startsWith("/api/knowledge-base/")) {
    const match = path.match(/^\/api\/knowledge-base\/\d+\/documents\/upload$/);
    if (match) return `${BACKEND_URL}/api/v1/documents/upload`;
    const deleteMatch = path.match(/^\/api\/knowledge-base\/(\d+)$/);
    if (deleteMatch) return `${BACKEND_URL}/api/v1/documents/${deleteMatch[1]}`;
  }
  return `${BACKEND_URL}${path}`;
}

export async function fetchApi(fullUrl: string, options: FetchOptions = {}) {
  const { data, headers: customHeaders = {}, ...restOptions } = options;

  // Get token from localStorage
  let token = '';
  if (typeof window !== 'undefined') {
    token = localStorage.getItem('token') || '';
  }

  const headers: Record<string, string> = {
    ...(token && { Authorization: `Bearer ${token}` }),
    ...customHeaders,
  };

  // If no content type is specified and we have data, default to JSON
  if (!headers['Content-Type'] && data && !(data instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const config: RequestInit = {
    ...restOptions,
    headers,
  };

  // Handle body based on Content-Type
  if (data) {
    if (data instanceof FormData) {
      config.body = data;
    } else if (headers['Content-Type'] === 'application/json') {
      config.body = JSON.stringify(data);
    } else if (headers['Content-Type'] === 'application/x-www-form-urlencoded') {
      config.body = typeof data === 'string' ? data : new URLSearchParams(data).toString();
    } else {
      config.body = data;
    }
  }

  try {
    const response = await fetch(backendUrl(fullUrl), config);

    if (response.status === 401) {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('token');
        window.location.href = '/login';
      }
      throw new ApiError(401, 'Unauthorized - Please log in again');
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        response.status,
        errorData.message || errorData.detail || 'An error occurred'
      );
    }

    const result = await response.json();
    if (fullUrl === "/api/auth/token") {
      return { access_token: result.token, token_type: "bearer", user: result.user };
    }
    if (fullUrl === "/api/knowledge-base") {
      return [{
        id: 1,
        name: "我的文档库",
        description: "当前账户的文档集合",
        documents: result.map((document: any) => ({
          id: document.id,
          file_name: document.name || document.filename,
          content_type: document.name || document.filename,
          status: document.status,
        })),
        created_at: new Date().toISOString(),
      }];
    }
    if (/^\/api\/knowledge-base\/\d+\/documents\/upload$/.test(fullUrl)) {
      return (result.documents || []).map((document: any) => ({
        file_name: document.name || document.filename,
        document_id: document.id,
        status: "exists",
        skip_processing: true,
        message: document.status,
      }));
    }
    return result;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(500, 'Network error or server is unreachable');
  }
}

// Helper methods for common HTTP methods
export const api = {
  get: (url: string, options?: Omit<FetchOptions, 'method'>) =>
    fetchApi(url, { ...options, method: 'GET' }),

  post: (url: string, data?: any, options?: Omit<FetchOptions, 'method'>) =>
    fetchApi(url, { ...options, method: 'POST', data }),

  put: (url: string, data?: any, options?: Omit<FetchOptions, 'method'>) =>
    fetchApi(url, { ...options, method: 'PUT', data }),

  delete: (url: string, options?: Omit<FetchOptions, 'method'>) =>
    fetchApi(url, { ...options, method: 'DELETE' }),

  patch: (url: string, data?: any, options?: Omit<FetchOptions, 'method'>) =>
    fetchApi(url, { ...options, method: 'PATCH', data }),
};
