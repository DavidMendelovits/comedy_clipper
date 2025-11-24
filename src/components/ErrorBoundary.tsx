/**
 * Error Boundary Component
 * Catches React errors and provides a graceful fallback UI
 */

import { Component, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: React.ErrorInfo;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({ errorInfo });
  }

  handleReset = () => {
    this.setState({ hasError: false, error: undefined, errorInfo: undefined });
  };

  handleGoHome = () => {
    window.location.hash = '#/';
    this.handleReset();
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen bg-[var(--color-bg-primary)] flex items-center justify-center p-8">
          <div className="max-w-2xl w-full bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg p-8">
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0">
                <AlertTriangle className="text-[var(--color-error)]" size={48} />
              </div>
              <div className="flex-1">
                <h1 className="text-2xl font-bold text-[var(--color-text-primary)] mb-2">
                  Oops! Something went wrong
                </h1>
                <p className="text-[var(--color-text-secondary)] mb-4">
                  An unexpected error occurred. This has been logged and you can try the actions below.
                </p>

                {this.state.error && (
                  <div className="bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg p-4 mb-4">
                    <p className="font-mono text-sm text-[var(--color-error)] mb-2">
                      {this.state.error.message}
                    </p>
                    {this.state.errorInfo && (
                      <details className="mt-2">
                        <summary className="text-sm text-[var(--color-text-muted)] cursor-pointer hover:text-[var(--color-text-secondary)]">
                          Stack trace
                        </summary>
                        <pre className="mt-2 text-xs text-[var(--color-text-muted)] overflow-auto max-h-64">
                          {this.state.errorInfo.componentStack}
                        </pre>
                      </details>
                    )}
                  </div>
                )}

                <div className="flex gap-3">
                  <button
                    onClick={this.handleReset}
                    className="flex items-center gap-2 px-4 py-2 bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white rounded-lg transition-colors"
                  >
                    <RefreshCw size={18} />
                    Try Again
                  </button>
                  <button
                    onClick={this.handleGoHome}
                    className="flex items-center gap-2 px-4 py-2 bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-hover)] border border-[var(--color-border)] text-[var(--color-text-primary)] rounded-lg transition-colors"
                  >
                    <Home size={18} />
                    Go Home
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
