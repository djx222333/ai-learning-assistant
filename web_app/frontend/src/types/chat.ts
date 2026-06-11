// 消息角色类型
export type MessageRole = "user" | "assistant";
export type AgentType = "code" | "english" | "career" | "search" | "research" | "rag" | "planner";

// 引用项
export interface Citation {
  document_name: string;
  chunk_text: string;
  relevance_score: number;
}

// 聊天消息
export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  agent_type?: AgentType;
  agent_name?: string;
  citations?: Citation[];
  created_at: string;
}

// 聊天请求
export interface ChatRequest {
  message: string;
  session_id?: string;
}

// 聊天响应
export interface ChatResponse {
  answer: string;
  agent_type: AgentType;
  agent_name: string;
  citations: Citation[];
}
