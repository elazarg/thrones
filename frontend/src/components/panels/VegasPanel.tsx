/**
 * Collapsible Vegas panel for compilation actions.
 * Shows compile-to-X buttons based on advertised compile_targets from plugins.
 */
import { useState } from 'react';
import { usePluginStore, useGameStore } from '../../stores';
import type { CompileTarget, VegasGame } from '../../types';
import './VegasPanel.css';

interface VegasPanelProps {
  onSelectCompiledTab: (targetId: string) => void;
}

export function VegasPanel({ onSelectCompiledTab }: VegasPanelProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  const currentGame = useGameStore((s) => s.currentGame);
  const currentGameId = useGameStore((s) => s.currentGameId);

  const plugins = usePluginStore((s) => s.plugins);
  const compiledCodeByGame = usePluginStore((s) => s.compiledCodeByGame);
  const compilingByGame = usePluginStore((s) => s.compilingByGame);
  const compileErrorByGame = usePluginStore((s) => s.compileErrorByGame);
  const compile = usePluginStore((s) => s.compile);

  // Compute compile targets from plugins
  const compileTargets: { pluginName: string; target: CompileTarget }[] = [];
  for (const plugin of plugins) {
    if (plugin.healthy && plugin.compile_targets) {
      for (const target of plugin.compile_targets) {
        compileTargets.push({ pluginName: plugin.name, target });
      }
    }
  }

  // Only show for Vegas games
  if (!currentGame || currentGame.format_name !== 'vegas') {
    return null;
  }

  // No compile targets available
  if (compileTargets.length === 0) {
    return null;
  }

  const vegasGame = currentGame as VegasGame;
  const sourceCode = vegasGame.source_code;
  const compiledCode = currentGameId ? compiledCodeByGame[currentGameId] || {} : {};
  const isCompiling = currentGameId ? compilingByGame[currentGameId] : null;
  const compileError = currentGameId ? compileErrorByGame[currentGameId] : null;

  const handleCompile = async (pluginName: string, target: CompileTarget) => {
    if (!currentGameId || !sourceCode) return;
    await compile(currentGameId, sourceCode, pluginName, target);
    // Auto-select the compiled tab after successful compilation
    // Check the store state after the async operation completes
    const { compileErrorByGame: errors, compiledCodeByGame: compiled } = usePluginStore.getState();
    if (!errors[currentGameId] && compiled[currentGameId]?.[target.id]) {
      onSelectCompiledTab(target.id);
    }
  };

  return (
    <div className="vegas-panel">
      <button
        type="button"
        className={`vegas-header ${isExpanded ? 'expanded' : ''}`}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="vegas-icon">{isExpanded ? '\u25BC' : '\u25B6'}</span>
        <span className="vegas-title">Vegas</span>
      </button>

      {isExpanded && (
        <div className="vegas-content">
          <div className="compile-section">
            <div className="compile-label">Compile to:</div>
            <div className="compile-buttons">
              {compileTargets.map(({ pluginName, target }) => {
                const isThisCompiling = isCompiling === target.id;
                const isCompiled = !!compiledCode[target.id];

                return (
                  <button
                    key={`${pluginName}-${target.id}`}
                    type="button"
                    className={`compile-button ${isCompiled ? 'compiled' : ''}`}
                    onClick={() => handleCompile(pluginName, target)}
                    disabled={!!isCompiling}
                    title={isCompiled ? `Recompile to ${target.label}` : `Compile to ${target.label}`}
                  >
                    {isThisCompiling ? (
                      <span className="compiling-spinner" />
                    ) : isCompiled ? (
                      <span className="compiled-check">{'\u2713'}</span>
                    ) : null}
                    {target.label}
                  </button>
                );
              })}
            </div>
          </div>

          {compileError && (
            <div className="compile-error">
              <span className="error-icon">{'\u26A0'}</span>
              <span className="error-message">{compileError}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
