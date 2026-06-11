# -*- coding: utf-8 -*-
"""agent_graph.py - Supervisor + Multi-Agent Architecture"""

from typing import Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition, create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from ddgs import DDGS
from rag_engine import RAGEngine
from dotenv import load_dotenv
import os

load_dotenv()


# ============================================================
# Part 1: State
#
# SupervisorState 扩展 MessagesState，除了 messages 字段外
# 还多了一个 next_agent 字段，用来记录 Supervisor 决定
# 下一步要调用哪个子 Agent
# ============================================================


class SupervisorState(MessagesState):
    """Supervisor 状态
    messages:   对话历史（所有子 Agent 共享）
    next_agent: Supervisor 决定的下一个 Agent 名字
    """
    next_agent: str


# ============================================================
# Part 2: Tools
#
# 这些工具可以被子 Agent 调用
# Code Agent 能调 calculator + read_file
# English/Career Agent 只能调 read_file
# ============================================================


@tool
def calculator(a: float, b: float, operator: str) -> str:
    """Perform arithmetic.
    Args:
        a: first number
        b: second number
        operator: add, subtract, multiply, divide
    """
    ops = {"add": a+b, "subtract": a-b, "multiply": a*b, "divide": a/b if b!=0 else "err"}
    return str(ops.get(operator, f"unknown: {operator}"))


@tool
def read_file(file_path: str) -> str:
    """Read a local file.
    Args:
        file_path: path to file
    """
    if not os.path.exists(file_path):
        return f"File not found: {file_path}"
    with open(file_path, "r", encoding="utf-8") as f:
        c = f.read()
    return c[:2000] + ("... (truncated)" if len(c) > 2000 else "")



# ---------- Web Search Tool ----------


@tool
def web_search(query: str) -> str:
    """Search the internet for current information.
    Use this for real-time data or recent events.
    
    Args:
        query: search keywords
    """
    try:
        ddgs = DDGS()
        results = list(ddgs.text(query, max_results=3))
        if not results:
            return "No search results found."
        lines = []
        for i, r in enumerate(results, 1):
            lines.append('Result {}: {}'.format(i, r['title']))
            lines.append('URL: {}'.format(r['href']))
            lines.append('Summary: {}'.format(r['body']))
            lines.append("")
        return '\n'.join(lines)
    except Exception as e:
        return 'Search error: {}'.format(e)



# ---------- Long-Term Memory Tools ----------
# 这两个工具让 Agent 能读写 user_profile.json
# 实现跨会话的用户画像持久化

# read_profile: Agent 用来读取用户背景信息
# update_profile: Agent 在了解到新信息时用来更新


@tool
def read_profile(field: str = "all") -> str:
    """Read user profile from long-term memory.
    Use this to personalize responses based on user background.
    
    Args:
        field: which field to read, or "all" for everything
    """
    import json
    try:
        with open("user_profile.json", "r", encoding="utf-8") as f:
            p = json.load(f)
        if field == "all":
            return json.dumps(p, ensure_ascii=False, indent=2)
        return json.dumps({field: p.get(field, "not set")}, ensure_ascii=False)
    except Exception as e:
        return f"Error reading profile: {e}"


@tool
def update_profile(key: str, value: str) -> str:
    """Update user profile in long-term memory.
    Call this when the user shares personal information
    like their background, skill level, or goals.
    
    Args:
        key: field name (background, skill_level, learning_goal, etc.)
        value: new value
    """
    import json
    from datetime import date
    try:
        with open("user_profile.json", "r", encoding="utf-8") as f:
            p = json.load(f)
        p[key] = value
        p["last_active"] = str(date.today())
        p["conversation_count"] = p.get("conversation_count", 0) + 1
        with open("user_profile.json", "w", encoding="utf-8") as f:
            json.dump(p, f, ensure_ascii=False, indent=2)
        return f"Profile updated: {key} = {value}"
    except Exception as e:
        return f"Error updating profile: {e}"

# ============================================================
# RAG Engine (global instance, loaded once)
rag_engine = RAGEngine()


@tool
def ingest_pdf(file_path: str) -> str:
    """Upload and index a PDF file.
    Use this when the user wants to ask questions about a document.
    Args:
        file_path: path to the PDF file
    """
    return rag_engine.ingest_pdf(file_path)


@tool
def rag_search(query: str, top_k: int = 3) -> str:
    """Search indexed documents and return relevant passages.
    Use this after ingest_pdf to answer questions about the document.
    Args:
        query: what to search for
        top_k: number of passages to return
    """
    results = rag_engine.search(query, top_k)
    return "\n---\n".join(results)


# ============================================================
# Part 3: LLM Helper
# ============================================================


DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")


