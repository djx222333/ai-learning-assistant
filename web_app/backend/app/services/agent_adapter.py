# -*- coding: utf-8 -*-
"""适配层：桥接 web_app 与现有 supervisor_agent

设计原则：
1. 不修改 supervisor_agent 任何文件
2. 通过 sys.path 导入，而非复制代码
3. 在模块初始化时切换 CWD，确保 load_dotenv() 找到 .env
4. 提供 clean API：chat(message, session_id) -> {answer, agent_type, agent_name}
"""
import sys
import os
import importlib

# 计算 supervisor_agent 目录的绝对路径
# 当前文件: web_app/backend/app/services/agent_adapter.py
# supervisor_agent: E:\Exploit_1\supervisor_agent
ADAPTER_DIR = os.path.dirname(os.path.abspath(__file__))
SUPERVISOR_DIR = os.path.abspath(os.path.join(ADAPTER_DIR, "..", "..", "..", "..", "supervisor_agent"))

# 存入 sys.path（只在未加入时）
if SUPERVISOR_DIR not in sys.path:
    sys.path.insert(0, SUPERVISOR_DIR)

# 切换到 supervisor_agent 目录再导入，确保 load_dotenv() 找到 .env
_original_cwd = os.getcwd()
os.chdir(SUPERVISOR_DIR)

try:
    # 导入现有 agent_graph 模块
    # 这会在模块级别执行：
    #   load_dotenv()          - 读 .env
    #   DEEPSEEK_API_KEY = ..  - 读环境变量
    #   rag_engine = RAGEngine() - 加载 Embedding 模型
    #   graph = build_graph()   - 编译 LangGraph
    import agent_graph as _agent_graph

    # 导出核心对象，供 ChatService 使用
    graph = _agent_graph.graph
    HumanMessage = _agent_graph.HumanMessage
    MemorySaver = _agent_graph.MemorySaver

finally:
    # 恢复 CWD（避免影响后续文件操作）
    os.chdir(_original_cwd)


# Agent 类型 -> 显示名称映射
AGENT_DISPLAY_NAMES = {
    "code": "Code Agent",
    "english": "English Agent",
    "career": "Career Agent",
    "search": "Search Agent",
    "research": "Research Agent",
    "rag": "RAG Agent",
    "planner": "Planner",
}


def chat(message: str, session_id: str = None) -> dict:
    """适配器函数：调用现有 supervisor_agent 并返回结构化结果

    Args:
        message: 用户消息
        session_id: 会话 ID（用于 MemorySaver 区分会话）

    Returns:
        {
            "answer": "AI 的回答文本",
            "agent_type": "code",
            "agent_name": "Code Agent",
        }
    """
    # thread_id = session_id，相同 ID 共享对话历史
    thread_id = session_id or "default"
    config = {"configurable": {"thread_id": thread_id}}

    # 调用 LangGraph
    result = graph.invoke(
        {
            "messages": [HumanMessage(content=message)],
            "next_agent": "",
        },
        config,
    )

    # 从 state 提取结果
    answer = result["messages"][-1].content
    agent_type = result.get("next_agent", "")

    return {
        "answer": answer,
        "agent_type": agent_type,
        "agent_name": AGENT_DISPLAY_NAMES.get(agent_type, "Assistant"),
    }
