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
import logging
_logger = logging.getLogger(__name__)

print("[BOOT] agent_graph imported")

load_dotenv()


# ============================================================
# Part 1: State
#
# SupervisorState 閹碘晛鐫?MessagesState閿涘矂娅庢禍?messages 鐎涙顔屾径?
# 鏉╂ê顦挎禍鍡曠娑?next_agent 鐎涙顔岄敍宀€鏁ら弶銉唶瑜?Supervisor 閸愬啿鐣?
# 娑撳绔村銉洣鐠嬪啰鏁ら崫顏冮嚋鐎?Agent
# ============================================================


class SupervisorState(MessagesState):
    """Supervisor 閻樿埖鈧?
    messages:   鐎电鐦介崢鍡楀蕉閿涘牊澧嶉張澶婄摍 Agent 閸忓彉闊╅敍?
    next_agent: Supervisor 閸愬啿鐣鹃惃鍕瑓娑撯偓娑?Agent 閸氬秴鐡?
    """
    next_agent: str


# ============================================================
# Part 2: Tools
#
# 鏉╂瑤绨哄銉ュ徔閸欘垯浜掔悮顐㈢摍 Agent 鐠嬪啰鏁?
# Code Agent 閼冲€熺殶 calculator + read_file
# English/Career Agent 閸欘亣鍏樼拫?read_file
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
# 鏉╂瑤琚辨稉顏勪紣閸忕柉顔€ Agent 閼冲€燁嚢閸?user_profile.json
# 鐎圭偟骞囩捄銊ょ窗鐠囨繄娈戦悽銊﹀煕閻㈣鍎氶幐浣风畽閸?

# read_profile: Agent 閻劍娼电拠璇插絿閻劍鍩涢懗灞炬珯娣団剝浼?
# update_profile: Agent 閸︺劋绨＄憴锝呭煂閺傞淇婇幁顖涙閻劍娼甸弴瀛樻煀


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
rag_engine = None
_rag_engine_loaded = False


def _get_rag_engine():
    global rag_engine, _rag_engine_loaded
    if not _rag_engine_loaded:
        rag_engine = RAGEngine()
        _rag_engine_loaded = True
    return rag_engine


@tool
def ingest_pdf(file_path: str) -> str:
    """Upload and index a PDF file.
    Use this when the user wants to ask questions about a document.
    Args:
        file_path: path to the PDF file
    """
    return _get_rag_engine().ingest_pdf(file_path)


@tool
def rag_search(query: str, top_k: int = 3) -> str:
    """Search indexed documents and return relevant passages.
    Use this after ingest_pdf to answer questions about the document.
    Args:
        query: what to search for
        top_k: number of passages to return
    """
    results = _get_rag_engine().search(query, top_k)
    return "\n---\n".join(results)


# ============================================================
# Part 3: LLM Helper
# ============================================================


DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")


