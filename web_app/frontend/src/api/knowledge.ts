import http from "./http";

export interface KnowledgeFile {
  id: string;
  filename: string;
  file_size: number;
  index_status: "processing" | "ready" | "failed";
  chunk_count: number;
  page_count: number;
  created_at: string;
}

export async function getFiles(): Promise<KnowledgeFile[]> {
  const resp = await http.get("/v1/knowledge/files");
  return resp.data;
}

export async function uploadFile(file: File): Promise<KnowledgeFile> {
  const form = new FormData();
  form.append("file", file);
  const resp = await http.post("/v1/knowledge/upload", form);
  return resp.data;
}

export async function deleteFile(id: string): Promise<void> {
  await http.delete(`/v1/knowledge/${id}`);
}