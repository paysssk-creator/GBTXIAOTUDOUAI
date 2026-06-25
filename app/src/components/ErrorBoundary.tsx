import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="boot-screen">
          <div className="boot-card">
            <h1 className="boot-title" style={{ color: "var(--error)" }}>应用启动失败</h1>
            <p className="boot-message">
              渲染时发生错误，请尝试重启应用或重新安装。
            </p>
            <pre
              style={{
                textAlign: "left",
                fontSize: 12,
                maxHeight: 240,
                overflow: "auto",
                padding: 12,
                background: "var(--bg)",
                borderRadius: 8,
                color: "var(--fg-dim)",
                wordBreak: "break-word",
                whiteSpace: "pre-wrap",
              }}
            >
              {this.state.error.stack || this.state.error.message}
            </pre>
            <button
              className="btn btn-primary mt-3 w-full"
              onClick={() => window.location.reload()}
            >
              重试
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