def get_llm(model="deepseek-chat"):
    print("[BOOT] get_llm called")
    print("[BOOT] get_llm called")
    if not DEEPSEEK_API_KEY or "xxx" in DEEPSEEK_API_KEY:
        _logger.warning("DeepSeek API key missing, LLM unavailable")
        return None
    return ChatOpenAI(model=model, api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com/v1", temperature=0.7)


# 閸掓媽绻栧銉ュ帥閸嬫粣绱濇稉瀣╃濮濄儱鍨卞?3 娑擃亜鐡?Agent

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
code_agent = None

# ---------- English Agent ----------
english_prompt = SystemMessage(content="You are an English teacher. Provide grammar explanations and examples.")
english_agent = None

# ---------- Career Agent ----------
career_prompt = SystemMessage(content="You are a study planning consultant. Before making a plan, use read_profile to learn about the user background. After the user shares personal info, use update_profile to save it. Provide plans with timelines.")
career_agent = None

# ---------- Search Agent ----------
# 閼卞矁鐭楅敍姘充粓缂冩垶鎮崇槐銏犵杽閺冩湹淇婇幁?
# 瀹搞儱鍙块敍姝竐b_search
#
# 娑撹桨绮堟稊?Search Agent 鐟曚胶鏁?create_react_agent 閼板奔绗夐弰顖涙珮闁艾鍤遍弫甯吹
#   閹兼粎鍌ㄦ稉宥嗘Ц鐠嬪啩绔村▎鈥冲毐閺佹澘姘ㄧ紒鎾存将閻ㄥ嫪绨ㄩ幆鍛偓?
#   閸欘垵鍏樼粭顑跨濞嗏剝鎮抽惃鍕波閺嬫粈绗夋径鐔虹翱绾噯绱濋棁鈧憰浣界殶閺佹潙鍙ч柨顔跨槤閸愬秵鎮抽妴?
#   create_react_agent 閹绘劒绶垫禍?agent 閳?tools 閳?agent 閻ㄥ嫬鎯婇悳顖濆厴閸旀稏鈧?

search_prompt = SystemMessage(content="You are a search specialist. Use web_search to find current information. If results are not clear, try different keywords.")
search_agent = None

# ---------- Research Agent ----------
# 閼卞矁鐭楅敍姘偝闂嗗棜绁弬?+ 閺佸鎮婄挧鍕灐 + 鏉堟挸鍤紒鎾寸€崠鏍ㄥГ閸?
# 瀹搞儱鍙块敍姝竐b_search閿涘牊鎮崇槐銏犳倗缁夊秵娼靛┃鎰剁礆+ read_file閿涘牐顕伴張顒€婀撮崣鍌濃偓鍐╂瀮娴犺绱?
#
# 娑?Search Agent 閻ㄥ嫬灏崚顐窗
#   Search: 閹兼粈绔村▎?閳?閻╁瓨甯撮崶鐐电摕
#   Research: 婢舵碍顐奸幖婊呭偍 閳?娴溿倕寮舵宀冪槈 閳?鐠囩粯鏋冩禒?閳?鏉堟挸鍤幎銉ユ啞

research_prompt = SystemMessage(content="You are a research analyst. Use web_search to gather information from multiple sources, and read_file to examine local reference materials. Organize your findings into a structured report with sections, key findings, and source citations. If initial search results are insufficient, try different search keywords to get comprehensive coverage.")
research_agent = None


# ---------- RAG Agent ----------
# 閼卞矁鐭楅敍姘瀮濡楋綁妫剁粵鏃撶礄娑撳﹣绱?PDF 閳?濡偓缁?閳?閸ョ偟鐡熼敍?
# 瀹搞儱鍙块敍姝﹏gest_pdf閿涘牅绗傛导鐘茬紦缁便垹绱╅敍? rag_search閿涘牊顥呯槐銏ゆ６缁涙棑绱?
#
# 娑?Search Agent 閻ㄥ嫬灏崚顐窗
#   Search: 閹兼粈绨伴懕鏃傜秹
#   RAG: 閹兼粈缍橀懛顏勭箒娑撳﹣绱堕惃鍕瀮濡?
#
# 娑?Research Agent 閻ㄥ嫬灏崚顐窗
#   Research: 婢舵碍娼靛┃鎰殶閻棑绱濇潏鎾冲毉閹躲儱鎲?
#   RAG: 閸╄桨绨悧鐟扮暰閺傚洦銆傞惃鍕翱閸戝棝妫剁粵?
rag_prompt = SystemMessage(content="You are a document Q&A assistant. When the user provides a PDF file, use ingest_pdf to index it. When they ask questions, use rag_search to find relevant passages and answer based on the document. Always cite the source chunks. IMPORTANT: If the knowledge base is empty or no relevant content is found, answer the question based on your own knowledge. Never refuse to answer.")
rag_agent = None

# ============================================================

# ============================================================
# Lazy Agent Initialization
# All agents are created on first call, not at import time.
# This ensures uvicorn can start even without an API key.
# ============================================================
def _ensure_agents():
    """Lazily initialize all sub-agents if not already created."""
    global code_agent, english_agent, career_agent
    global search_agent, research_agent, rag_agent

    if code_agent is not None:
        return  # already initialized

    llm = get_llm()
    if llm is None:
        _logger.warning("LLM not available - agents will run without tools")
        return  # cannot create agents without LLM

    code_agent = create_react_agent(
        llm,
        [read_profile, calculator, read_file, update_profile],
        prompt=code_prompt,
    )
    english_agent = create_react_agent(
        llm,
        [],
        prompt=english_prompt,
    )
    career_agent = create_react_agent(
        llm,
        [read_profile, update_profile],
        prompt=career_prompt,
    )
    search_agent = create_react_agent(
        llm,
        [web_search],
        prompt=search_prompt,
    )
    research_agent = create_react_agent(
        llm,
        [web_search, read_file],
        prompt=research_prompt,
    )
    rag_agent = create_react_agent(
        llm,
        [ingest_pdf, rag_search],
        prompt=rag_prompt,
    )
# Part 5: Supervisor Node
# Supervisor classifies the question and returns next_agent
# ============================================================


def supervisor_node(state: SupervisorState) -> dict:
    _ensure_agents()
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
# Planner 閹恒儲鏁规径宥嗘絽闂傤噣顣介敍灞惧閹存劕顦挎稉顏勭摍娴犺濮熼敍灞肩贩濞喡ょ殶閻劋绗夐崥宀€娈?Agent閿?
# 閺€鍫曟肠缂佹挻鐏夐獮鑸电湽閹粯鍨氶張鈧紒鍫濇礀缁涙柣鈧?
#
# 娑撹桨绮堟稊?Planner 閺勵垱娅橀柅姘毐閺佹媽鈧奔绗夐弰?create_react_agent閿?
#   Planner 闂団偓鐟曚線浜堕崢鍡曟崲閸斺€冲灙鐞涖劊鈧椒绶峰▎陇鐨熺€?Agent閵嗕焦鐪归幀鑽ょ波閺嬫壕鈧柡鈧?
#   鏉╂瑤绨洪弰顖滅椽閹烘帡鈧槒绶敍灞肩瑝閺?ReAct 瀵邦亞骞嗛妴鍌涙珮闁艾鍤遍弫鐗堟纯闁倸鎮庨妴?
# ============================================================


AGENT_MAP_PLAN = {}

def _get_agent_map():
    if not AGENT_MAP_PLAN:
        _ensure_agents()
        AGENT_MAP_PLAN.update({
            "code": code_agent,
            "english": english_agent,
            "career": career_agent,
            "search": search_agent,
            "research": research_agent,
            "rag": rag_agent,
        })
    return AGENT_MAP_PLAN


def planner_node(state: SupervisorState) -> dict:
    _ensure_agents()
    """Planner: receive complex question, split tasks, collect results"""
    import json
    from langchain_core.messages import HumanMessage, AIMessage

    question = state["messages"][-1].content
    llm = get_llm()

    # Step 1: LLM 閹峰棜袙娴犺濮?
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

    # Step 2: 鐟欙絾鐎芥禒璇插閸掓銆?
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


    # Step 3: 娓氭繃顐奸幍褑顢戝В蹇庨嚋鐎涙劒鎹㈤崝?
    results = []
    for t in tasks:
        agent_name = t.get("agent", "code")
        task_desc = t.get("task", question)
        agent = _get_agent_map().get(agent_name)
        if agent is None:
            continue
        try:
            r = agent.invoke({"messages": [HumanMessage(content=task_desc)]})
            answer = r["messages"][-1].content
            results.append(f"[{agent_name.upper()}] {task_desc}\n{answer}")
        except Exception as e:
            results.append(f"[{agent_name.upper()}] Error: {e}")

    # Step 4: 濮瑰洦鈧崵绮ㄩ弸?
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
# 閸ュ墽娈戠紒鎾寸€敍?
#   START
#     |
#     v
#   supervisor_node (classify)
#     |
#     v (conditional)
#   閳瑰备鏀㈤埞鈧埞鈧埞鈧埞鈧埞鈧埞灏栨敘閳光偓閳光偓閳光偓閳光偓閳光偓閳?
#   v      v      v
#  code  english career
#  agent  agent   agent
#   |      |      |
#   閳规柡鏀㈤埞鈧埞鈧埞鈧埞鈧埞鈧埞灏栨敘閳光偓閳光偓閳光偓閳光偓閳光偓閳?
#          v
#         END
#
# 濞夈劍鍓伴敍姝漮de_agent / english_agent / career_agent 閺?
# 閻?create_react_agent 閸掓稑缂撻惃鍕摍閸?
# 鐎瑰啩婊戦崘鍛村劥閺堝鎮囬懛顏嗘畱 agent -> tool -> agent 瀵邦亞骞?
# 娴ｅ棗婀?Supervisor 閸ュ彞鑵戦敍灞界暊娴狀剙褰ч弰顖欑娑擃亣濡悙?
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



THREAD_ID = "supervisor-main"


def run(question: str) -> str:
    config = {"configurable": {"thread_id": THREAD_ID}}
    result = graph.invoke({
        "messages": [HumanMessage(content=question)],
        "next_agent": "",
    }, config)
    return result["messages"][-1].content

# Lazy graph
_graph_instance = None

def get_graph():
    print("[BOOT] get_graph called")
    print("[BOOT] get_graph called")
    global _graph_instance
    if _graph_instance is None:
        _ensure_agents()
        _graph_instance = build_graph()
    return _graph_instance

graph = None
