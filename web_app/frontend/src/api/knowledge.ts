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

export async function getFiles(conversationId?: string): Promise<KnowledgeFile[]> {
  const params: Record<string, string> = {};
  if (conversationId) params.conversation_id = conversationId;
  const resp = await http.get("/v1/knowledge/files", { params });
  return resp.data;
}

export async function uploadFile(file: File, conversationId?: string): Promise<KnowledgeFile> {
  const form = new FormData();
  form.append("file", file);
  const params: Record<string, string> = {};
  if (conversationId) params.conversation_id = conversationId;
  const resp = await http.post("/v1/knowledge/upload", form, { params });
  return resp.data;
}

export async function deleteFile(id: string): Promise<void> {
  await http.delete(`/v1/knowledge/${id}`);
}
