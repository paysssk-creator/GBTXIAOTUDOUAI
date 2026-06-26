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
      const stack = this.state.error.stack || this.state.error.message;
      return (
        <div className="boot-screen">
          <div className="boot-card">
            <h1 className="boot-title" style={{ color: "var(--error)" }}>应用渲染失败</h1>
            <p className="boot-message">
              发生未捕获的渲染错误，请尝试重启应用或复制错误信息反馈。
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
              {stack}
            </pre>
            <div className="flex gap-2 mt-3">
              <button
                className="btn btn-primary flex-1"
                onClick={() => window.location.reload()}
              >
                重试
              </button>
              <button
                className="btn btn-ghost flex-1"
                onClick={async () => {
                  try {
                    await navigator.clipboard.writeText(stack);
                    alert("错误信息已复制到剪贴板");
                  } catch {
                    alert("复制失败，请手动复制上方日志");
                  }
                }}
              >
                复制错误
              </button>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
