import { Component, type ErrorInfo, type ReactNode } from "react";

type Props = { children: ReactNode };
type State = { error: Error | null };

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("App error:", error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-[--color-bg] p-6">
          <div className="max-w-sm rounded-[--radius-lg] border border-[--color-border] bg-[--color-bg-elevated] p-6 text-center">
            <p className="font-medium">Something went wrong.</p>
            <p className="mt-2 text-sm text-[--color-text-muted]">
              {this.state.error.message}
            </p>
            <button
              type="button"
              className="mt-4 text-sm text-[--color-accent] hover:underline"
              onClick={() => window.location.reload()}
            >
              Reload
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
