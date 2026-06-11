import type { ChatMessage } from "../../types/chat";
import AgentBadge from "./AgentBadge";

export default function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div className={`max-w-[75%] ${isUser ? "order-1" : "order-1"}`}>
        {/* Agent 标识 */}
        {!isUser && msg.agent_type && (
          <div className="mb-1">
            <AgentBadge agent_type={msg.agent_type} />
          </div>
        )}

        {/* 消息气泡 */}
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
            isUser
              ? "bg-blue-500 text-white rounded-br-md"
              : "bg-gray-100 text-gray-800 rounded-bl-md border border-gray-200"
          }`}
        >
          {msg.content}
        </div>

        {/* 引用来源 */}
        {!isUser && msg.citations && msg.citations.length > 0 && (
          <div className="mt-2 space-y-1">
            <p className="text-[10px] text-gray-400 font-medium">📖 引用来源</p>
            {msg.citations.map((c, i) => (
              <details key={i} className="text-xs">
                <summary className="text-gray-400 cursor-pointer hover:text-gray-600">
                  来源 {i + 1} · 相关性 {c.relevance_score}
                </summary>
                <p className="mt-1 text-gray-500 bg-gray-50 rounded p-2 border border-gray-100">
                  {c.chunk_text}
                </p>
              </details>
            ))}
          </div>
        )}

        {/* 时间戳 */}
        <div className={`text-[10px] text-gray-400 mt-1 ${isUser ? "text-right" : "text-left"}`}>
          {new Date(msg.created_at).toLocaleTimeString("zh-CN", {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </div>
      </div>
    </div>
  );
}
