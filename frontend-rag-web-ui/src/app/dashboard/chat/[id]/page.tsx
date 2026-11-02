"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Send, User, Bot, Loader2 } from "lucide-react";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { ApiError } from "@/lib/api";
import { Answer } from "@/components/chat/answer";
import { useToast } from "@/components/ui/use-toast";

interface LocalMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
}

interface ChatSource {
  filename: string;
  excerpt: string;
}

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export default function ChatPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();

  const [messages, setMessages] = useState<LocalMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");
  const [sources, setSources] = useState<ChatSource[]>([]);
  const [convId, setConvId] = useState<number | null>(null);
  const [elapsed, setElapsed] = useState<number | null>(null);

  // 同步 URL 参数中的 conversation ID
  useEffect(() => {
    const id = params.id !== "0" ? Number(params.id) : null;
    setConvId(id);
    if (id) setMessages([]); // 切换对话时清空旧消息
  }, [params.id]);

  // 加载历史消息
  useEffect(() => {
    if (!convId) return;
    const token = localStorage.getItem("token") || "";
    fetch(`${BACKEND}/api/v1/chat/conversations/${convId}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load conversation");
        return res.json();
      })
      .then((data) => {
        const msgs: LocalMessage[] = (data.messages || []).map((m: any) => ({
          id: String(m.id),
          role: m.role === "assistant" ? "assistant" : "user",
          content: m.content,
        }));
        setMessages(msgs);
      })
      .catch((err) => {
        console.error("Failed to load conversation:", err);
      });
  }, [convId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = useCallback(async () => {
    const q = input.trim();
    if (!q || loading) return;

    const userMsg: LocalMessage = { id: Date.now().toString(), role: "user", content: q };
    setMessages((p) => [...p, userMsg]);
    setInput("");
    setLoading(true);
    setStatusMsg("");
    setSources([]);
    setElapsed(null);

    const aid = (Date.now() + 1).toString();
    setMessages((p) => [...p, { id: aid, role: "assistant", content: "" }]);

    const token = typeof window !== "undefined" ? localStorage.getItem("token") || "" : "";

    try {
      const resp = await fetch(`${BACKEND}/api/v1/chat/query/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ question: q, conversation_id: convId }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new ApiError(resp.status, err.detail || "请求失败");
      }

      const reader = resp.body?.getReader();
      if (!reader) throw new ApiError(500, "无响应流");

      const decoder = new TextDecoder();
      let buf = "", full = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop() || "";
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const d = line.slice(6).trim();
          if (!d || d === "[DONE]") continue;
          try {
            const ev = JSON.parse(d);
            if (ev.type === "status") setStatusMsg(ev.message || "");
            else if (ev.type === "error") throw new ApiError(500, ev.message || "AI 服务异常");
            else if (ev.type === "token") {
              full += ev.content || "";
              setMessages((p) => p.map((m) => (m.id === aid ? { ...m, content: full } : m)));
            } else if (ev.type === "done") {
              if (ev.sources) setSources(ev.sources);
              if (ev.elapsed_seconds != null) setElapsed(ev.elapsed_seconds);
              if (ev.conversation_id != null) {
                setConvId(ev.conversation_id);
                if (params.id === "0") router.replace(`/dashboard/chat/${ev.conversation_id}`);
              }
            }
          } catch { /* skip */ }
        }
      }
    } catch (err: any) {
      setMessages((p) =>
        p.map((m) => (m.id === aid ? { ...m, content: "⚠️ 请求失败：" + (err.message || "未知错误") } : m))
      );
    } finally {
      setLoading(false);
      setStatusMsg("");
    }
  }, [input, loading, convId, params.id, router]);

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  };

  return (
    <DashboardLayout>
      <div className="flex flex-col h-[calc(100vh-5rem)] relative">
        <div className="flex items-center justify-between px-4 py-3 border-b">
          <h2 className="text-lg font-semibold">{convId ? `对话 #${convId}` : "新建对话"}</h2>
          {statusMsg && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground animate-pulse">
              <Loader2 className="h-4 w-4 animate-spin" />{statusMsg}
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4 pb-[80px]">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
              <Bot className="h-12 w-12 mb-4 opacity-30" />
              <p className="text-lg">AI 文档问答助手</p>
              <p className="text-sm mt-1">上传文档后开始提问</p>
            </div>
          )}

          {messages.map((m) =>
            m.role === "assistant" ? (
              <div key={m.id} className="flex gap-3">
                <img src="/logo.png" className="h-8 w-8 rounded-full shrink-0" alt="AI" />
                <div className="max-w-[80%] rounded-lg px-4 py-2">
                  {m.content ? (
                    <Answer markdown={m.content} citations={undefined} />
                  ) : (
                    <div className="flex gap-1 py-2">
                      <div className="w-2 h-2 rounded-full bg-primary/60 animate-bounce" />
                      <div className="w-2 h-2 rounded-full bg-primary/60 animate-bounce [animation-delay:0.2s]" />
                      <div className="w-2 h-2 rounded-full bg-primary/60 animate-bounce [animation-delay:0.4s]" />
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div key={m.id} className="flex justify-end gap-3">
                <div className="max-w-[80%] rounded-lg px-4 py-2 bg-primary text-primary-foreground">
                  {m.content}
                </div>
                <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shrink-0">
                  <User className="h-5 w-5 text-primary-foreground" />
                </div>
              </div>
            )
          )}

          {sources.length > 0 && !loading && (
            <div className="ml-11 mt-2">
              <details className="text-sm text-muted-foreground">
                <summary className="cursor-pointer hover:text-foreground">参考来源 ({sources.length})</summary>
                <div className="mt-2 space-y-2">
                  {sources.map((s, i) => (
                    <div key={i} className="bg-muted rounded p-2 text-xs">
                      <span className="font-medium">{s.filename}</span>
                      <p className="mt-1 line-clamp-3">{s.excerpt}</p>
                    </div>
                  ))}
                </div>
              </details>
            </div>
          )}

          {elapsed != null && !loading && (
            <div className="ml-11 text-xs text-muted-foreground/70">
              ⏱ {elapsed.toFixed(1)} 秒
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <form
          onSubmit={(e) => { e.preventDefault(); send(); }}
          className="border-t p-4 flex items-center gap-4 bg-background absolute bottom-0 left-0 right-0"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="输入问题，Enter 发送..."
            disabled={loading}
            className="flex-1 h-10 rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-2 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="inline-flex items-center justify-center rounded-md bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2 disabled:pointer-events-none disabled:opacity-50"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </button>
        </form>
      </div>
    </DashboardLayout>
  );
}