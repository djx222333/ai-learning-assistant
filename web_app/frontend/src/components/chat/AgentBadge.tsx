// Agent 配置映射
const AGENT_CONFIG: Record<string, { icon: string; label: string; color: string }> = {
  code:     { icon: "💻", label: "Code Agent",     color: "bg-blue-100 text-blue-700" },
  english:  { icon: "🌍", label: "English Agent",  color: "bg-green-100 text-green-700" },
  career:   { icon: "📋", label: "Career Agent",   color: "bg-purple-100 text-purple-700" },
  search:   { icon: "🔍", label: "Search Agent",   color: "bg-orange-100 text-orange-700" },
  research: { icon: "📚", label: "Research Agent", color: "bg-red-100 text-red-700" },
  rag:      { icon: "📄", label: "RAG Agent",      color: "bg-teal-100 text-teal-700" },
  planner:  { icon: "📝", label: "Planner",        color: "bg-indigo-100 text-indigo-700" },
};

export default function AgentBadge({ agent_type }: { agent_type?: string }) {
  if (!agent_type) return null;
  const cfg = AGENT_CONFIG[agent_type] || { icon: "🤖", label: agent_type, color: "bg-gray-100 text-gray-700" };

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${cfg.color}`}>
      <span>{cfg.icon}</span>
      <span>{cfg.label}</span>
    </span>
  );
}