def get_llm(model="deepseek-v4-flash"):
    if not DEEPSEEK_API_KEY or "xxx" in DEEPSEEK_API_KEY:
        raise ValueError("Invalid API key")
    return ChatOpenAI(model=model, api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com/v1", temperature=0.7)


# 到这步先停，下一步创建 3 个子 Agent

# ============================================================
# Part 4: Create 3 Sub-Agents
#
# create_react_agent creates a complete agent graph in one call.
# Internally it builds: START -> agent -> (tools?) -> agent -> END
#
# Each sub-agent is a compiled sub-graph.
# In the supervisor graph, they act as single nodes.
# ============================================================

# ---------- Code Agent ----------
code_prompt = SystemMessage(content="You are a Python tutor. Use read_profile to learn the user skill level before teaching. Use calculator for math. Use read_file for code files. Use update_profile to track progress.")
code_agent = create_react_agent(
    model=get_llm().bind_tools([calculator, read_file, read_profile, update_profile]),
    tools=[calculator, read_file, read_profile, update_profile],
    prompt=code_prompt,
)

# ---------- English Agent ----------
english_prompt = SystemMessage(content="You are an English teacher. Provide grammar explanations and examples.")
english_agent = create_react_agent(
    model=get_llm().bind_tools([read_file]),
    tools=[read_file],
    prompt=english_prompt,
)

# ---------- Career Agent ----------
career_prompt = SystemMessage(content="You are a study planning consultant. Before making a plan, use read_profile to learn about the user background. After the user shares personal info, use update_profile to save it. Provide plans with timelines.")
career_agent = create_react_agent(
    model=get_llm().bind_tools([read_file, read_profile, update_profile]),
    tools=[read_file, read_profile, update_profile],
    prompt=career_prompt,
)

# ---------- Search Agent ----------
# 职责：联网搜索实时信息
# 工具：web_search
#
# 为什么 Search Agent 要用 create_react_agent 而不是普通函数？
#   搜索不是调一次函数就结束的事情。
#   可能第一次搜的结果不够精确，需要调整关键词再搜。
#   create_react_agent 提供了 agent → tools → agent 的循环能力。

search_prompt = SystemMessage(content="You are a search specialist. Use web_search to find current information. If results are not clear, try different keywords.")
search_agent = create_react_agent(
    model=get_llm().bind_tools([web_search]),
    tools=[web_search],
    prompt=search_prompt,
)

# ---------- Research Agent ----------
# 职责：搜集资料 + 整理资料 + 输出结构化报告
# 工具：web_search（搜索各种来源）+ read_file（读本地参考文件）
#
# 与 Search Agent 的区别：
#   Search: 搜一次 → 直接回答
#   Research: 多次搜索 → 交叉验证 → 读文件 → 输出报告

research_prompt = SystemMessage(content="You are a research analyst. Use web_search to gather information from multiple sources, and read_file to examine local reference materials. Organize your findings into a structured report with sections, key findings, and source citations. If initial search results are insufficient, try different search keywords to get comprehensive coverage.")
research_agent = create_react_agent(
    model=get_llm().bind_tools([web_search, read_file]),
    tools=[web_search, read_file],
    prompt=research_prompt,
)


# ---------- RAG Agent ----------
# 职责：文档问答（上传 PDF → 检索 → 回答）
# 工具：ingest_pdf（上传建索引）+ rag_search（检索问答）
#
# 与 Search Agent 的区别：
#   Search: 搜互联网
#   RAG: 搜你自己上传的文档
#
# 与 Research Agent 的区别：
#   Research: 多来源调研，输出报告
#   RAG: 基于特定文档的精准问答
rag_prompt = SystemMessage(content="You are a document Q&A assistant. When the user provides a PDF file, use ingest_pdf to index it. When they ask questions, use rag_search to find relevant passages and answer based on the document. Always cite the source chunks.")
rag_agent = create_react_agent(
    model=get_llm().bind_tools([ingest_pdf, rag_search]),
    tools=[ingest_pdf, rag_search],
    prompt=rag_prompt,
)

# ============================================================
# Part 5: Supervisor Node
# Supervisor classifies the question and returns next_agent
# ============================================================


def supervisor_node(state: SupervisorState) -> dict:
    last = state["messages"][-1]
    question = last.content
    llm = get_llm()
    prompt = (
        "Classify into ONE category. Reply ONLY the word.\n"
        "- code: Python programming\n"
        "- english: English learning\n"
        "- career: Study planning\n"
        "- search: Quick internet search for current/recent info\n"
        "- research: In-depth research, multi-source investigation, report writing\n\n"
        "-rag: Document Q&A, PDF analysis\n\n"
        "-planner: Complex tasks, multi-step, breakdown\n\n"
        f"Question: {question}"
    )
    resp = llm.invoke(prompt)
    cat = resp.content.strip().lower()
    if cat not in ("code", "english", "career", "search", "research", "rag", "planner"):
        cat = "code"
    return {"next_agent": cat}


# ============================================================
# Part 5b: Planner Node
#
# Planner 接收复杂问题，拆成多个子任务，依次调用不同的 Agent，
# 收集结果并汇总成最终回答。
#
# 为什么 Planner 是普通函数而不是 create_react_agent？
#   Planner 需要遍历任务列表、依次调子 Agent、汇总结果——
#   这些是编排逻辑，不是 ReAct 循环。普通函数更适合。
# ============================================================


AGENT_MAP_PLAN = {
    "code": code_agent,
    "english": english_agent,
    "career": career_agent,
    "search": search_agent,
    "research": research_agent,
    "rag": rag_agent,
}


def planner_node(state: SupervisorState) -> dict:
    """Planner: receive complex question, split tasks, collect results"""
    import json
    from langchain_core.messages import HumanMessage, AIMessage

    question = state["messages"][-1].content
    llm = get_llm()

    # Step 1: LLM 拆解任务
    prompt = f"""Break this request into subtasks.
    Each subtask is assigned to ONE agent:
    - code: Python programming
    - english: English learning
    - career: Study planning
    - search: Internet search
    - research: Multi-source research
    - rag: Document Q&A

    Output ONLY a JSON array:
    [{{"agent": "code", "task": "description"}}]

    Request: {question}"""

    resp = llm.invoke(prompt)

    # Step 2: 解析任务列表
    text = resp.content.strip()
    # Remove markdown code fences if present
    if "`" in text:
        text = text.split("`")[1]
        if text.startswith("json"):
            text = text[4:]
    tasks = json.loads(text)
    if not isinstance(tasks, list):
        tasks = [tasks]
    # Limit to 4 tasks max
    tasks = tasks[:4]


    # Step 3: 依次执行每个子任务
    results = []
    for t in tasks:
        agent_name = t.get("agent", "code")
        task_desc = t.get("task", question)
        agent = AGENT_MAP_PLAN.get(agent_name)
        if agent is None:
            continue
        try:
            r = agent.invoke({"messages": [HumanMessage(content=task_desc)]})
            answer = r["messages"][-1].content
            results.append(f"[{agent_name.upper()}] {task_desc}\n{answer}")
        except Exception as e:
            results.append(f"[{agent_name.upper()}] Error: {e}")

    # Step 4: 汇总结果
    all_results = "\n\n---\n\n".join(results)
    final_prompt = f"""Consolidate these results into a coherent response.
    Original question: {question}

    Results:
    {all_results}

    Write a final response that integrates all information smoothly."""
    final_resp = llm.invoke(final_prompt)
    return {"messages": [AIMessage(content=final_resp.content)]}


# ============================================================
# Part 6: Routing
# Conditional Edge reads next_agent and routes to sub-agent
# ============================================================


AGENT_MAP = {"code": "code_agent", "english": "english_agent", "career": "career_agent", "search": "search_agent", "research": "research_agent", "rag": "rag_agent", "planner": "planner_node"}


def route_to_agent(state: SupervisorState) -> str:
    return AGENT_MAP.get(state["next_agent"], "code_agent")

# ============================================================
# Part 7: Build Graph
#
# 图的结构：
#   START
#     |
#     v
#   supervisor_node (classify)
#     |
#     v (conditional)
#   ┌──────┼──────┐
#   v      v      v
#  code  english career
#  agent  agent   agent
#   |      |      |
#   └──────┼──────┘
#          v
#         END
#
# 注意：code_agent / english_agent / career_agent 是
# 用 create_react_agent 创建的子图
# 它们内部有各自的 agent -> tool -> agent 循环
# 但在 Supervisor 图中，它们只是一个节点
# ============================================================


memory = MemorySaver()


def build_graph() -> StateGraph:
    builder = StateGraph(SupervisorState)

    # Register supervisor node
    builder.add_node("supervisor", supervisor_node)

    # Register sub-agents (these are compiled sub-graphs!)
    builder.add_node("code_agent", code_agent)
    builder.add_node("english_agent", english_agent)
    builder.add_node("career_agent", career_agent)
    builder.add_node("search_agent", search_agent)
    builder.add_node("research_agent", research_agent)
    builder.add_node("rag_agent", rag_agent)
    builder.add_node("planner_node", planner_node)

    # START -> supervisor
    builder.add_edge(START, "supervisor")

    # Conditional: supervisor -> sub-agent
    builder.add_conditional_edges("supervisor", route_to_agent)

    # Sub-agent -> END
    builder.add_edge("code_agent", END)
    builder.add_edge("english_agent", END)
    builder.add_edge("career_agent", END)
    builder.add_edge("search_agent", END)
    builder.add_edge("research_agent", END)
    builder.add_edge("rag_agent", END)
    builder.add_edge("planner_node", END)

    return builder.compile(checkpointer=memory)


graph = build_graph()
THREAD_ID = "supervisor-main"


def run(question: str) -> str:
    config = {"configurable": {"thread_id": THREAD_ID}}
    result = graph.invoke({
        "messages": [HumanMessage(content=question)],
        "next_agent": "",
    }, config)
    return result["messages"][-1].content