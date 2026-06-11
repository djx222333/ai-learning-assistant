import http from "./http";
import type {
  PaginatedConversations,
  PaginatedMessages,
} from "../types/conversation";

export async function listConversations(
  offset: number = 0,
  limit: number = 20
): Promise<PaginatedConversations> {
  const resp = await http.get<PaginatedConversations>("/v1/conversations", {
    params: { offset, limit },
  });
  return resp.data;
}

export async function getConversationMessages(
  conversationId: string,
  offset: number = 0,
  limit: number = 50
): Promise<PaginatedMessages> {
  const resp = await http.get<PaginatedMessages>(
    `/v1/conversations/${conversationId}/messages`,
    { params: { offset, limit } }
  );
  return resp.data;
}

export async function deleteConversation(
  conversationId: string
): Promise<void> {
  await http.delete(`/v1/conversations/${conversationId}`);
}