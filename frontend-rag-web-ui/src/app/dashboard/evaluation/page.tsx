"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  BarChart3, Database, Play, TrendingUp, TrendingDown, Clock,
  CheckCircle2, XCircle, AlertTriangle, Brain, GitBranch,
  Search, Zap, Shuffle, Filter, RefreshCw, Coins, EyeOff,
  Gauge, Layers, Target,
} from "lucide-react";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/components/ui/use-toast";
import { api, ApiError } from "@/lib/api";

interface EvalStats {
  // 基础统计
  total_runs: number;
  total_datasets: number;

  // 标准检索指标
  avg_recall_at_5: number | null;
  avg_recall_at_10: number | null;
  avg_precision_at_5: number | null;
  avg_mrr: number | null;
  avg_ndcg_at_5: number | null;

  // 生成质量 (LLM-as-Judge)
  avg_faithfulness: number | null;
  avg_relevance: number | null;
  avg_correctness: number | null;
  avg_completeness: number | null;

  // ========== 项目特有能力指标 ==========

  // 意图分类
  intent_accuracy: number | null;
  intent_confusion_pairs: { from: string; to: string; count: number }[];

  // 混合检索各阶段对比
  dense_only_recall: number | null;    // 纯 Dense 召回
  bm25_only_recall: number | null;     // 纯 BM25 召回
  hybrid_recall: number | null;        // RRF 融合后召回
  reranker_recall_gain: number | null; // Reranker 带来的召回增益

  // RAG React 决策
  react_accuracy: number | null;       // answer/retry/stop 决策准确率
  query_rewrite_rate: number | null;   // 查询改写触发比例
  rewrite_success_rate: number | null; // 改写后检索改善比例

  // 拒答/无答案
  no_answer_precision: number | null;  // 拒答准确率
  no_answer_recall: number | null;     // 拒答召回率

  // 系统性能
  avg_latency_ms: number | null;
  latency_p50_ms: number | null;
  latency_p95_ms: number | null;
  avg_token_usage: number | null;      // 平均 Token 消耗
  avg_prompt_tokens: number | null;
  avg_completion_tokens: number | null;

  // 联网搜索
  web_search_rate: number | null;      // 触发联网搜索的比例
  web_search_success_rate: number | null; // 联网搜索后回答质量

  // 记忆
  memory_impact_score: number | null;  // 记忆上下文对答案的改善幅度
}

interface RecentRun {
  id: number;
  dataset_name: string;
  status: string;
  created_at: string;
  avg_overall_score: number | null;
  total_cases: number;
  // 项目特有
  intent_accuracy: number | null;
  hybrid_recall: number | null;
  avg_latency_ms: number | null;
}

