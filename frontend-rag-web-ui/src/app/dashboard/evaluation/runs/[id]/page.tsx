"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft, Loader2, Brain, Search, Shuffle, Filter,
  TrendingUp, TrendingDown, Clock, GitBranch,
} from "lucide-react";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useToast } from "@/components/ui/use-toast";
import { api } from "@/lib/api";

interface EvalRun {
  id: number;
  dataset_name: string;
  status: string;
  total_cases: number;
  completed_cases: number;
  created_at: string;
  finished_at: string | null;
  // All metrics
  avg_recall_at_5: number | null;
  avg_recall_at_10: number | null;
  avg_precision_at_5: number | null;
  avg_mrr: number | null;
  avg_ndcg_at_5: number | null;
  dense_only_recall: number | null;
  bm25_only_recall: number | null;
  hybrid_recall: number | null;
  reranker_recall_gain: number | null;
  avg_faithfulness: number | null;
  avg_relevance: number | null;
  avg_correctness: number | null;
  avg_completeness: number | null;
  intent_accuracy: number | null;
  intent_confusion_pairs: any;
  react_accuracy: number | null;
  query_rewrite_rate: number | null;
  rewrite_success_rate: number | null;
  no_answer_precision: number | null;
  no_answer_recall: number | null;
  avg_latency_ms: number | null;
  latency_p50_ms: number | null;
  latency_p95_ms: number | null;
  avg_token_usage: number | null;
  avg_prompt_tokens: number | null;
  avg_completion_tokens: number | null;
  web_search_rate: number | null;
  web_search_success_rate: number | null;
  memory_impact_score: number | null;
  avg_overall_score: number | null;
}

interface EvalResult {
  id: number;
  case_index: number;
  question: string;
  expected_answer: string | null;
  question_type: string | null;
  difficulty: string | null;
  actual_answer: string | null;
  faithfulness: number | null;
  relevance: number | null;
  correctness: number | null;
  completeness: number | null;
  recall_at_5: number | null;
  hybrid_recall: number | null;
  intent_correct: number | null;
  intent_predicted: string | null;
  intent_expected: string | null;
  latency_ms: number | null;
  total_tokens: number | null;
  evaluation: string | null;
}

function MetricCard({
  title, value, desc, color, highlight, trend,
}: {
  title: string; value: string; desc: string;
  color?: string; highlight?: boolean; trend?: "up" | "down";
}) {
  const colorMap: Record<string, string> = {
    blue: "border-l-blue-500", green: "border-l-green-500", red: "border-l-red-500",
    orange: "border-l-orange-500", purple: "border-l-purple-500", pink: "border-l-pink-500",
    yellow: "border-l-yellow-500", cyan: "border-l-cyan-500", slate: "border-l-slate-500",
    rose: "border-l-rose-500", teal: "border-l-teal-500", sky: "border-l-sky-500",
  };
  return (
    <Card className={`border-l-4 ${colorMap[color || "blue"]} ${highlight ? "ring-2 ring-primary/20" : ""}`}>
      <CardHeader className="pb-1">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          {title}
          {trend && (trend === "up"
            ? <TrendingUp className="h-3 w-3 text-green-500" />
            : <TrendingDown className="h-3 w-3 text-red-500" />)}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <p className="text-xs text-muted-foreground mt-1">{desc}</p>
      </CardContent>
    </Card>
  );
}

