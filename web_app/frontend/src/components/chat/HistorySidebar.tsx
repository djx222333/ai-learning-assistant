// HistorySidebar 组件
// 对话历史侧边栏：列表 / 切换 / 删除 / 新建

import { useState, useEffect, useCallback } from "react";
import type { ConversationItem } from "../../types/conversation";
import {
  listConversations,
  deleteConversation,
} from "../../api/conversations";
import ChatKnowledgePanel from "./ChatKnowledgePanel";

interface HistorySidebarProps {
  /** 当前会话 ID（用于高亮） */
  currentSessionId: string;
  /** 当前 conversation ID */
  currentConvId?: string;
  /** 切换到指定会话 */
  onSelectSession: (sessionId: string, convId: string) => void;
  /** 新建会话 */
  onNewSession: () => void;
  /** 刷新会话列表的外部触发器 */
  refreshTrigger: number;
  /** 知识库外部刷新触发器 */
  knowledgeRefreshTrigger?: number;
}

// 格式化时间：今天显示 HH:MM，昨天显示"昨天"，更早显示 MM-DD
function formatTime(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    const day = 24 * 60 * 60 * 1000;
    if (diff < day) return d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
    if (diff < 2 * day) return "昨天";
    if (diff < 7 * day) return `${Math.floor(diff / day)}天前`;
    return `${d.getMonth() + 1}-${d.getDate()}`;
  } catch {
    return "";
  }
}

// 简化标题：取第一条消息的前 20 字
function simplifyTitle(item: ConversationItem): string {
  if (item.title && item.title !== "新对话") return item.title;
  if (item.last_message) return item.last_message.slice(0, 20) + (item.last_message.length > 20 ? "..." : "");
  return "新对话";
}

export default function HistorySidebar({
  currentSessionId,
  currentConvId,
  onSelectSession,
  onNewSession,
  refreshTrigger,
}: HistorySidebarProps) {
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // 加载会话列表
  const loadConversations = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await listConversations(0, 50);
      setConversations(data.items);
    } catch (err: any) {
      if (err?.response?.status === 401) {
        setError("请先登录");
      } else {
        setError("加载失败");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  // 首次加载 + 外部刷新
  useEffect(() => {
    loadConversations();
  }, [loadConversations, refreshTrigger]);

  // 删除会话
  const handleDelete = async (e: React.MouseEvent, convId: string) => {
    e.stopPropagation();
    if (deletingId) return;
    setDeletingId(convId);
    try {
      await deleteConversation(convId);
      await loadConversations();
    } catch {
      // ignore
    } finally {
      setDeletingId(null);
    }
  };

  // 切换侧边栏（移动端）
  const toggleSidebar = () => setSidebarOpen(!sidebarOpen);

  // 选择会话
  const handleSelect = (conv: ConversationItem) => {
    onSelectSession(conv.session_id, conv.id);
    setSidebarOpen(false); // 移动端自动收起
  };

  // 新建会话
  const handleNew = () => {
    onNewSession();
    setSidebarOpen(false);
  };

  return (
    <>
      {/* 移动端 Toggle 按钮 */}
      <button
        onClick={toggleSidebar}
        className="fixed top-3 left-3 z-50 md:hidden p-2 rounded-lg bg-white/90 border border-gray-200 shadow-sm hover:bg-gray-100 transition-colors"
        title="历史记录"
      >
        <span className="text-lg">{sidebarOpen ? "✕" : "☰"}</span>
      </button>

      {/* 遮罩层（移动端） */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/20 z-30 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* 侧边栏 */}
      <aside
        className={`
          fixed md:static inset-y-0 left-0 z-40
          w-72 bg-white border-r border-gray-200
          flex flex-col transition-transform duration-200
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}
        `}
      >
        {/* 顶部：标题 + 新建 */}
        <div className="flex-shrink-0 p-3 border-b border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
              历史对话
            </h2>
            <button
              onClick={handleNew}
              className="text-xs px-2.5 py-1 rounded-lg bg-blue-50 text-blue-600 hover:bg-blue-100 transition-colors"
            >
              ＋ 新建
            </button>
          </div>
        </div>

        {/* 状态区域 */}
        {loading && (
          <div className="flex-1 flex items-center justify-center">
            <div className="flex flex-col items-center gap-2">
              <div className="flex gap-1">
                <span className="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
              <span className="text-xs text-gray-400">加载中...</span>
            </div>
          </div>
        )}

        {error && !loading && (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center px-4">
              <p className="text-sm text-gray-400 mb-2">{error}</p>
              <button
                onClick={loadConversations}
                className="text-xs text-blue-500 hover:underline"
              >
                重试
              </button>
            </div>
          </div>
        )}

        {!loading && !error && conversations.length === 0 && (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center px-4">
              <p className="text-2xl mb-2">💬</p>
              <p className="text-sm text-gray-400">还没有对话记录</p>
              <p className="text-xs text-gray-300 mt-1">开始聊天吧</p>
            </div>
          </div>
        )}

        {/* 会话列表 */}
        {!loading && !error && conversations.length > 0 && (
          <div className="flex-1 overflow-y-auto">
            {conversations.map((conv) => {
              const isActive = conv.session_id === currentSessionId;
              return (
                <div
                  key={conv.id}
                  onClick={() => handleSelect(conv)}
                  className={`
                    group flex items-start gap-2 px-3 py-2.5 cursor-pointer border-b border-gray-50
                    transition-colors relative
                    ${isActive
                      ? "bg-blue-50 border-l-2 border-l-blue-500"
                      : "hover:bg-gray-50 border-l-2 border-l-transparent"
                    }
                  `}
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-800 truncate">
                      {simplifyTitle(conv)}
                    </p>
                    <p className="text-xs text-gray-400 truncate mt-0.5">
                      {conv.last_message?.slice(0, 60) || `${conv.message_count} 条消息`}
                    </p>
                    <p className="text-[10px] text-gray-300 mt-0.5">
                      {formatTime(conv.updated_at)}
                    </p>
                  </div>
                  <button
                    onClick={(e) => handleDelete(e, conv.id)}
                    disabled={deletingId === conv.id}
                    className={`
                      flex-shrink-0 p-1 rounded
                      opacity-0 group-hover:opacity-100 transition-opacity
                      ${deletingId === conv.id ? "opacity-50" : ""}
                      hover:bg-red-50 text-gray-400 hover:text-red-500
                    `}
                    title="删除"
                  >
                    {deletingId === conv.id ? (
                      <span className="text-xs animate-pulse">...</span>
                    ) : (
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    )}
                  </button>
                </div>
              );
            })}
          </div>
        )}
        <ChatKnowledgePanel refreshTrigger={0} conversationId={currentConvId} />
      </aside>
    </>
  );
}