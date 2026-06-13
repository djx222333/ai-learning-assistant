import { useState, useRef, useEffect, useCallback } from "react";
import type { ChatMessage } from "../types/chat";
import type { ConversationMessage } from "../types/conversation";
import { sendMessage } from "../api/chat";
import { getConversationMessages } from "../api/conversations";
import InputBox from "../components/chat/InputBox";
import { useAuth } from "../contexts/AuthContext";
import HistorySidebar from "../components/chat/HistorySidebar";
import MessageBubble from "../components/chat/MessageBubble";

const SESSION_KEY = "ai_larning_session_id";

function getOrCreateSessionId(): string {
  const existing = localStorage.getItem(SESSION_KEY);
  if (existing) return existing;
  const newId = "session-" + Date.now().toString(36);
  localStorage.setItem(SESSION_KEY, newId);
  return newId;
}

function resetSession(): string {
  const newId = "session-" + Date.now().toString(36);
  localStorage.setItem(SESSION_KEY, newId);
  return newId;
}

function toChatMessage(m: ConversationMessage): ChatMessage {
  return {
    id: m.id,
    role: m.role,
    content: m.content,
    agent_type: m.agent_type as any,
    agent_name: m.agent_name,
    citations: m.citations,
    created_at: m.created_at,
  };
}

export default function Chat() {
  const { user, logout } = useAuth();
  const [sessionId, setSessionId] = useState(getOrCreateSessionId);
  const [convId, setConvId] = useState<string | undefined>(undefined);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [knowledgeRefresh, setKnowledgeRefresh] = useState(0);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSelectSession = useCallback(
    async (sid: string, convId: string) => {
      if (sid === sessionId) return;
      setHistoryLoading(true);
      setSessionId(sid);
      setConvId(convId);
      localStorage.setItem(SESSION_KEY, sid);
      try {
        const data = await getConversationMessages(convId, 0, 100);
        const mapped = data.items.map(toChatMessage);
        setMessages(mapped);
      } catch {
        setMessages([]);
      } finally {
        setHistoryLoading(false);
      }
    },
    [sessionId]
  );

  const handleNewSession = useCallback(() => {
    const newId = resetSession();
    setSessionId(newId);
    setMessages([]);
    setRefreshTrigger((n) => n + 1);
  }, []);

  const handleLogout = () => {
  logout();
  window.location.href = "/login";
};

const handleSend = useCallback(
    async (text: string) => {
      const tempId = "u-" + Date.now().toString(36);
      const userMsg: ChatMessage = {
        id: tempId,
        role: "user",
        content: text,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setLoading(true);

      try {
        const resp = await sendMessage({ message: text, session_id: sessionId, conversation_id: convId });
        const aiMsg: ChatMessage = {
          id: "a-" + Date.now().toString(36),
          role: "assistant",
          content: resp.answer,
          agent_type: resp.agent_type,
          agent_name: resp.agent_name,
          citations: resp.citations ?? [],
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, aiMsg]);
        setRefreshTrigger((n) => n + 1);
      } catch (err: any) {
        const errMsg: ChatMessage = {
          id: "e-" + Date.now().toString(36),
          role: "assistant",
          content:
            "抱歉，发生了错误：" +
            (err?.response?.data?.detail || err?.message || "请求失败，请重试"),
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, errMsg]);
      } finally {
        setLoading(false);
      }
    },
    [sessionId]
  );

  return (
    <div className="h-screen flex bg-gray-50">
      <HistorySidebar
        currentSessionId={sessionId}
        currentConvId={convId}
        onSelectSession={handleSelectSession}
        onNewSession={handleNewSession}
        refreshTrigger={refreshTrigger}
        knowledgeRefreshTrigger={knowledgeRefresh}
      />

      <div className="flex-1 flex flex-col min-w-0">
        <header className="flex-shrink-0 border-b border-gray-200 bg-white px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 ml-8 md:ml-0">
              <span className="text-xl">🎓</span>
              <h1 className="font-semibold text-gray-800">AI Learning Assistant</h1>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={handleNewSession}
                className="text-xs px-3 py-1.5 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-600 transition-colors"
              >
                + 新会话
              </button>
              <button
                onClick={handleLogout}
                className="text-xs px-2.5 py-1.5 rounded-lg text-gray-400 hover:text-red-500 transition-colors"
                title={user?.username}
              >
                退出
              </button>
            </div>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto px-4 py-6">
          <div className="max-w-4xl mx-auto">
            {historyLoading ? (
              <div className="flex items-center justify-center h-full min-h-[400px]">
                <div className="flex flex-col items-center gap-2">
                  <div className="flex gap-1">
                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                  <span className="text-sm text-gray-400">加载历史消息...</span>
                </div>
              </div>
            ) : messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full min-h-[400px] text-center">
                <span className="text-5xl mb-4">🎓</span>
                <h2 className="text-xl font-semibold text-gray-700 mb-2">欢迎来到 AI Learning Assistant</h2>
                <p className="text-sm text-gray-400 max-w-md mb-6">我可以帮你学习编程、英语、制定学习计划、搜索资料、研究课题。<br />试试在下方输入你的问题。</p>
                <div className="flex flex-wrap gap-2 justify-center">
                  {["Python 列表是什么？", "帮我制定学习计划", "最新的 Python 版本"].map((q) => (
                    <button
                      key={q}
                      onClick={() => handleSend(q)}
                      className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded-full text-gray-600 transition-colors"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <>
                {messages.map((msg) => <MessageBubble key={msg.id} msg={msg} />)}
                {loading && (
                  <div className="flex items-center gap-2 text-sm text-gray-400 mb-4">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                    </div>
                    <span>AI 思考中...</span>
                  </div>
                )}
                <div ref={bottomRef} />
              </>
            )}

          </div>
        </div>

        <InputBox
          onSend={handleSend}
          disabled={loading || historyLoading}
          conversationId={convId}
          onUploadStart={() => {}}
          onUploadEnd={() => setKnowledgeRefresh((n) => n + 1)}
        />
      </div>
    </div>
  );
}