export default function RunDetailPage() {
  const params = useParams();
  const runId = params.id as string;
  const [run, setRun] = useState<EvalRun | null>(null);
  const [results, setResults] = useState<EvalResult[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    fetchRun();
  }, [runId]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(fetchRun, 5000);
    return () => clearInterval(interval);
  }, [autoRefresh, runId]);

  const fetchRun = async () => {
    try {
      const [runData, resultsData] = await Promise.all([
        api.get(`/api/evaluation/runs/${runId}`),
        api.get(`/api/evaluation/runs/${runId}/results`),
      ]);
      setRun(runData);
      setResults(Array.isArray(resultsData) ? resultsData : []);
      if (runData?.status === "pending" || runData?.status === "running") {
        setAutoRefresh(true);
      } else {
        setAutoRefresh(false);
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to load run", variant: "destructive" });
    } finally {
      setIsLoading(false);
    }
  };

  const fmtPercent = (v: number | null) => v != null ? `${(v * 100).toFixed(1)}%` : "--";
  const fmtScore = (v: number | null) => v != null ? `${v.toFixed(1)}/5` : "--";
  const fmtMs = (v: number | null) => v != null ? `${Math.round(v)}ms` : "--";
  const fmtNum = (v: number | null) => v != null ? Math.round(v).toLocaleString() : "--";

  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="flex justify-center py-20"><Loader2 className="h-8 w-8 animate-spin" /></div>
      </DashboardLayout>
    );
  }

  if (!run) {
    return (
      <DashboardLayout>
        <div className="text-center py-20">
          <h2 className="text-xl font-bold">Run not found</h2>
          <Link href="/dashboard/evaluation/runs"><Button variant="outline" className="mt-4">Back to Runs</Button></Link>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <Link href="/dashboard/evaluation/runs" className="text-sm text-muted-foreground hover:underline mb-2 block">
            ← Back to Runs
          </Link>
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-2xl font-bold">{run.dataset_name}</h1>
              <p className="text-muted-foreground">
                Run #{run.id} · {run.completed_cases}/{run.total_cases} cases · {new Date(run.created_at).toLocaleString()}
              </p>
            </div>
            <Badge className={
              run.status === "completed" ? "bg-green-100 text-green-800" :
              run.status === "running" ? "bg-blue-100 text-blue-800" :
              run.status === "failed" ? "bg-red-100 text-red-800" : ""
            }>
              {run.status === "running" && <Loader2 className="mr-1 h-3 w-3 animate-spin inline" />}
              {run.status}
            </Badge>
          </div>
        </div>

        {/* Retrieval Quality */}
        <div>
          <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <Search className="h-5 w-5 text-blue-500" />检索质量
          </h3>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
            <MetricCard title="Recall@5" value={fmtPercent(run.avg_recall_at_5)} desc="Top-5 chunk hit rate" color="blue" />
            <MetricCard title="Recall@10" value={fmtPercent(run.avg_recall_at_10)} desc="Top-10 chunk hit rate" color="blue" />
            <MetricCard title="Precision@5" value={fmtPercent(run.avg_precision_at_5)} desc="Top-5 chunk accuracy" color="blue" />
            <MetricCard title="MRR" value={run.avg_mrr?.toFixed(3) ?? "--"} desc="First relevant rank" color="blue" />
            <MetricCard title="NDCG@5" value={run.avg_ndcg_at_5?.toFixed(3) ?? "--"} desc="Rank-weighted quality" color="blue" />
          </div>
        </div>

        {/* Hybrid Pipeline Stages */}
        <div>
          <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <Shuffle className="h-5 w-5 text-purple-500" />混合检索各阶段
          </h3>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <MetricCard title="Dense Only" value={fmtPercent(run.dense_only_recall)} desc="Vector retrieval recall" color="purple" />
            <MetricCard title="BM25 Only" value={fmtPercent(run.bm25_only_recall)} desc="Sparse retrieval recall" color="purple" />
            <MetricCard title="RRF Hybrid" value={fmtPercent(run.hybrid_recall)} desc="Fused retrieval recall" color="pink" highlight />
            <MetricCard title="Reranker Gain Δ" value={fmtPercent(run.reranker_recall_gain)} desc="Reranker improvement" color="rose"
              trend={run.reranker_recall_gain != null ? (run.reranker_recall_gain >= 0 ? "up" : "down") : undefined} />
          </div>
        </div>

        {/* Generation Quality */}
        <div>
          <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <Brain className="h-5 w-5 text-green-500" />生成质量 (LLM-as-Judge)
          </h3>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <MetricCard title="Faithfulness" value={fmtScore(run.avg_faithfulness)} desc="No hallucination" color="green" />
            <MetricCard title="Relevance" value={fmtScore(run.avg_relevance)} desc="Directly answers" color="green" />
            <MetricCard title="Correctness" value={fmtScore(run.avg_correctness)} desc="Factually correct" color="green" />
            <MetricCard title="Completeness" value={fmtScore(run.avg_completeness)} desc="No missing info" color="green" />
          </div>
        </div>

        {/* Intent & React */}
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
              <GitBranch className="h-5 w-5 text-orange-500" />意图分类 & 决策
            </h3>
            <div className="grid gap-4 grid-cols-2">
              <MetricCard title="Intent Acc." value={fmtPercent(run.intent_accuracy)} desc="6-class accuracy" color="orange" />
              <MetricCard title="React Acc." value={fmtPercent(run.react_accuracy)} desc="answer/retry/stop" color="orange" />
              <MetricCard title="Rewrite Rate" value={fmtPercent(run.query_rewrite_rate)} desc="Query rewrite triggered" color="orange" />
              <MetricCard title="Rewrite Success" value={fmtPercent(run.rewrite_success_rate)} desc="Rewrite improved recall" color="orange" />
            </div>
          </div>
          <div>
            <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
              <Clock className="h-5 w-5 text-yellow-500" />性能
            </h3>
            <div className="grid gap-4 grid-cols-2">
              <MetricCard title="Avg Latency" value={fmtMs(run.avg_latency_ms)} desc="Average response" color="yellow" />
              <MetricCard title="P50 Latency" value={fmtMs(run.latency_p50_ms)} desc="Median response" color="yellow" />
              <MetricCard title="P95 Latency" value={fmtMs(run.latency_p95_ms)} desc="95th percentile" color="yellow" />
              <MetricCard title="Avg Tokens" value={fmtNum(run.avg_token_usage)} desc="Per query" color="yellow" />
            </div>
          </div>
        </div>

        {/* Per-Case Results */}
        <Card>
          <CardHeader>
            <CardTitle>Per-Case Results</CardTitle>
            <CardDescription>{results.length} cases evaluated</CardDescription>
          </CardHeader>
          <CardContent>
            {results.length === 0 ? (
              <p className="text-center py-8 text-muted-foreground">
                {run.status === "running" ? "Evaluation in progress..." : "No results yet"}
              </p>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>#</TableHead>
                      <TableHead className="max-w-[300px]">Question</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Faith.</TableHead>
                      <TableHead>Relev.</TableHead>
                      <TableHead>Correct.</TableHead>
                      <TableHead>Recall@5</TableHead>
                      <TableHead>Hybrid</TableHead>
                      <TableHead>Latency</TableHead>
                      <TableHead>Judge Notes</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {results.map((r) => (
                      <TableRow key={r.id}>
                        <TableCell>{r.case_index + 1}</TableCell>
                        <TableCell className="max-w-[300px] truncate">{r.question}</TableCell>
                        <TableCell><Badge variant="outline">{r.question_type || "--"}</Badge></TableCell>
                        <TableCell>{fmtScore(r.faithfulness)}</TableCell>
                        <TableCell>{fmtScore(r.relevance)}</TableCell>
                        <TableCell>{fmtScore(r.correctness)}</TableCell>
                        <TableCell>{fmtPercent(r.recall_at_5)}</TableCell>
                        <TableCell>{fmtPercent(r.hybrid_recall)}</TableCell>
                        <TableCell>{fmtMs(r.latency_ms)}</TableCell>
                        <TableCell className="max-w-[200px] truncate text-sm text-muted-foreground">
                          {r.evaluation || "--"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}