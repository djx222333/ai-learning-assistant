// ChatKnowledgePanel — 集成在 Chat 侧边栏的小型知识库面板
// 显示当前会话的已上传文档列表 + 上传入口

import { useState, useEffect, useCallback } from "react";
import { getFiles, uploadFile, deleteFile, type KnowledgeFile } from "../../api/knowledge";

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

function formatStatus(status: string): { label: string; color: string } {
  switch (status) {
    case "ready":
      return { label: "ready", color: "bg-green-100 text-green-700" };
    case "processing":
      return { label: "processing", color: "bg-yellow-100 text-yellow-700" };
    case "failed":
      return { label: "failed", color: "bg-red-100 text-red-700" };
    default:
      return { label: status, color: "bg-gray-100 text-gray-700" };
  }
}

interface Props {
  /** 外部触发刷新（上传完成后） */
  refreshTrigger: number;
  /** 当前会话 ID（用于隔离文档） */
  conversationId?: string;
}

export default function ChatKnowledgePanel({ refreshTrigger, conversationId }: Props) {
  const [files, setFiles] = useState<KnowledgeFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const loadFiles = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getFiles(conversationId);
      setFiles(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [conversationId]);

  useEffect(() => {
    let cancelled = false;
    loadFiles().then(() => {
      if (cancelled) return;
    });
    return () => { cancelled = true; };
  }, [loadFiles, refreshTrigger]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      alert("仅支持 PDF 文件");
      return;
    }
    setUploading(true);
    try {
      await uploadFile(file, conversationId);
      await loadFiles();
      setExpanded(true);
    } catch (err: any) {
      alert("上传失败: " + (err?.response?.data?.detail || err?.message));
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteFile(id);
      await loadFiles();
    } catch {
      // ignore
    }
  };

  const readyCount = files.filter((f) => f.index_status === "ready").length;

  return (
    <div className="border-t border-gray-200">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-3 py-2 text-xs text-gray-500 hover:bg-gray-50 transition-colors"
      >
        <span className="font-medium">
          📚 知识库 {files.length > 0 && `(${readyCount}/${files.length})`}
        </span>
        <span className="text-gray-300">{expanded ? "▼" : "▶"}</span>
      </button>

      {expanded && (
        <div className="px-2 pb-2">
          {/* Upload area */}
          <label className="block cursor-pointer">
            <div className="border-2 border-dashed border-gray-200 rounded-lg py-3 text-center hover:border-blue-300 hover:bg-blue-50/30 transition-colors">
              {uploading ? (
                <div className="flex items-center justify-center gap-1 text-xs text-gray-400">
                  <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  正在上传...
                </div>
              ) : (
                <div className="text-xs text-gray-400">
                  <span className="text-sm mr-1">📎</span>
                  点击上传 PDF
                </div>
              )}
              <input
                type="file"
                accept=".pdf"
                onChange={handleUpload}
                disabled={uploading}
                className="hidden"
              />
            </div>
          </label>

          {/* File list */}
          {loading ? (
            <div className="text-center py-3 text-xs text-gray-400">加载中...</div>
          ) : files.length === 0 ? (
            <div className="text-center py-3 text-xs text-gray-300">暂无文档</div>
          ) : (
            <div className="mt-1 space-y-1 max-h-48 overflow-y-auto">
              {files.map((f) => {
                const st = formatStatus(f.index_status);
                return (
                  <div key={f.id} className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-gray-50 group transition-colors">
                    <span className="text-xs flex-shrink-0">📄</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-gray-700 truncate">{f.filename}</p>
                      <p className="text-[10px] text-gray-400">{formatSize(f.file_size)}</p>
                    </div>
                    <span className={"text-[10px] px-1.5 py-0.5 rounded-full flex-shrink-0 " + st.color}>
                      {st.label}
                    </span>
                    <button
                      onClick={() => handleDelete(f.id)}
                      className="flex-shrink-0 text-gray-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all text-xs"
                    >
                      ✕
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}


