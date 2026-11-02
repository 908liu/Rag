"use client";

import { useState, useEffect } from "react";
import { Plus, Copy, Check, Star, Settings, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/components/ui/use-toast";
import { api } from "@/lib/api";

// ---- Types ----

export interface APIKey {
  id: number;
  name: string;
  key: string;
  is_active: boolean;
  is_default: boolean;
  provider_name: string;
  llm_api_key: string;
  llm_base_url: string;
  llm_model: string;
  embedding_api_key: string;
  embedding_base_url: string;
  embedding_model: string;
  last_used_at: string | null;
  created_at: string;
  updated_at: string;
}

// ---- Provider Presets ----

interface ProviderPreset {
  name: string;
  base_url: string;
  models: string[];
}

const PROVIDER_PRESETS: Record<string, ProviderPreset> = {
  openai: {
    name: "OpenAI",
    base_url: "https://api.openai.com/v1",
    models: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
  },
  deepseek: {
    name: "DeepSeek",
    base_url: "https://api.deepseek.com/v1",
    models: ["deepseek-chat", "deepseek-reasoner"],
  },
  qwen: {
    name: "通义千问 (Qwen)",
    base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1",
    models: ["qwen-turbo", "qwen-plus", "qwen-max", "qwen-max-longcontext"],
  },
  zhipu: {
    name: "智谱 (GLM)",
    base_url: "https://open.bigmodel.cn/api/paas/v4",
    models: ["glm-4-flash", "glm-4-plus", "glm-4-air"],
  },
  moonshot: {
    name: "Moonshot (Kimi)",
    base_url: "https://api.moonshot.cn/v1",
    models: ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
  },
  siliconflow: {
    name: "SiliconFlow",
    base_url: "https://api.siliconflow.cn/v1",
    models: [
      "deepseek-ai/DeepSeek-V3",
      "Qwen/Qwen2.5-72B-Instruct",
      "Pro/OpenAI/gpt-4o",
    ],
  },
  custom: {
    name: "自定义",
    base_url: "https://api.openai.com/v1",
    models: [],
  },
};

// ---- Helpers ----

function maskKey(key: string): string {
  if (!key) return "—";
  if (key.length <= 8) return "****";
  return key.slice(0, 4) + "****" + key.slice(-4);
}

// ---- Page ----

export default function APIKeysPage() {
  const [apiKeys, setApiKeys] = useState<APIKey[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingKey, setEditingKey] = useState<APIKey | null>(null);
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const { toast } = useToast();

  // ---- Form state ----
  const [formName, setFormName] = useState("");
  const [formProvider, setFormProvider] = useState("custom");
  const [formApiKey, setFormApiKey] = useState("");
  const [formBaseUrl, setFormBaseUrl] = useState("");
  const [formModel, setFormModel] = useState("");
  const [formIsDefault, setFormIsDefault] = useState(false);
  const [formIsActive, setFormIsActive] = useState(true);
  const [formEmbeddingApiKey, setFormEmbeddingApiKey] = useState("");
  const [formEmbeddingBaseUrl, setFormEmbeddingBaseUrl] = useState("");
  const [formEmbeddingModel, setFormEmbeddingModel] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);

  // ---- Fetch ----

  const fetchAPIKeys = async () => {
    try {
      const data = await api.get("/api/api-keys");
      setApiKeys(data);
    } catch {
      toast({
        title: "Error",
        description: "Failed to fetch API keys",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAPIKeys();
  }, []);

  // ---- Reset form ----

  const resetForm = () => {
    setFormName("");
    setFormProvider("custom");
    setFormApiKey("");
    setFormBaseUrl("");
    setFormModel("");
    setFormIsDefault(false);
    setFormIsActive(true);
    setFormEmbeddingApiKey("");
    setFormEmbeddingBaseUrl("");
    setFormEmbeddingModel("");
    setShowAdvanced(false);
    setEditingKey(null);
  };

  const openCreate = () => {
    resetForm();
    setIsDialogOpen(true);
  };

  const openEdit = (key: APIKey) => {
    setEditingKey(key);
    setFormName(key.name);
    setFormProvider(key.provider_name || "custom");
    setFormApiKey(key.llm_api_key);
    setFormBaseUrl(key.llm_base_url);
    setFormModel(key.llm_model);
    setFormIsDefault(key.is_default);
    setFormIsActive(key.is_active);
    setFormEmbeddingApiKey(key.embedding_api_key);
    setFormEmbeddingBaseUrl(key.embedding_base_url);
    setFormEmbeddingModel(key.embedding_model);
    setIsDialogOpen(true);
  };

  // ---- Provider preset handler ----

  const handleProviderChange = (value: string) => {
    setFormProvider(value);
    const preset = PROVIDER_PRESETS[value];
    if (preset) {
      setFormBaseUrl(preset.base_url);
      if (preset.models.length > 0 && !formModel) {
        setFormModel(preset.models[0]);
      }
    }
  };

  // ---- Create / Update ----

  const saveApiKey = async () => {
    if (!formName.trim()) {
      toast({ title: "Error", description: "请输入名称", variant: "destructive" });
      return;
    }
    if (!formApiKey.trim()) {
      toast({ title: "Error", description: "请输入 LLM API Key", variant: "destructive" });
      return;
    }
    if (!formBaseUrl.trim()) {
      toast({ title: "Error", description: "请输入 Base URL", variant: "destructive" });
      return;
    }
    if (!formModel.trim()) {
      toast({ title: "Error", description: "请输入模型名称", variant: "destructive" });
      return;
    }

    setIsCreating(true);
    const payload = {
      name: formName,
      is_active: formIsActive,
      is_default: formIsDefault,
      provider_name: formProvider,
      llm_api_key: formApiKey,
      llm_base_url: formBaseUrl,
      llm_model: formModel,
      embedding_api_key: formEmbeddingApiKey,
      embedding_base_url: formEmbeddingBaseUrl,
      embedding_model: formEmbeddingModel,
    };

    try {
      if (editingKey) {
        const data = await api.put(`/api/api-keys/${editingKey.id}`, payload);
        setApiKeys(apiKeys.map((k) => (k.id === editingKey.id ? data : k)));
        toast({ title: "Success", description: "API Key 已更新" });
      } else {
        const data = await api.post("/api/api-keys", payload);
        setApiKeys([data, ...apiKeys]);
        toast({ title: "Success", description: "API Key 创建成功" });
      }
      setIsDialogOpen(false);
      resetForm();
    } catch {
      toast({ title: "Error", description: "操作失败", variant: "destructive" });
    } finally {
      setIsCreating(false);
    }
  };

  // ---- Set Default ----

  const setDefault = async (id: number) => {
    try {
      const data = await api.post(`/api/api-keys/${id}/set-default`);
      setApiKeys(
        apiKeys.map((k) =>
          k.id === id
            ? { ...k, is_default: true }
            : { ...k, is_default: false }
        )
      );
      toast({ title: "Success", description: "已设为默认 Provider" });
    } catch {
      toast({ title: "Error", description: "设置失败", variant: "destructive" });
    }
  };

  // ---- Delete ----

  const deleteAPIKey = async (id: number) => {
    try {
      await api.delete(`/api/api-keys/${id}`);
      setApiKeys(apiKeys.filter((key) => key.id !== id));
      toast({ title: "Success", description: "API Key 已删除" });
    } catch {
      toast({ title: "Error", description: "删除失败", variant: "destructive" });
    }
  };

  // ---- Toggle Active ----

  const toggleActive = async (id: number, current: boolean) => {
    try {
      await api.put(`/api/api-keys/${id}`, { is_active: !current });
      setApiKeys(
        apiKeys.map((k) => (k.id === id ? { ...k, is_active: !current } : k))
      );
    } catch {
      toast({ title: "Error", description: "更新失败", variant: "destructive" });
    }
  };

  // ---- Copy ----

  const copyKey = async (id: number, key: string) => {
    try {
      await navigator.clipboard.writeText(key);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 3000);
    } catch {
      toast({ title: "Error", description: "复制失败", variant: "destructive" });
    }
  };

  // ---- Render ----

  const preset = PROVIDER_PRESETS[formProvider];

  return (
    <DashboardLayout>
      <div className="container mx-auto py-10 max-w-6xl">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-2xl font-bold">模型配置</h1>
            <p className="text-sm text-muted-foreground mt-1">
              配置 LLM Provider，系统将优先使用设为"默认"的配置调用 AI
            </p>
          </div>
          <Button onClick={openCreate}>
            <Plus className="mr-2 h-4 w-4" />
            添加 Provider
          </Button>
        </div>

        {/* ---- Table ---- */}
        {isLoading ? (
          <p className="text-muted-foreground">加载中…</p>
        ) : apiKeys.length === 0 ? (
          <div className="text-center py-20 border rounded-xl bg-muted/20">
            <Settings className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-1">还没有配置模型</h3>
            <p className="text-muted-foreground mb-4">
              添加 OpenAI / DeepSeek / 通义千问 等提供商的 API Key
            </p>
            <Button onClick={openCreate}>
              <Plus className="mr-2 h-4 w-4" />
              添加 Provider
            </Button>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Provider</TableHead>
                <TableHead>模型</TableHead>
                <TableHead>API Key</TableHead>
                <TableHead>Base URL</TableHead>
                <TableHead>状态</TableHead>
                <TableHead className="w-[120px]">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {apiKeys.map((key) => {
                const preset = Object.values(PROVIDER_PRESETS).find(
                  (p) => p.base_url === key.llm_base_url
                );
                const providerLabel =
                  preset?.name || key.provider_name || "自定义";
                return (
                  <TableRow key={key.id}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{key.name}</span>
                        <Badge variant="secondary" className="text-xs">
                          {providerLabel}
                        </Badge>
                        {key.is_default && (
                          <Star className="h-3.5 w-3.5 text-amber-500 fill-amber-500" />
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="font-mono text-sm">
                      {key.llm_model || "—"}
                    </TableCell>
                    <TableCell className="font-mono text-sm text-muted-foreground">
                      {maskKey(key.llm_api_key)}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground max-w-[200px] truncate">
                      {key.llm_base_url || "—"}
                    </TableCell>
                    <TableCell>
                      <Switch
                        checked={key.is_active}
                        onCheckedChange={() =>
                          toggleActive(key.id, key.is_active)
                        }
                      />
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => copyKey(key.id, key.key)}
                          title="复制 Key"
                        >
                          {copiedId === key.id ? (
                            <Check className="h-4 w-4 text-green-500" />
                          ) : (
                            <Copy className="h-4 w-4" />
                          )}
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => openEdit(key)}
                          title="编辑"
                        >
                          <Settings className="h-4 w-4" />
                        </Button>
                        {!key.is_default && (
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setDefault(key.id)}
                            title="设为默认"
                          >
                            <Star className="h-4 w-4" />
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => deleteAPIKey(key.id)}
                          title="删除"
                        >
                          <Trash2 className="h-4 w-4 text-red-500" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}

        {/* ---- Create / Edit Dialog ---- */}
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>
                {editingKey ? "编辑 Provider" : "添加 Provider"}
              </DialogTitle>
              <DialogDescription>
                配置 LLM 提供商的 API Key、Base URL 和模型
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 mt-2">
              {/* Name */}
              <div>
                <Label htmlFor="name">名称 *</Label>
                <Input
                  id="name"
                  placeholder="如：我的 DeepSeek"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                />
              </div>

              {/* Provider preset */}
              <div>
                <Label>提供商</Label>
                <Select value={formProvider} onValueChange={handleProviderChange}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(PROVIDER_PRESETS).map(([key, p]) => (
                      <SelectItem key={key} value={key}>
                        {p.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* API Key */}
              <div>
                <Label htmlFor="apiKey">LLM API Key *</Label>
                <Input
                  id="apiKey"
                  type="password"
                  placeholder="sk-..."
                  value={formApiKey}
                  onChange={(e) => setFormApiKey(e.target.value)}
                />
              </div>

              {/* Base URL */}
              <div>
                <Label htmlFor="baseUrl">Base URL *</Label>
                <Input
                  id="baseUrl"
                  placeholder="https://api.openai.com/v1"
                  value={formBaseUrl}
                  onChange={(e) => setFormBaseUrl(e.target.value)}
                />
              </div>

              {/* Model */}
              <div>
                <Label htmlFor="model">模型 *</Label>
                {preset && preset.models.length > 0 ? (
                  <Select value={formModel} onValueChange={setFormModel}>
                    <SelectTrigger>
                      <SelectValue placeholder="选择模型…" />
                    </SelectTrigger>
                    <SelectContent>
                      {preset.models.map((m) => (
                        <SelectItem key={m} value={m}>
                          {m}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <Input
                    id="model"
                    placeholder="如：gpt-4o"
                    value={formModel}
                    onChange={(e) => setFormModel(e.target.value)}
                  />
                )}
              </div>

              {/* Advanced: Embedding */}
              <div>
                <button
                  type="button"
                  className="text-sm text-muted-foreground hover:underline"
                  onClick={() => setShowAdvanced(!showAdvanced)}
                >
                  {showAdvanced ? "收起高级设置 ▲" : "高级设置：Embedding 模型 ▼"}
                </button>
                {showAdvanced && (
                  <div className="space-y-3 mt-3 pl-2 border-l-2 border-muted">
                    <div>
                      <Label htmlFor="embKey">Embedding API Key</Label>
                      <Input
                        id="embKey"
                        type="password"
                        placeholder="留空则使用 LLM API Key"
                        value={formEmbeddingApiKey}
                        onChange={(e) => setFormEmbeddingApiKey(e.target.value)}
                      />
                    </div>
                    <div>
                      <Label htmlFor="embUrl">Embedding Base URL</Label>
                      <Input
                        id="embUrl"
                        placeholder="留空则使用 LLM Base URL"
                        value={formEmbeddingBaseUrl}
                        onChange={(e) => setFormEmbeddingBaseUrl(e.target.value)}
                      />
                    </div>
                    <div>
                      <Label htmlFor="embModel">Embedding Model</Label>
                      <Input
                        id="embModel"
                        placeholder="如：text-embedding-3-small"
                        value={formEmbeddingModel}
                        onChange={(e) => setFormEmbeddingModel(e.target.value)}
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Switches */}
              <div className="flex items-center justify-between pt-2 border-t">
                <div className="flex items-center gap-2">
                  <Switch
                    checked={formIsDefault}
                    onCheckedChange={setFormIsDefault}
                  />
                  <Label>设为默认 Provider</Label>
                </div>
                <div className="flex items-center gap-2">
                  <Switch
                    checked={formIsActive}
                    onCheckedChange={setFormIsActive}
                  />
                  <Label>启用</Label>
                </div>
              </div>
            </div>

            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => {
                  setIsDialogOpen(false);
                  resetForm();
                }}
              >
                取消
              </Button>
              <Button onClick={saveApiKey} disabled={isCreating}>
                {isCreating ? "保存中…" : editingKey ? "更新" : "创建"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </DashboardLayout>
  );
}