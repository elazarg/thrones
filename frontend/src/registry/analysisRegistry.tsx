import type { ReactNode } from 'react';
import type { AnalysisSectionResult, NashEquilibrium } from '../types';

/** Game format requirement for an analysis */
export type GameFormatRequirement = 'efg' | 'nfg' | 'maid';

/** Default options for an analysis */
export interface AnalysisDefaultOptions {
  solver?: 'exhaustive' | 'quick' | 'pure' | 'approximate';
  maxEquilibria?: number;
}

/** Props passed to content renderers */
export interface RendererProps {
  result: AnalysisSectionResult;
  onRun: () => void;
  // Equilibrium-specific props
  selectedIndex?: number | null;
  onSelectEquilibrium?: (index: number | null) => void;
  // IESDS-specific props
  isSelected?: boolean;
  isMatrixView?: boolean;
  onSelect?: () => void;
  // Extra footer for nash backoff
  extraFooter?: ReactNode;
}

/** Registry entry for an analysis type */
export interface AnalysisRegistryEntry {
  /** Unique identifier for this analysis (e.g., 'nash', 'iesds') */
  id: string;
  /** Display name shown in the UI */
  name: string;
  /** Tooltip description */
  description: string;
  /** Backend plugin name for API calls */
  pluginName: string;
  /** Game format requirements - analysis is available if any of these formats are supported */
  requires: GameFormatRequirement[];
  /** Key for backend applicability check (e.g., 'Exploitability') */
  applicabilityKey?: string;
  /** Default options to pass when running analysis */
  defaultOptions?: AnalysisDefaultOptions;
  /** Override loading text (default: "Computing...") */
  loadingText?: string;
  /** Whether this analysis supports equilibrium selection highlighting */
  supportsSelection?: boolean;
  /** Render badge content (count, quality indicator, etc.) */
  renderBadge?: (result: AnalysisSectionResult) => ReactNode;
  /** Render main content area */
  renderContent: (props: RendererProps) => ReactNode;
}

// Badge render helpers - defined here to avoid circular imports
function renderEquilibriaBadge(result: AnalysisSectionResult): ReactNode {
  if (!result) return null;
  const equilibria = result.details.equilibria as NashEquilibrium[] | undefined;
  if (!equilibria) return null;
  return (
    <span className="count-badge">
      {equilibria.length}
      {!result.details.exhaustive && '+'}
    </span>
  );
}

function renderIESDSBadge(result: AnalysisSectionResult): ReactNode {
  if (!result) return null;
  const eliminated = result.details.eliminated as unknown[] | undefined;
  const count = eliminated?.length ?? 0;
  return (
    <span className={`count-badge ${count === 0 ? 'none' : ''}`}>
      {count === 0 ? '0' : `-${count}`}
    </span>
  );
}

function renderExploitabilityBadge(result: AnalysisSectionResult): ReactNode {
  if (!result) return null;
  const nashConv = result.details.nash_conv as number | undefined;
  const quality = result.details.quality as string | undefined;
  if (nashConv === undefined || quality === undefined) return null;

  const getQualityClass = (q: string) => {
    const lower = q.toLowerCase();
    if (lower.includes('near-optimal') || lower.includes('essentially nash')) return 'good';
    if (lower.includes('very good') || lower.includes('good')) return 'moderate';
    return 'poor';
  };

  return (
    <span className={`quality-badge ${getQualityClass(quality)}`}>
      {nashConv.toFixed(4)}
    </span>
  );
}

function renderReplicatorBadge(result: AnalysisSectionResult): ReactNode {
  if (!result) return null;
  const timeSteps = result.details.time_steps as number | undefined;
  if (timeSteps === undefined) return null;
  return <span className="count-badge">{timeSteps} steps</span>;
}

function renderEvolutionaryBadge(result: AnalysisSectionResult): ReactNode {
  if (!result) return null;
  const popSize = result.details.population_size as number | undefined;
  if (popSize === undefined) return null;
  return <span className="count-badge">N={popSize}</span>;
}

function renderCFRBadge(result: AnalysisSectionResult): ReactNode {
  if (!result) return null;
  const iterations = result.details.iterations as number | undefined;
  if (iterations === undefined) return null;
  return <span className="count-badge">{iterations} iter</span>;
}

