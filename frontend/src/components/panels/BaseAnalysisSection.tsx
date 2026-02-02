import type { ReactNode } from 'react';
import type { AnalysisSectionResult } from '../../types';
import { isAnalysisError } from '../../types';

export interface BaseAnalysisSectionProps {
  /** Unique identifier for this analysis */
  analysisId: string;
  /** Display name shown in the header */
  name: string;
  /** Tooltip description */
  description: string;
  /** Analysis result (or null if not yet run) */
  result: AnalysisSectionResult;
  /** Whether this analysis is currently computing */
  isLoading: boolean;
  /** Whether the section is expanded */
  isExpanded: boolean;
  /** Whether this analysis is disabled */
  disabled?: boolean;
  /** Reason for being disabled (shown in tooltip) */
  disabledReason?: string;
  /** Handler to toggle expand/collapse */
  onToggle: () => void;
  /** Handler to run the analysis */
  onRun: () => void;
  /** Handler to cancel the analysis */
  onCancel: () => void;
  /** Loading text override (default: "Computing...") */
  loadingText?: string;
  /** Render badge content in the header */
  renderBadge?: () => ReactNode;
  /** Render the main content area when expanded */
  renderContent: () => ReactNode;
  /** Render extra footer content (e.g., "Find more" button) */
  renderExtraFooter?: () => ReactNode;
  /** Whether to show timing badge */
  showTimingBadge?: boolean;
  /** Whether to show the Recompute footer button (default: true) */
  showRecomputeButton?: boolean;
}

export function BaseAnalysisSection({
  name,
  description,
  result,
  isLoading,
  isExpanded,
  disabled,
  disabledReason,
  onToggle,
  onRun,
  onCancel,
  loadingText = 'Computing...',
  renderBadge,
  renderContent,
  renderExtraFooter,
  showTimingBadge = true,
  showRecomputeButton = true,
}: BaseAnalysisSectionProps) {
  const hasResult = !!result;
  const isError = isAnalysisError(result);
  const canExpand = (hasResult || isLoading) && !disabled;

  const handleHeaderClick = () => {
    if (disabled) return;
    if (canExpand) {
      onToggle();
    } else {
      onRun();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleHeaderClick();
    }
  };

  // Determine the icon to show
  const renderIcon = () => {
    if (isLoading) {
      return <span className="spinner-small"></span>;
    }
    if (canExpand) {
      return isExpanded ? '▼' : '▶';
    }
    return '▶';
  };

  // Build trigger class names
  const triggerClasses = [
    'analysis-trigger',
    hasResult && !isError ? 'has-result' : '',
    isError ? 'has-error' : '',
    disabled ? 'disabled' : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={`analysis-section ${isExpanded && canExpand ? 'expanded' : ''}`}>
      <div
        className={triggerClasses}
        role="button"
        tabIndex={disabled ? -1 : 0}
        onClick={handleHeaderClick}
        onKeyDown={handleKeyDown}
        aria-expanded={canExpand ? isExpanded : undefined}
        aria-disabled={disabled}
        title={disabled ? disabledReason : undefined}
      >
        <span className="trigger-icon">{renderIcon()}</span>
        <span className="trigger-text">{name}</span>

        <div className="trigger-badges">
          {showTimingBadge && result?.details.computation_time_ms !== undefined && (
            <span className="timing-badge">{result.details.computation_time_ms as number}ms</span>
          )}
          {hasResult && !isError && renderBadge?.()}
        </div>

        {isLoading && (
          <button
            type="button"
            className="stop-link"
            onClick={(e) => {
              e.stopPropagation();
              onCancel();
            }}
          >
            Stop
          </button>
        )}

        {description && (
          <span
            className="help-icon"
            title={description}
            onClick={(e) => e.stopPropagation()}
          >
            ?
          </span>
        )}
      </div>

      {isExpanded && canExpand && (
        <div className="analysis-content">
          {/* Loading state */}
          {isLoading && !result && (
            <div className="analysis-loading">
              <span>{loadingText}</span>
            </div>
          )}

          {/* Main content - render for both success and error states */}
          {hasResult && !isError && (
            <>
              {renderContent()}
              {(showRecomputeButton || renderExtraFooter) && (
                <div className="analysis-section-footer">
                  {renderExtraFooter?.()}
                  {showRecomputeButton && (
                    <button
                      type="button"
                      className="rerun-link"
                      onClick={(e) => {
                        e.stopPropagation();
                        onRun();
                      }}
                    >
                      Recompute
                    </button>
                  )}
                </div>
              )}
            </>
          )}

          {/* Error state */}
          {hasResult && isError && (
            <div className="analysis-result-text analysis-error">
              {result.summary}
              <button
                type="button"
                className="rerun-link"
                onClick={(e) => {
                  e.stopPropagation();
                  onRun();
                }}
              >
                Retry
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
