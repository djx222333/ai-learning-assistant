import { Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export default function Home() {
  const { isAuthenticated, user } = useAuth();

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center">
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">
          AI Learning Assistant
        </h1>
        <p className="text-lg text-gray-500">
          你的智能学习伙伴 · 基于 LangGraph Multi-Agent
        </p>
        {isAuthenticated && user && (
          <p className="text-sm text-blue-500 mt-2">
            欢迎回来，{user.username}
          </p>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-3xl w-full px-4">
        <div className="bg-white rounded-xl shadow-sm p-6 text-center hover:shadow-md transition-shadow">
          <div className="text-3xl mb-2">🤖</div>
          <h3 className="font-semibold text-gray-800">多 Agent 对话</h3>
          <p className="text-sm text-gray-500 mt-1">
            Code · English · Career · Search · Research
          </p>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-6 text-center hover:shadow-md transition-shadow">
          <div className="text-3xl mb-2">📄</div>
          <h3 className="font-semibold text-gray-800">知识库 RAG</h3>
          <p className="text-sm text-gray-500 mt-1">上传 PDF · 自动索引 · 文档问答</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-6 text-center hover:shadow-md transition-shadow">
          <div className="text-3xl mb-2">📋</div>
          <h3 className="font-semibold text-gray-800">学习规划</h3>
          <p className="text-sm text-gray-500 mt-1">Planner 拆解目标 · 阶段计划 · 进度追踪</p>
        </div>
      </div>

      <div className="mt-8 flex gap-3">
        {isAuthenticated ? (
          <>
            <Link
              to="/chat"
              className="px-6 py-3 bg-blue-500 text-white rounded-xl font-medium hover:bg-blue-600 transition-colors"
            >
              开始学习 →
            </Link>
            <Link
              to="/knowledge"
              className="px-6 py-3 bg-gray-200 text-gray-700 rounded-xl font-medium hover:bg-gray-300 transition-colors"
            >
              知识库
            </Link>
          </>
        ) : (
          <>
            <Link
              to="/login"
              className="px-6 py-3 bg-blue-500 text-white rounded-xl font-medium hover:bg-blue-600 transition-colors"
            >
              登录
            </Link>
            <Link
              to="/register"
              className="px-6 py-3 bg-gray-200 text-gray-700 rounded-xl font-medium hover:bg-gray-300 transition-colors"
            >
              注册
            </Link>
          </>
        )}
      </div>

      <p className="mt-12 text-xs text-gray-300">
        Powered by LangGraph + FastAPI + React + Tailwind
      </p>
    </div>
  );
}