/** Central registry of all analysis types */
export const ANALYSIS_REGISTRY: AnalysisRegistryEntry[] = [
  // MAID analyses
  {
    id: 'maid-nash',
    name: 'MAID Nash',
    description: 'Compute Nash equilibria for the Multi-Agent Influence Diagram',
    pluginName: 'MAID Nash Equilibrium',
    requires: ['maid'],
    supportsSelection: true,
    renderBadge: renderEquilibriaBadge,
    renderContent: () => null, // Placeholder - will use EquilibriumRenderer
  },
  {
    id: 'maid-spe',
    name: 'MAID SPE',
    description: 'Compute subgame perfect equilibria for the MAID',
    pluginName: 'MAID Subgame Perfect Equilibrium',
    requires: ['maid'],
    supportsSelection: true,
    renderBadge: renderEquilibriaBadge,
    renderContent: () => null, // Placeholder - will use EquilibriumRenderer
  },
  // EFG/NFG analyses
  {
    id: 'pure-ne',
    name: 'Pure NE',
    description: 'Find all pure-strategy Nash equilibria',
    pluginName: 'Nash Equilibrium',
    requires: ['efg'],
    defaultOptions: { solver: 'pure' },
    supportsSelection: true,
    renderBadge: renderEquilibriaBadge,
    renderContent: () => null, // Placeholder - will use EquilibriumRenderer
  },
  {
    id: 'nash',
    name: 'Nash Equilibrium',
    description: "Find Nash equilibria (click 'Find more' to search deeper)",
    pluginName: 'Nash Equilibrium',
    requires: ['efg'],
    defaultOptions: { solver: 'quick' },
    supportsSelection: true,
    renderBadge: renderEquilibriaBadge,
    renderContent: () => null, // Placeholder - will use EquilibriumRenderer
  },
  {
    id: 'approx-ne',
    name: 'Approximate NE',
    description: 'Fast approximate equilibrium via simplicial subdivision',
    pluginName: 'Nash Equilibrium',
    requires: ['efg'],
    defaultOptions: { solver: 'approximate' },
    supportsSelection: true,
    renderBadge: renderEquilibriaBadge,
    renderContent: () => null, // Placeholder - will use EquilibriumRenderer
  },
  {
    id: 'iesds',
    name: 'IESDS',
    description: 'Iteratively Eliminate Strictly Dominated Strategies',
    pluginName: 'IESDS',
    requires: ['efg'],
    renderBadge: renderIESDSBadge,
    renderContent: () => null, // Placeholder - will use IESDSRenderer
  },
  // OpenSpiel analyses
  {
    id: 'exploitability',
    name: 'Exploitability',
    description: 'Measure distance from Nash equilibrium',
    pluginName: 'Exploitability',
    requires: ['efg'],
    applicabilityKey: 'Exploitability',
    renderBadge: renderExploitabilityBadge,
    renderContent: () => null, // Placeholder - will use ExploitabilityRenderer
  },
  {
    id: 'cfr-convergence',
    name: 'CFR Convergence',
    description: 'Run CFR and track exploitability convergence',
    pluginName: 'CFR Convergence',
    requires: ['efg'],
    applicabilityKey: 'CFR Convergence',
    loadingText: 'Running CFR...',
    renderBadge: renderCFRBadge,
    renderContent: () => null, // Placeholder - will use CFRConvergenceRenderer
  },
  // EGTTools analyses
  {
    id: 'replicator-dynamics',
    name: 'Replicator Dynamics',
    description: 'Simulate strategy evolution using replicator dynamics',
    pluginName: 'Replicator Dynamics',
    requires: ['nfg'],
    applicabilityKey: 'Replicator Dynamics',
    loadingText: 'Simulating...',
    renderBadge: renderReplicatorBadge,
    renderContent: () => null, // Placeholder - will use ReplicatorDynamicsRenderer
  },
  {
    id: 'evolutionary-stability',
    name: 'Evolutionary Stability',
    description: 'Analyze evolutionary stability via finite population dynamics',
    pluginName: 'Evolutionary Stability',
    requires: ['nfg'],
    applicabilityKey: 'Evolutionary Stability',
    renderBadge: renderEvolutionaryBadge,
    renderContent: () => null, // Placeholder - will use EvolutionaryStabilityRenderer
  },
];

/** Map from analysis ID to registry entry for fast lookup */
const REGISTRY_BY_ID = new Map(ANALYSIS_REGISTRY.map((entry) => [entry.id, entry]));

/**
 * Get the backend plugin name for an analysis ID.
 * Falls back to the ID itself if not found in registry.
 */
export function getPluginName(analysisId: string): string {
  return REGISTRY_BY_ID.get(analysisId)?.pluginName ?? analysisId;
}

/**
 * Get registry entry by analysis ID.
 */
export function getRegistryEntry(analysisId: string): AnalysisRegistryEntry | undefined {
  return REGISTRY_BY_ID.get(analysisId);
}

/**
 * Get all analyses applicable to the given game format capabilities.
 */
export function getApplicableAnalyses(
  isEfgCapable: boolean,
  isNfgCapable: boolean,
  isMaidCapable: boolean
): AnalysisRegistryEntry[] {
  return ANALYSIS_REGISTRY.filter((entry) => {
    // Check if any of the required formats are supported
    return entry.requires.some((req) => {
      switch (req) {
        case 'efg':
          return isEfgCapable;
        case 'nfg':
          return isNfgCapable;
        case 'maid':
          return isMaidCapable;
        default:
          return false;
      }
    });
  });
}

/**
 * Get analyses grouped by format requirement.
 * Useful for rendering sections in the UI.
 */
export function getAnalysesByFormat(): {
  maid: AnalysisRegistryEntry[];
  efg: AnalysisRegistryEntry[];
  nfg: AnalysisRegistryEntry[];
} {
  return {
    maid: ANALYSIS_REGISTRY.filter((e) => e.requires.includes('maid')),
    efg: ANALYSIS_REGISTRY.filter((e) => e.requires.includes('efg')),
    nfg: ANALYSIS_REGISTRY.filter((e) => e.requires.includes('nfg')),
  };
}

/**
 * Get the default options for an analysis.
 */
export function getDefaultOptions(analysisId: string): AnalysisDefaultOptions | undefined {
  return REGISTRY_BY_ID.get(analysisId)?.defaultOptions;
}
