import http from "./http";
import type { ChatRequest, ChatResponse } from "../types/chat";

export async function sendMessage(req: ChatRequest): Promise<ChatResponse> {
  const resp = await http.post<ChatResponse>("/v1/chat", req);
  return resp.data;
}