export default function EvaluationPage() {
  const [stats, setStats] = useState<EvalStats | null>(null);
  const [recentRuns, setRecentRuns] = useState<RecentRun[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const { toast } = useToast();

  useEffect(() => {
    fetchOverview();
  }, []);

  const fetchOverview = async () => {
    try {
      // Use the backend overview endpoint which aggregates all completed runs
      const overviewData = await api.get("/api/evaluation/overview").catch(() => null);
      if (overviewData) {
        setStats(overviewData);
      }

      // Fetch recent runs for the table
      const runsData = await api.get("/api/evaluation/runs").catch(() => []);
      const runs = Array.isArray(runsData) ? runsData : [];
      setRecentRuns(runs.slice(0, 5));

      // If overview failed, compute from runs manually
      if (!overviewData) {
        const completedRuns = runs.filter((r: any) => r.status === "completed");
        const avgOf = (key: string) => {
          const vals = completedRuns.map((r: any) => r[key]).filter((v: any) => v != null);
          return vals.length > 0 ? vals.reduce((a: number, b: number) => a + b, 0) / vals.length : null;
        };
        const computed: EvalStats = {
          total_runs: runs.length,
          total_datasets: 0,
          avg_recall_at_5: avgOf("avg_recall_at_5"),
          avg_recall_at_10: avgOf("avg_recall_at_10"),
          avg_precision_at_5: avgOf("avg_precision_at_5"),
          avg_mrr: avgOf("avg_mrr"),
          avg_ndcg_at_5: avgOf("avg_ndcg_at_5"),
          avg_faithfulness: avgOf("avg_faithfulness"),
          avg_relevance: avgOf("avg_relevance"),
          avg_correctness: avgOf("avg_correctness"),
          avg_completeness: avgOf("avg_completeness"),
          intent_accuracy: avgOf("intent_accuracy"),
          intent_confusion_pairs: [],
          dense_only_recall: avgOf("dense_only_recall"),
          bm25_only_recall: avgOf("bm25_only_recall"),
          hybrid_recall: avgOf("hybrid_recall"),
          reranker_recall_gain: avgOf("reranker_recall_gain"),
          react_accuracy: avgOf("react_accuracy"),
          query_rewrite_rate: avgOf("query_rewrite_rate"),
          rewrite_success_rate: avgOf("rewrite_success_rate"),
          no_answer_precision: avgOf("no_answer_precision"),
          no_answer_recall: avgOf("no_answer_recall"),
          avg_latency_ms: avgOf("avg_latency_ms"),
          latency_p50_ms: avgOf("latency_p50_ms"),
          latency_p95_ms: avgOf("latency_p95_ms"),
          avg_token_usage: avgOf("avg_token_usage"),
          avg_prompt_tokens: avgOf("avg_prompt_tokens"),
          avg_completion_tokens: avgOf("avg_completion_tokens"),
          web_search_rate: avgOf("web_search_rate"),
          web_search_success_rate: avgOf("web_search_success_rate"),
          memory_impact_score: avgOf("memory_impact_score"),
        };
        try {
          const datasetsData = await api.get("/api/evaluation/datasets");
          computed.total_datasets = Array.isArray(datasetsData) ? datasetsData.length : 0;
        } catch { /* ignore */ }
        setStats(computed);
      }
    } catch {
      // endpoints not yet built — show empty state gracefully
    } finally {
      setIsLoading(false);
    }
  };

  const fmtPercent = (v: number | null | undefined) => v != null ? `${(v * 100).toFixed(1)}%` : "--";
  const fmtScore = (v: number | null | undefined) => v != null ? `${v.toFixed(1)}/5` : "--";
  const fmtMs = (v: number | null | undefined) => v != null ? `${Math.round(v)}ms` : "--";
  const fmtNum = (v: number | null | undefined) => v != null ? Math.round(v).toLocaleString() : "--";
  const fmtDec = (v: number | null | undefined, d = 3) => v != null ? v.toFixed(d) : "--";

  const statusBadge = (status: string) => {
    switch (status) {
      case "completed": return <Badge className="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">Completed</Badge>;
      case "running": return <Badge className="bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">Running</Badge>;
      case "failed": return <Badge variant="destructive">Failed</Badge>;
      default: return <Badge variant="outline">{status}</Badge>;
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-8">
        {/* ========== Header ========== */}
        <div className="bg-card rounded-lg shadow-sm p-6">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div>
              <h2 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
                RAG Evaluation
              </h2>
              <p className="text-muted-foreground mt-1">
                Retrieval · Generation · Intent · Latency — full pipeline quality dashboard
              </p>
            </div>
            <div className="flex gap-3">
              <Link href="/dashboard/evaluation/datasets">
                <Button variant="outline">
                  <Database className="mr-2 h-4 w-4" />
                  Manage Datasets
                </Button>
              </Link>
              <Link href="/dashboard/evaluation/runs">
                <Button>
                  <Play className="mr-2 h-4 w-4" />
                  View Runs
                </Button>
              </Link>
            </div>
          </div>
        </div>

        {/* ========== Section 1: Retrieval Quality ========== */}
        <div>
          <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <Search className="h-5 w-5 text-blue-500" />
            检索质量 Retrieval
          </h3>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <MetricCard title="Recall@5" value={fmtPercent(stats?.avg_recall_at_5)} desc="Top-5 中相关片段命中率" color="blue" />
            <MetricCard title="Recall@10" value={fmtPercent(stats?.avg_recall_at_10)} desc="Top-10 中相关片段命中率" color="blue" />
            <MetricCard title="Precision@5" value={fmtPercent(stats?.avg_precision_at_5)} desc="Top-5 中相关片段占比" color="indigo" />
            <MetricCard title="MRR" value={fmtDec(stats?.avg_mrr)} desc="首个相关片段排位质量 (0-1)" color="indigo" />
          </div>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mt-4">
            <MetricCard title="NDCG@5" value={fmtDec(stats?.avg_ndcg_at_5)} desc="排序质量加权得分 (0-1)" color="violet" />
          </div>
        </div>

        {/* ========== Section 2: 混合检索各阶段对比（项目独有！）========== */}
        <div>
          <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <Shuffle className="h-5 w-5 text-purple-500" />
            混合检索各阶段对比 Hybrid Pipeline Stage Comparison
          </h3>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <MetricCard
              title="Dense Only Recall"
              value={fmtPercent(stats?.dense_only_recall)}
              desc="纯向量检索召回率（baseline）"
              icon={<Layers className="h-4 w-4" />}
              color="purple"
            />
            <MetricCard
              title="BM25 Only Recall"
              value={fmtPercent(stats?.bm25_only_recall)}
              desc="纯 BM25 检索召回率"
              icon={<Layers className="h-4 w-4" />}
              color="purple"
            />
            <MetricCard
              title="RRF Hybrid Recall"
              value={fmtPercent(stats?.hybrid_recall)}
              desc="Dense+BM25 RRF 融合后召回"
              icon={<Shuffle className="h-4 w-4" />}
              color="pink"
              highlight
            />
            <MetricCard
              title="Reranker Gain Δ"
              value={fmtPercent(stats?.reranker_recall_gain)}
              desc="Reranker 带来的召回增益"
              icon={<Filter className="h-4 w-4" />}
              color="rose"
              trend={stats?.reranker_recall_gain != null ? (stats.reranker_recall_gain >= 0 ? "up" : "down") : undefined}
            />
          </div>
        </div>

        {/* ========== Section 3: 生成质量 ========== */}
        <div>
          <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <Brain className="h-5 w-5 text-green-500" />
            生成质量 Generation (LLM-as-Judge)
          </h3>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <MetricCard title="Faithfulness 忠实度" value={fmtScore(stats?.avg_faithfulness)} desc="答案是否基于文档，有无幻觉" color="green" />
            <MetricCard title="Relevance 相关性" value={fmtScore(stats?.avg_relevance)} desc="答案是否直接回应问题" color="emerald" />
            <MetricCard title="Correctness 正确性" value={fmtScore(stats?.avg_correctness)} desc="答案是否事实正确" color="teal" />
            <MetricCard title="Completeness 完整性" value={fmtScore(stats?.avg_completeness)} desc="是否遗漏文档关键信息" color="cyan" />
          </div>
        </div>

        {/* ========== Section 4: 意图分类（项目独有！）========== */}
        <div>
          <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <GitBranch className="h-5 w-5 text-orange-500" />
            意图分类 Intent Classification
          </h3>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <MetricCard
              title="Intent Accuracy"
              value={fmtPercent(stats?.intent_accuracy)}
              desc="6分类整体准确率 (greeting/general/knowledge/summary/follow_up/other)"
              icon={<Target className="h-4 w-4" />}
              color="orange"
              highlight
            />
            <MetricCard
              title="Top Confusion Pair"
              value={stats?.intent_confusion_pairs?.[0]
                ? `${stats.intent_confusion_pairs[0].from}→${stats.intent_confusion_pairs[0].to}`
                : "--"}
              desc={stats?.intent_confusion_pairs?.[0]
                ? `最常误判: ${stats.intent_confusion_pairs[0].count} 次`
                : "最易混淆的分类对"}
              icon={<AlertTriangle className="h-4 w-4" />}
              color="amber"
            />
          </div>
        </div>

        {/* ========== Section 5: RAG React 决策 + 查询改写（项目独有！）========== */}
        <div>
          <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <RefreshCw className="h-5 w-5 text-red-500" />
            RAG React 决策与查询改写 Agent Decision &amp; Query Rewrite
          </h3>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <MetricCard
              title="React Accuracy"
              value={fmtPercent(stats?.react_accuracy)}
              desc="answer/retry/stop 决策准确率"
              icon={<GitBranch className="h-4 w-4" />}
              color="red"
            />
            <MetricCard
              title="Rewrite Trigger Rate"
              value={fmtPercent(stats?.query_rewrite_rate)}
              desc="触发查询改写的比例"
              icon={<RefreshCw className="h-4 w-4" />}
              color="red"
            />
            <MetricCard
              title="Rewrite Success Rate"
              value={fmtPercent(stats?.rewrite_success_rate)}
              desc="改写后检索 Recall 改善的比例"
              icon={<TrendingUp className="h-4 w-4" />}
              color="rose"
              trend={stats?.rewrite_success_rate != null ? (stats.rewrite_success_rate >= 0.5 ? "up" : "down") : undefined}
            />
            <MetricCard
              title="No-Answer Precision"
              value={fmtPercent(stats?.no_answer_precision)}
              desc="拒答准确率（该拒的时候拒了吗）"
              icon={<EyeOff className="h-4 w-4" />}
              color="slate"
            />
          </div>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mt-4">
            <MetricCard
              title="No-Answer Recall"
              value={fmtPercent(stats?.no_answer_recall)}
              desc="拒答召回率（不该拒的时候拒了吗）"
              icon={<XCircle className="h-4 w-4" />}
              color="slate"
            />
          </div>
        </div>

        {/* ========== Section 6: 系统性能 ========== */}
        <div>
          <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <Gauge className="h-5 w-5 text-yellow-500" />
            系统性能 Performance
          </h3>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <MetricCard title="Avg Latency" value={fmtMs(stats?.avg_latency_ms)} desc="平均端到端延迟" icon={<Clock className="h-4 w-4" />} color="yellow" />
            <MetricCard title="P50 Latency" value={fmtMs(stats?.latency_p50_ms)} desc="中位数延迟（50% 请求）" icon={<Clock className="h-4 w-4" />} color="yellow" />
            <MetricCard title="P95 Latency" value={fmtMs(stats?.latency_p95_ms)} desc="95分位延迟（长尾）" icon={<TrendingUp className="h-4 w-4" />} color="amber" />
            <MetricCard title="Avg Tokens" value={fmtNum(stats?.avg_token_usage)} desc="每次查询平均 Token 消耗" icon={<Coins className="h-4 w-4" />} color="yellow" />
          </div>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mt-4">
            <MetricCard title="Avg Prompt Tokens" value={fmtNum(stats?.avg_prompt_tokens)} desc="Prompt 平均 Token 数" color="lime" />
            <MetricCard title="Avg Completion Tokens" value={fmtNum(stats?.avg_completion_tokens)} desc="生成平均 Token 数" color="lime" />
          </div>
        </div>

        {/* ========== Section 7: 联网搜索 + 记忆（项目独有！）========== */}
        <div>
          <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <Zap className="h-5 w-5 text-cyan-500" />
            联网搜索 &amp; 记忆 Web Search &amp; Memory
          </h3>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <MetricCard
              title="Web Search Rate"
              value={fmtPercent(stats?.web_search_rate)}
              desc="触发联网搜索的查询比例"
              icon={<Search className="h-4 w-4" />}
              color="sky"
            />
            <MetricCard
              title="Web Search Quality"
              value={fmtPercent(stats?.web_search_success_rate)}
              desc="联网搜索后回答质量达标率"
              icon={<CheckCircle2 className="h-4 w-4" />}
              color="cyan"
            />
            <MetricCard
              title="Memory Impact Δ"
              value={fmtPercent(stats?.memory_impact_score)}
              desc="长期记忆上下文对答案的改善幅度"
              icon={<Brain className="h-4 w-4" />}
              color="teal"
              trend={stats?.memory_impact_score != null ? (stats.memory_impact_score >= 0 ? "up" : "down") : undefined}
            />
          </div>
        </div>

        {/* ========== 系统概览卡片 ========== */}
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Datasets</CardTitle>
              <Database className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.total_datasets ?? "--"}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Runs</CardTitle>
              <Play className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.total_runs ?? "--"}</div>
            </CardContent>
          </Card>
        </div>

        {/* ========== Recent Runs ========== */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Evaluation Runs</CardTitle>
            <CardDescription>Latest evaluation runs across all datasets</CardDescription>
          </CardHeader>
          <CardContent>
            {recentRuns.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <BarChart3 className="mx-auto h-12 w-12 mb-4 opacity-50" />
                <p className="text-lg font-medium">No evaluation runs yet</p>
                <p className="text-sm mt-1">Upload a dataset and start your first evaluation run</p>
                <Link href="/dashboard/evaluation/datasets">
                  <Button className="mt-4" variant="outline">
                    <Database className="mr-2 h-4 w-4" />Go to Datasets
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                {recentRuns.map((run) => (
                  <Link
                    key={run.id}
                    href={`/dashboard/evaluation/runs/${run.id}`}
                    className="flex items-center justify-between p-4 rounded-lg border hover:bg-accent/50 transition-colors"
                  >
                    <div className="space-y-1">
                      <p className="font-medium">{run.dataset_name}</p>
                      <div className="flex items-center gap-3 text-xs text-muted-foreground">
                        <span>{run.total_cases} cases</span>
                        <span>·</span>
                        <span>{new Date(run.created_at).toLocaleDateString()}</span>
                        {run.intent_accuracy != null && (
                          <>
                            <span>·</span>
                            <span>Intent: {fmtPercent(run.intent_accuracy)}</span>
                          </>
                        )}
                        {run.hybrid_recall != null && (
                          <>
                            <span>·</span>
                            <span>Hybrid Recall: {fmtPercent(run.hybrid_recall)}</span>
                          </>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      {run.avg_overall_score != null && (
                        <span className="text-sm font-semibold">Score: {run.avg_overall_score.toFixed(1)}</span>
                      )}
                      {run.avg_latency_ms != null && (
                        <span className="text-xs text-muted-foreground">{Math.round(run.avg_latency_ms)}ms</span>
                      )}
                      {statusBadge(run.status)}
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* ========== Metric Definitions ========== */}
        <Card>
          <CardHeader>
            <CardTitle>All Metrics Reference</CardTitle>
            <CardDescription>
              32 evaluation metrics across 7 dimensions — computed via deterministic code &amp; LLM-as-Judge
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              <MetricDef color="blue" title="Recall@K">Top-K 结果中包含标注相关片段的比例。同时对比 Dense-only、BM25-only、RRF Hybrid 三个阶段。</MetricDef>
              <MetricDef color="indigo" title="Precision@K / MRR / NDCG@K">精度、首位排名质量和加权排序质量。Reranker Gain 衡量精排带来的增量。</MetricDef>
              <MetricDef color="green" title="Faithfulness (忠实度)">LLM-as-Judge 评分：答案是否完全基于检索文档，有无编造幻觉。1=严重幻觉，5=完全忠实。</MetricDef>
              <MetricDef color="emerald" title="Relevance (相关性)">LLM-as-Judge 评分：答案是否直接回应用户问题。1=答非所问，5=精准回应。</MetricDef>
              <MetricDef color="teal" title="Correctness (正确性)">LLM-as-Judge 评分：对比 Ground Truth，答案事实是否正确。1=完全错误，5=完全正确。</MetricDef>
              <MetricDef color="cyan" title="Completeness (完整性)">LLM-as-Judge 评分：是否遗漏了文档中的关键信息。1=严重遗漏，5=信息完整。</MetricDef>
              <MetricDef color="orange" title="Intent Accuracy">6 分类意图识别准确率。Confusion Matrix 展示 greeting ↔ general_question 等易混淆对。</MetricDef>
              <MetricDef color="red" title="React Decision Accuracy">RAG Agent 决策准确率：answer → 生成回答、retry → 改写查询重新检索、stop → 说明无依据。</MetricDef>
              <MetricDef color="rose" title="Query Rewrite">查询改写触发率和改写后 Recall 改善率。衡量 LangGraph 多轮检索的价值。</MetricDef>
              <MetricDef color="slate" title="No-Answer Detection">拒答准确率 & 召回率：该拒时拒了吗？不该拒时乱拒了吗？</MetricDef>
              <MetricDef color="yellow" title="Latency & Token">P50/P95 延迟和 Token 消耗。Prompt/Completion 分开统计，用于成本估算和性能调优。</MetricDef>
              <MetricDef color="sky" title="Web Search Fallback">内部资料不足时触发联网搜索的比例及搜索后回答质量。</MetricDef>
              <MetricDef color="teal" title="Memory Impact">Mem0 长期记忆上下文对回答质量的改善幅度。正值 = 记忆有帮助，负值 = 记忆干扰。</MetricDef>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}

// ── 可复用子组件 ──

function MetricCard({
  title, value, desc, icon, color, highlight, trend,
}: {
  title: string;
  value: string;
  desc: string;
  icon?: React.ReactNode;
  color?: string;
  highlight?: boolean;
  trend?: "up" | "down";
}) {
  const colorMap: Record<string, string> = {
    blue: "bg-blue-500", indigo: "bg-indigo-500", violet: "bg-violet-500",
    purple: "bg-purple-500", pink: "bg-pink-500", rose: "bg-rose-500",
    green: "bg-green-500", emerald: "bg-emerald-500", teal: "bg-teal-500",
    cyan: "bg-cyan-500", sky: "bg-sky-500",
    orange: "bg-orange-500", amber: "bg-amber-500", yellow: "bg-yellow-500",
    lime: "bg-lime-500", red: "bg-red-500", slate: "bg-slate-500",
  };

  return (
    <Card className={highlight ? "ring-2 ring-primary/20" : ""}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div className="flex items-center gap-2">
          {icon && <span className="text-muted-foreground">{icon}</span>}
          <CardTitle className="text-sm font-medium">{title}</CardTitle>
          {trend && (
            <span className={trend === "up" ? "text-green-500" : "text-red-500"}>
              {trend === "up" ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <p className="text-xs text-muted-foreground mt-1">{desc}</p>
      </CardContent>
    </Card>
  );
}

function MetricDef({ color, title, children }: { color: string; title: string; children: React.ReactNode }) {
  const colorMap: Record<string, string> = {
    blue: "bg-blue-500", indigo: "bg-indigo-500", violet: "bg-violet-500",
    purple: "bg-purple-500", pink: "bg-pink-500", rose: "bg-rose-500",
    green: "bg-green-500", emerald: "bg-emerald-500", teal: "bg-teal-500",
    cyan: "bg-cyan-500", sky: "bg-sky-500",
    orange: "bg-orange-500", amber: "bg-amber-500", yellow: "bg-yellow-500",
    lime: "bg-lime-500", red: "bg-red-500", slate: "bg-slate-500",
  };
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <div className={`h-8 w-1 rounded-full ${colorMap[color] || "bg-slate-500"}`} />
        <h4 className="font-semibold">{title}</h4>
      </div>
      <p className="text-sm text-muted-foreground">{children}</p>
    </div>
  );
}