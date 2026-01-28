import { Component, type ReactNode } from 'react';
import { logger } from '../lib/logger';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  /** Optional name to identify which boundary caught the error */
  name?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * Error boundary component that catches JavaScript errors in child components.
 * Prevents the entire app from crashing when a component throws.
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    const name = this.props.name ?? 'Unknown';
    logger.error(`ErrorBoundary [${name}] caught error:`, error);
    logger.error('Component stack:', errorInfo.componentStack);
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="error-boundary-fallback">
          <h3>Something went wrong</h3>
          <p>{this.state.error?.message ?? 'An unexpected error occurred'}</p>
          <button onClick={this.handleRetry}>Try Again</button>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * Simple inline error fallback for smaller sections.
 */
export function ErrorFallback({ message, onRetry }: { message?: string; onRetry?: () => void }) {
  return (
    <div className="error-fallback">
      <span className="error-icon">⚠</span>
      <span className="error-message">{message ?? 'Error loading content'}</span>
      {onRetry && (
        <button className="error-retry" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}
