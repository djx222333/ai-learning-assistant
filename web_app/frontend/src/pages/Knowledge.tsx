import { useAuth } from "../contexts/AuthContext";
import { useState, useEffect, useCallback } from "react";
import { getFiles, uploadFile, deleteFile, type KnowledgeFile } from "../api/knowledge";

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

export default function Knowledge() {
  const { logout } = useAuth();
  const [files, setFiles] = useState<KnowledgeFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);

  const loadFiles = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getFiles();
      setFiles(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadFiles(); }, [loadFiles]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      alert("Only PDF files are supported");
      return;
    }
    setUploading(true);
    try {
      await uploadFile(file);
      await loadFiles();
    } catch (err: any) {
      alert("Upload failed: " + (err?.response?.data?.detail || err?.message));
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm("Delete " + name + "?")) return;
    try {
      await deleteFile(id);
      await loadFiles();
    } catch (err: any) {
      alert("Delete failed: " + (err?.response?.data?.detail || err?.message));
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b border-gray-200 bg-white px-4 py-3">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xl">DOC</span>
            <h1 className="font-semibold text-gray-800">Knowledge Base</h1>
          </div>
          <div className="flex items-center gap-2">
            <a href="/chat" className="text-sm text-blue-500 hover:underline">Back to Chat</a>
            <button
              onClick={() => { logout(); window.location.href = "/login"; }}
              className="text-xs text-gray-400 hover:text-red-500 transition-colors px-2 py-1"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 py-6">
        <div className="bg-white rounded-xl border-2 border-dashed border-gray-300 p-8 text-center hover:border-blue-400 transition-colors">
          <label className="cursor-pointer block">
            <div className="text-4xl mb-2">UPLOAD</div>
            <p className="text-sm text-gray-600 mb-1">
              {uploading ? "Uploading and indexing..." : "Drag PDF here, or click to select"}
            </p>
            <p className="text-xs text-gray-400">PDF only, max 50MB</p>
            <input
              type="file"
              accept=".pdf"
              onChange={handleUpload}
              disabled={uploading}
              className="hidden"
            />
          </label>
        </div>

        <div className="mt-6">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
            Uploaded Documents {files.length > 0 && (" (" + files.length + ")")}
          </h2>

          {loading ? (
            <div className="text-center py-8 text-sm text-gray-400">Loading...</div>
          ) : files.length === 0 ? (
            <div className="text-center py-8 text-sm text-gray-400">No documents yet. Upload a PDF to start.</div>
          ) : (
            <div className="space-y-2">
              {files.map((f) => {
                const st = formatStatus(f.index_status);
                return (
                  <div key={f.id} className="flex items-center justify-between bg-white rounded-lg px-4 py-3 border border-gray-200">
                    <div className="flex items-center gap-3 min-w-0">
                      <span className="text-xl flex-shrink-0">FILE</span>
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-gray-800 truncate">{f.filename}</p>
                        <p className="text-xs text-gray-400">
                          {formatSize(f.file_size)} - {f.page_count} pages - {f.chunk_count} chunks
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <span className={"text-xs px-2 py-0.5 rounded-full " + st.color}>
                        {st.label}
                      </span>
                      <button onClick={() => handleDelete(f.id, f.filename)}
                        className="text-xs text-gray-400 hover:text-red-500 transition-colors px-2 py-1">
                        Delete
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}