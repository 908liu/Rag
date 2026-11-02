"use client";

import { useEffect, useState } from "react";
import { Plus, Upload, FileText, Trash2, Eye, Download } from "lucide-react";
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
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
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
import { useToast } from "@/components/ui/use-toast";
import { api, ApiError } from "@/lib/api";

interface EvalDataset {
  id: number;
  name: string;
  description: string;
  sample_count: number;
  created_at: string;
  tags?: string[];
}

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState<EvalDataset[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [previewDataset, setPreviewDataset] = useState<EvalDataset | null>(null);
  const [previewSamples, setPreviewSamples] = useState<any[]>([]);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);

  // Create form
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);

  const { toast } = useToast();

  useEffect(() => {
    fetchDatasets();
  }, []);

  const fetchDatasets = async () => {
    try {
      const data = await api.get("/api/evaluation/datasets");
      setDatasets(Array.isArray(data) ? data : []);
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to fetch datasets",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!newName.trim()) {
      toast({
        title: "Error",
        description: "Please enter a dataset name",
        variant: "destructive",
      });
      return;
    }

    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append("name", newName);
      formData.append("description", newDescription);
      if (uploadFile) {
        formData.append("file", uploadFile);
      }

      const data = await api.post("/api/evaluation/datasets", formData);
      setDatasets([...datasets, data]);
      setNewName("");
      setNewDescription("");
      setUploadFile(null);
      setIsCreateDialogOpen(false);

      toast({
        title: "Success",
        description: "Dataset created successfully",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof ApiError ? error.message : "Failed to create dataset",
        variant: "destructive",
      });
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Are you sure you want to delete this dataset?")) return;
    try {
      await api.delete(`/api/evaluation/datasets/${id}`);
      setDatasets(datasets.filter((d) => d.id !== id));
      toast({
        title: "Success",
        description: "Dataset deleted successfully",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to delete dataset",
        variant: "destructive",
      });
    }
  };

  const handlePreview = async (dataset: EvalDataset) => {
    try {
      const data = await api.get(`/api/evaluation/datasets/${dataset.id}`);
      setPreviewDataset(data.dataset || data);
      setPreviewSamples(data.samples || []);
      setIsPreviewOpen(true);
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to load dataset preview",
        variant: "destructive",
      });
    }
  };

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleDateString();
    } catch {
      return dateStr;
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold">Evaluation Datasets</h1>
            <p className="text-muted-foreground mt-1">
              Manage Q&A datasets for evaluating your RAG pipeline
            </p>
          </div>
          <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Create Dataset
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[500px]">
              <DialogHeader>
                <DialogTitle>Create New Dataset</DialogTitle>
                <DialogDescription>
                  Upload a JSONL file with Q&A pairs to create a new evaluation dataset.
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="grid gap-2">
                  <Label htmlFor="name">Dataset Name</Label>
                  <Input
                    id="name"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    placeholder="e.g. Financial Policy Q&A v1"
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="description">Description</Label>
                  <Input
                    id="description"
                    value={newDescription}
                    onChange={(e) => setNewDescription(e.target.value)}
                    placeholder="Brief description of the dataset"
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="file">Upload JSONL File</Label>
                  <div className="flex items-center gap-2">
                    <Input
                      id="file"
                      type="file"
                      accept=".jsonl,.json"
                      onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                    />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Each line should be a JSON object with: question, expected_answer, relevant_chunks, expected_facts
                  </p>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={handleCreate} disabled={isUploading || !newName.trim()}>
                  {isUploading ? "Creating..." : "Create"}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>

        {/* Datasets Table */}
        <Card>
          <CardHeader>
            <CardTitle>All Datasets</CardTitle>
            <CardDescription>
              {isLoading ? "Loading..." : `${datasets.length} datasets total`}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {datasets.length === 0 && !isLoading ? (
              <div className="text-center py-12 text-muted-foreground">
                <FileText className="mx-auto h-12 w-12 mb-4 opacity-50" />
                <p className="text-lg font-medium">No datasets yet</p>
                <p className="text-sm mt-1">
                  Create your first evaluation dataset to get started
                </p>
              </div>
            ) : (
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Description</TableHead>
                      <TableHead>Samples</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead className="w-[120px]">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {datasets.map((dataset) => (
                      <TableRow key={dataset.id}>
                        <TableCell className="font-medium">{dataset.name}</TableCell>
                        <TableCell className="text-muted-foreground max-w-[300px] truncate">
                          {dataset.description || "--"}
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary">{dataset.sample_count}</Badge>
                        </TableCell>
                        <TableCell>{formatDate(dataset.created_at)}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handlePreview(dataset)}
                              title="Preview"
                            >
                              <Eye className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleDelete(dataset.id)}
                              title="Delete"
                            >
                              <Trash2 className="h-4 w-4 text-destructive" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* JSONL Format Guide */}
        <Card>
          <CardHeader>
            <CardTitle>JSONL Format Reference</CardTitle>
            <CardDescription>
              Expected format for each line in the uploaded JSONL file
            </CardDescription>
          </CardHeader>
          <CardContent>
            <pre className="bg-muted p-4 rounded-lg text-sm overflow-x-auto">
{`{
  "case_id": "case_001",
  "question": "公司的年假有多少天？",
  "expected_answer": "符合条件的正式员工每年享有5天年假。",
  "relevant_chunks": [
    {"chunk_id": "doc_001_chunk_005", "relevance": 3},
    {"chunk_id": "doc_002_chunk_001", "relevance": 1}
  ],
  "expected_facts": [
    "年假天数为5天",
    "适用对象为符合条件的正式员工"
  ],
  "question_type": "factual",
  "difficulty": "easy",
  "is_answerable": true,
  "metadata": {}
}`}
            </pre>
            <div className="mt-4 space-y-2 text-sm text-muted-foreground">
              <p><strong>case_id</strong>: Unique identifier for the test case (required)</p>
              <p><strong>question</strong>: The question to ask the RAG system (required)</p>
              <p><strong>expected_answer</strong>: Ground truth answer for LLM-as-Judge evaluation (optional)</p>
              <p><strong>relevant_chunks</strong>: Annotated chunks that should be retrieved (optional, for retrieval metrics)</p>
              <p><strong>expected_facts</strong>: Key facts the answer should contain (optional)</p>
              <p><strong>question_type</strong>: factual / multi_doc / multi_hop / unanswerable / ambiguous / adversarial</p>
              <p><strong>difficulty</strong>: easy / medium / hard</p>
              <p><strong>is_answerable</strong>: Whether the question can be answered from the knowledge base</p>
            </div>
          </CardContent>
        </Card>

        {/* Preview Dialog */}
        <Dialog open={isPreviewOpen} onOpenChange={setIsPreviewOpen}>
          <DialogContent className="sm:max-w-[700px] max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Dataset Preview</DialogTitle>
              <DialogDescription>
                {previewDataset?.name} — {previewDataset?.sample_count} samples
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              {previewSamples.slice(0, 10).map((sample, idx) => (
                <Card key={sample.case_id || idx}>
                  <CardHeader className="py-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm">
                        #{idx + 1}: {sample.question?.slice(0, 80)}{sample.question?.length > 80 ? "..." : ""}
                      </CardTitle>
                      <div className="flex gap-2">
                        {sample.question_type && (
                          <Badge variant="outline">{sample.question_type}</Badge>
                        )}
                        {sample.difficulty && (
                          <Badge
                            variant={
                              sample.difficulty === "hard" ? "destructive" :
                              sample.difficulty === "medium" ? "secondary" : "outline"
                            }
                          >
                            {sample.difficulty}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="py-2 text-sm text-muted-foreground">
                    <p><strong>Expected:</strong> {sample.expected_answer?.slice(0, 200)}</p>
                    <p className="mt-1">
                      <strong>Relevant chunks:</strong>{" "}
                      {sample.relevant_chunks?.length || 0} annotated
                    </p>
                  </CardContent>
                </Card>
              ))}
              {previewSamples.length > 10 && (
                <p className="text-sm text-muted-foreground text-center">
                  ...and {previewSamples.length - 10} more samples
                </p>
              )}
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </DashboardLayout>
  );
}