export interface AgentLog {
  agentName: string;
  role: string;
  message: string;
  status: 'thinking' | 'done' | 'idle' | 'error';
  timestamp: string;
}

export interface CriticVote {
  critic: 'purist' | 'marketer' | 'novelty';
  verdict: 'approve' | 'reject' | 'amend';
  score: number;
  reasoning: string;
  keyIssues: string[];
  recommendation: string;
}

export interface DebateRound {
  id: string;
  concept: string;
  votes: CriticVote[];
  directorSynthesis: string;
  finalVerdict: 'approved' | 'rejected' | 'iterated';
  consensusScore: number;
  debateLog: { speaker: string; line: string }[];
}

export interface EvalScores {
  brandFit: number;
  novelty: number;
  predictedPerformance: number;
  overallScore: number;
  breakdown: {
    brandFitReason: string;
    noveltyReason: string;
    predictedPerfReason: string;
  };
}

export interface HistoricalEntry {
  id: string;
  conceptName: string;
  timestamp: string;
  scores: EvalScores;
  status: 'approved' | 'rejected' | 'iterated';
}

export interface RationaleTrace {
  conceptName: string;
  platform: string;
  headline: string;
  tagline: string;
  colorPalette: string[];
  layoutDescription: string;
  decisions: {
    decision: string;
    rule: string;
    ruleSource: string;
    confidence: number;
  }[];
  hanlonReframe: string | null;
  competitorGap: string;
  suggestedIterations: string[];
}

export interface BriefData {
  brandName: string;
  platform: string;
  tone: string;
  files: string[];
  prompt: string;
}
