export type MessageRole = "user" | "assistant";
export type AgentType = "code" | "english" | "career" | "search" | "research" | "rag" | "planner";

export interface Citation {
  document_name: string;
  chunk_text: string;
  relevance_score: number;
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  agent_type?: AgentType;
  agent_name?: string;
  citations?: Citation[];
  created_at: string;
}

export interface ChatRequest {
  message: string;
  session_id?: string;
  conversation_id?: string;
}

export interface ChatResponse {
  answer: string;
  agent_type: AgentType;
  agent_name: string;
  citations: Citation[];
}
