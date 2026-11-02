"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { Sparkles } from "lucide-react";

export default function NewChatPage() {
  const router = useRouter();
  const [title, setTitle] = useState("");

  const startQuickChat = () => router.push("/dashboard/chat/0");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    router.push(`/dashboard/chat/0?title=${encodeURIComponent(title.trim() || "新对话")}`);
  };

  return (
    <DashboardLayout>
      <div className="max-w-2xl mx-auto space-y-8">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">开始新对话</h2>
          <p className="text-muted-foreground mt-1">AI 将基于你上传的文档回答问题</p>
        </div>

        <div className="grid gap-6">
          <button
            onClick={startQuickChat}
            className="flex flex-col items-center justify-center rounded-2xl border bg-card p-8 shadow-sm hover:shadow-md hover:border-primary/50 transition-all cursor-pointer"
          >
            <div className="rounded-full bg-purple-100 dark:bg-purple-900/30 p-4 mb-4">
              <Sparkles className="h-8 w-8 text-purple-600 dark:text-purple-400" />
            </div>
            <h3 className="text-lg font-medium mb-2">快速开始</h3>
            <p className="text-sm text-muted-foreground text-center">直接开始对话，无需设置</p>
          </button>

          <form onSubmit={handleSubmit} className="rounded-2xl border bg-card p-8 shadow-sm">
            <h3 className="text-lg font-medium mb-4">命名对话</h3>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="flex h-10 w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-2"
              placeholder="输入对话标题（可选）"
            />
            <div className="flex justify-end gap-4 mt-4">
              <button type="button" onClick={() => router.back()}
                className="inline-flex items-center justify-center rounded-md border px-4 py-2 text-sm font-medium hover:bg-accent">
                取消
              </button>
              <button type="submit"
                className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90">
                开始对话
              </button>
            </div>
          </form>
        </div>
      </div>
    </DashboardLayout>
  );
}