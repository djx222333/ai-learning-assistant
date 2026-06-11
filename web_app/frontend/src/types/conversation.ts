// 对话历史类型定义
// 对应后端 GET /api/v1/conversations 响应

export interface ConversationItem {
  id: string;
  session_id: string;
  title: string;
  message_count: number;
  last_message?: string;
  created_at: string;
  updated_at: string;
}

export interface PaginatedConversations {
  total: number;
  offset: number;
  limit: number;
  items: ConversationItem[];
}

export interface ConversationMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  agent_type?: string;
  agent_name?: string;
  citations?: Array<{
    document_name: string;
    chunk_text: string;
    relevance_score: number;
  }>;
  created_at: string;
}

export interface PaginatedMessages {
  total: number;
  offset: number;
  limit: number;
  items: ConversationMessage[];
}