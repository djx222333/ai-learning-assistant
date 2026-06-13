import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  componentStack: string;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, componentStack: "" };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("=== [ErrorBoundary] ERROR ===", error);
    console.error("=== [ErrorBoundary] COMPONENT STACK ===", errorInfo.componentStack);
    this.setState({ componentStack: errorInfo.componentStack || "" });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 40, fontFamily: "monospace", maxWidth: 800, margin: "0 auto" }}>
          <h2 style={{ color: "#dc2626", marginBottom: 12 }}>React Error Boundary</h2>
          <h3 style={{ color: "#991b1b", marginBottom: 8 }}>Error</h3>
          <pre style={{
            background: "#fef2f2", border: "1px solid #fca5a5",
            borderRadius: 8, padding: 16, color: "#dc2626",
            whiteSpace: "pre-wrap", wordBreak: "break-word", fontSize: 13
          }}>
            {this.state.error?.toString()}
          </pre>
          <h3 style={{ color: "#991b1b", marginTop: 16, marginBottom: 8 }}>Component Stack</h3>
          <pre style={{
            background: "#f8fafc", border: "1px solid #cbd5e1",
            borderRadius: 8, padding: 16, color: "#64748b",
            whiteSpace: "pre-wrap", wordBreak: "break-word", fontSize: 12,
            maxHeight: 400, overflow: "auto"
          }}>
            {this.state.componentStack || "(no component stack)"}
          </pre>
          <h3 style={{ color: "#991b1b", marginTop: 16, marginBottom: 8 }}>Full Error Object</h3>
          <pre style={{
            background: "#f8fafc", border: "1px solid #cbd5e1",
            borderRadius: 8, padding: 16, color: "#64748b",
            whiteSpace: "pre-wrap", wordBreak: "break-word", fontSize: 11,
            maxHeight: 300, overflow: "auto"
          }}>
            {JSON.stringify(this.state.error, Object.getOwnPropertyNames(this.state.error ?? {}), 2)}
          </pre>
          <button
            onClick={() => window.location.reload()}
            style={{
              marginTop: 20, padding: "8px 24px",
              background: "#3b82f6", color: "white",
              border: "none", borderRadius: 8, cursor: "pointer",
              fontSize: 14
            }}
          >
            重新加载
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
