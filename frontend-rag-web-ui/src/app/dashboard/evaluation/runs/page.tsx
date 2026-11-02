"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Play, Eye, Loader2, Clock } from "lucide-react";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/components/ui/use-toast";
import { api, ApiError } from "@/lib/api";

interface EvalRun {
  id: number;
  dataset_id: number;
  dataset_name: string;
  status: string;
  total_cases: number;
  completed_cases: number;
  created_at: string;
  finished_at: string | null;
  avg_faithfulness: number | null;
  avg_relevance: number | null;
  avg_correctness: number | null;
  avg_completeness: number | null;
  intent_accuracy: number | null;
  hybrid_recall: number | null;
  avg_latency_ms: number | null;
  avg_overall_score: number | null;
}

interface Dataset {
  id: number;
  name: string;
  sample_count: number;
}

export default function RunsPage() {
  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRunning, setIsRunning] = useState(false);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>("");
  const { toast } = useToast();

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [runsData, datasetsData] = await Promise.all([
        api.get("/api/evaluation/runs"),
        api.get("/api/evaluation/datasets"),
      ]);
      setRuns(Array.isArray(runsData) ? runsData : []);
      setDatasets(Array.isArray(datasetsData) ? datasetsData : []);
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to load runs",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleStartRun = async () => {
    if (!selectedDatasetId) return;
    setIsRunning(true);
    try {
      await api.post("/api/evaluation/runs", { dataset_id: Number(selectedDatasetId) });
      setIsDialogOpen(false);
      toast({
        title: "Success",
        description: "Evaluation run started",
      });
      // Refresh after a short delay
      setTimeout(() => fetchData(), 1000);
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof ApiError ? error.message : "Failed to start run",
        variant: "destructive",
      });
    } finally {
      setIsRunning(false);
    }
  };

  const statusBadge = (status: string) => {
    switch (status) {
      case "completed":
        return <Badge className="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">Completed</Badge>;
      case "running":
        return <Badge className="bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"><Loader2 className="mr-1 h-3 w-3 animate-spin inline" />Running</Badge>;
      case "pending":
        return <Badge variant="outline"><Clock className="mr-1 h-3 w-3" />Pending</Badge>;
      case "failed":
        return <Badge variant="destructive">Failed</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const fmtPercent = (v: number | null) => v != null ? `${(v * 100).toFixed(1)}%` : "--";
  const fmtScore = (v: number | null) => v != null ? `${v.toFixed(1)}/5` : "--";
  const fmtMs = (v: number | null) => v != null ? `${Math.round(v)}ms` : "--";

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <Link href="/dashboard/evaluation" className="text-sm text-muted-foreground hover:underline mb-1 block">
              ← Back to Overview
            </Link>
            <h1 className="text-2xl font-bold">Evaluation Runs</h1>
            <p className="text-muted-foreground mt-1">
              Run evaluations on datasets to measure RAG quality
            </p>
          </div>
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <Button onClick={() => setIsDialogOpen(true)} disabled={datasets.length === 0}>
              <Play className="mr-2 h-4 w-4" />
              New Run
            </Button>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Start Evaluation Run</DialogTitle>
                <DialogDescription>
                  Select a dataset to evaluate. The RAG pipeline will be run on every Q&A pair.
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="grid gap-2">
                  <Label htmlFor="dataset">Dataset</Label>
                  <Select value={selectedDatasetId} onValueChange={setSelectedDatasetId}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select a dataset..." />
                    </SelectTrigger>
                    <SelectContent>
                      {datasets.map((ds) => (
                        <SelectItem key={ds.id} value={String(ds.id)}>
                          {ds.name} ({ds.sample_count} cases)
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsDialogOpen(false)}>Cancel</Button>
                <Button onClick={handleStartRun} disabled={!selectedDatasetId || isRunning}>
                  {isRunning ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                  Start Run
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>

        {/* Runs Table */}
        <Card>
          <CardHeader>
            <CardTitle>All Runs</CardTitle>
            <CardDescription>{runs.length} evaluation runs total</CardDescription>
          </CardHeader>
          <CardContent>
            {runs.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <Play className="mx-auto h-12 w-12 mb-4 opacity-50" />
                <p className="text-lg font-medium">No runs yet</p>
                <p className="text-sm mt-1">Upload a dataset first, then start an evaluation run</p>
                <Link href="/dashboard/evaluation/datasets">
                  <Button className="mt-4" variant="outline">Upload Dataset</Button>
                </Link>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>Dataset</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Cases</TableHead>
                    <TableHead>Intent Acc.</TableHead>
                    <TableHead>Hybrid Recall</TableHead>
                    <TableHead>Faithfulness</TableHead>
                    <TableHead>Latency</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {runs.map((run) => (
                    <TableRow key={run.id}>
                      <TableCell className="font-mono">#{run.id}</TableCell>
                      <TableCell className="font-medium">{run.dataset_name}</TableCell>
                      <TableCell>{statusBadge(run.status)}</TableCell>
                      <TableCell>{run.completed_cases}/{run.total_cases}</TableCell>
                      <TableCell>{fmtPercent(run.intent_accuracy)}</TableCell>
                      <TableCell>{fmtPercent(run.hybrid_recall)}</TableCell>
                      <TableCell>{fmtScore(run.avg_faithfulness)}</TableCell>
                      <TableCell>{fmtMs(run.avg_latency_ms)}</TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {new Date(run.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell>
                        <Link href={`/dashboard/evaluation/runs/${run.id}`}>
                          <Button variant="ghost" size="sm">
                            <Eye className="mr-1 h-3 w-3" />
                            View
                          </Button>
                        </Link>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}