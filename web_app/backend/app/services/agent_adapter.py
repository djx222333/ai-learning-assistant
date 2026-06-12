# -*- coding: utf-8 -*-
"""Adapter layer between web_app and supervisor_agent"""
import sys, os
from app.core.config import settings
os.environ["DEEPSEEK_API_KEY"] = settings.DEEPSEEK_API_KEY
os.environ["DEEPSEEK_MODEL"] = settings.DEEPSEEK_MODEL
os.environ["DEEPSEEK_BASE_URL"] = settings.DEEPSEEK_BASE_URL
ADAPTER_DIR = os.path.dirname(os.path.abspath(__file__))
SUPERVISOR_DIR = os.path.abspath(os.path.join(ADAPTER_DIR,"..","..","..","..","supervisor_agent"))
if SUPERVISOR_DIR not in sys.path: sys.path.insert(0, SUPERVISOR_DIR)
_orig = os.getcwd()
os.chdir(SUPERVISOR_DIR)
try:
    import agent_graph as _ag
    graph = _ag.get_graph()  # lazy init, returns the graph
    HumanMessage = _ag.HumanMessage
    MemorySaver = _ag.MemorySaver
finally:
    os.chdir(_orig)
AGENT_MAP = {"code":"Code Agent","english":"English Agent","career":"Career Agent","search":"Search Agent","research":"Research Agent","rag":"RAG Agent","planner":"Planner"}
def chat(message, session_id=None):
    conf = {"configurable":{"thread_id":session_id or "default"}}
    r = graph.invoke({"messages":[HumanMessage(content=message)],"next_agent":""}, conf)
    agent = r.get("next_agent","")
    return {"answer":r["messages"][-1].content,"agent_type":agent,"agent_name":AGENT_MAP.get(agent,"Assistant")}
