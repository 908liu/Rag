"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useDropzone } from "react-dropzone";
import {
  Upload,
  X,
  FileText,
  CheckCircle,
  AlertCircle,
} from "lucide-react";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { api, ApiError } from "@/lib/api";
import { useToast } from "@/components/ui/use-toast";

interface FileStatus {
  file: File;
  status: "pending" | "uploading" | "completed" | "error";
  error?: string;
  documentId?: number;
}

export default function UploadPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const [files, setFiles] = useState<FileStatus[]>([]);
  const { toast } = useToast();

  const handleUpload = async (file: File) => {
    const formData = new FormData();
    formData.append("files", file);

    try {
      setFiles((prev) =>
        prev.map((f) =>
          f.file === file ? { ...f, status: "uploading" } : f
        )
      );

      const results = await api.post(
        `/api/knowledge-base/${params.id}/documents/upload`,
        formData
      );

      // 后端上传即处理，直接标记完成
      const result = Array.isArray(results) ? results[0] : results;
      setFiles((prev) =>
        prev.map((f) =>
          f.file.name === result?.file_name
            ? { ...f, status: "completed", documentId: result?.document_id }
            : f
        )
      );

      toast({
        title: "上传成功",
        description: `${file.name} 已上传并处理完成`,
      });
    } catch (error) {
      setFiles((prev) =>
        prev.map((f) =>
          f.file === file
            ? {
                ...f,
                status: "error",
                error: error instanceof ApiError ? error.message : "上传失败",
              }
            : f
        )
      );
      toast({
        title: "上传失败",
        description: error instanceof ApiError ? error.message : "上传失败",
        variant: "destructive",
      });
    }
  };

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles = acceptedFiles.map((file) => ({
      file,
      status: "pending" as const,
    }));
    setFiles((prev) => [...prev, ...newFiles]);

    // 直接上传每个文件（后端同步处理）
    newFiles.forEach(async (fileStatus) => {
      await handleUpload(fileStatus.file);
    });
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "text/plain": [".txt"],
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        [".docx"],
      "text/markdown": [".md"],
    },
  });

  const removeFile = (file: File) => {
    setFiles((prev) => prev.filter((f) => f.file !== file));
  };

  return (
    <DashboardLayout>
      <div className="max-w-4xl mx-auto space-y-8">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">
            上传文档
          </h2>
          <p className="text-muted-foreground">
            拖拽或点击上传文档，系统将自动切分并建立索引
          </p>
        </div>

        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors ${
            isDragActive
              ? "border-primary bg-primary/5"
              : "border-border hover:border-primary/50"
          }`}
        >
          <input {...getInputProps()} />
          <Upload className="mx-auto h-12 w-12 text-muted-foreground" />
          <p className="mt-4 text-sm text-muted-foreground">
            拖拽文件到这里，或点击选择文件
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            支持格式：PDF、DOCX、TXT、MD（最大 20MB）
          </p>
        </div>

        {files.length > 0 && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">文件列表</h3>
            <div className="space-y-2 max-h-[400px] overflow-y-auto rounded-lg">
              {files.map((fileStatus) => (
                <div
                  key={fileStatus.file.name}
                  className="flex items-center justify-between p-4 rounded-lg border bg-card"
                >
                  <div className="flex items-center space-x-4">
                    <FileText className="h-8 w-8 text-primary" />
                    <div>
                      <p className="font-medium">{fileStatus.file.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {(fileStatus.file.size / 1024).toFixed(1)} KB
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    {fileStatus.status === "uploading" && (
                      <span className="text-sm text-muted-foreground">
                        上传中...
                      </span>
                    )}
                    {fileStatus.status === "completed" && (
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    )}
                    {fileStatus.status === "error" && (
                      <div className="flex items-center space-x-2 text-red-500">
                        <AlertCircle className="h-5 w-5" />
                        <span className="text-sm">{fileStatus.error}</span>
                      </div>
                    )}
                    <button
                      onClick={() => removeFile(fileStatus.file)}
                      className="p-1 hover:bg-accent rounded-full"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="flex justify-end space-x-4">
          <button
            onClick={() => router.push("/dashboard/knowledge")}
            className="inline-flex items-center justify-center rounded-md text-sm font-medium border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2"
          >
            返回
          </button>
        </div>
      </div>
    </DashboardLayout>
  );
}
