import { AgentLog } from './components/AgentVisualizer';
import { DebateRound, CriticVote } from './components/DebatePanel';
import { EvalScores, HistoricalEntry } from './components/EvalDashboard';
import { RationaleTrace } from './components/RationalePanel';
import { BriefData } from './components/BriefForm';

// ─── STEP TYPES ──────────────────────────────────────────────────────────────
interface SimStep {
  delayMs: number;
  logEntry?: AgentLog;
  activeAgent?: string | null;
  spawnedAgents?: string[];
  debateRound?: DebateRound;
  evalScores?: EvalScores;
  rationale?: RationaleTrace;
  historyEntry?: HistoricalEntry;
}

// ─── MOCK DATA GENERATORS ─────────────────────────────────────────────────────
function buildDebateRound(brief: BriefData): DebateRound {
  const brandName = brief.brandName.split(' - ')[0];
  const conceptName = `Bold ${brief.tone} Hero Shot`;
  const puristVote: CriticVote = {
    critic: 'purist',
    verdict: 'amend',
    score: 68,
    reasoning: `The concept uses an 87% match to ${brandName}'s approved color palette (violet-neon #7C3AED as primary, slate as secondary). However, the headline typeface — Inter ExtraBold — deviates from the brand's mandated Space Grotesk. Additionally, the logo placement at top-right conflicts with the brand guide's "bottom-left, 8% canvas width" rule. These are Rule Class A violations (non-negotiable corrections required).`,
    keyIssues: [
      `Typeface: "Inter ExtraBold" is not on the approved list (required: Space Grotesk 700)`,
      `Logo position: top-right (required: bottom-left, min 8% canvas width clearance)`,
      `Tagline contrast ratio: 3.2:1 — fails WCAG AA (required: ≥4.5:1)`,
    ],
    recommendation: `Swap to Space Grotesk, move logo to brand-mandated position, increase tagline contrast to #FFFFFFCC on the dark background.`,
  };
  const marketerVote: CriticVote = {
    critic: 'marketer',
    verdict: 'approve',
    score: 82,
    reasoning: `Strong CTR signals. The product occupies 40% canvas area with clear z-index priority — above-fold focal point is compelling. The CTA ("Shop Now — 30% Off") uses direct-response copywriting (urgency + discount) and is positioned in the golden ratio hotspot. Predicted CTR uplift: +18–24% vs. category baseline based on the performance model's historical pattern recognition for ${brief.platform}.`,
    keyIssues: [
      `CTA button contrast is excellent — no issues`,
      `Headline character count: 28 chars — optimal for ${brief.platform} truncation`,
    ],
    recommendation: `Add a secondary micro-CTA ("Free returns") below the main CTA to reduce purchase friction. This pattern increased conversion +7% in last 3 A/B tests in sports apparel vertical.`,
  };
  const noveltyVote: CriticVote = {
    critic: 'novelty',
    verdict: 'approve',
    score: 74,
    reasoning: `Cosine distance from the brand's last 12 approved concepts: 0.71 (above the 0.65 novelty floor). The "duotone product on dark gradient" composition is distinctive vs. competitors' predominantly flat/white-background ads scraped from Meta Ad Library this week. However, the headline structure "VERB + BRAND + EMOJI" matches 3 of our archived outputs — flagging for possible copycat drift.`,
    keyIssues: [
      `Headline structure "VERB BRAND EMOJI" detected in 3 prior outputs — reduce template dependency`,
      `Competitor gap opportunity: no rival in vertical is using kinetic text treatment this quarter`,
    ],
    recommendation: `Introduce a typographic motion element (kinetic headline) or an asymmetric crop to increase distinctiveness score above 0.80 threshold.`,
  };

  const consensusScore = Math.round((puristVote.score + marketerVote.score + noveltyVote.score) / 3);

  return {
    id: crypto.randomUUID(),
    concept: conceptName,
    votes: [puristVote, marketerVote, noveltyVote],
    directorSynthesis: `Two of three critics approve. The Brand-Purist's Class A violations (typeface + logo placement) are blocking issues and must be resolved — these are non-negotiable per brand contract. The Marketer's recommendation to add a micro-CTA is high-value and low-risk; integrate it. The Novelty critic's kinetic text suggestion is deferred to iteration 2. Verdict: iterate on brand compliance issues, then re-evaluate. The core concept strategy is sound.`,
    finalVerdict: 'iterated',
    consensusScore,
    debateLog: [
      { speaker: 'Brand-Purist Critic', line: `The typeface is wrong. Full stop. Space Grotesk 700 is a contractual requirement — I'm flagging this as blocking.` },
      { speaker: 'Performance-Marketer Critic', line: `Agreed on typeface. But the CTR signals are exceptional. Let's not throw the baby out with the bathwater — the layout and CTA placement is the best we've seen in 6 iterations.` },
      { speaker: 'Novelty Critic', line: `I concur. The structural composition is genuinely distinct from competitive creatives. The typeface is a quick fix. My concern is the headline template reuse — we're at 3 instances now.` },
      { speaker: 'Brand-Purist Critic', line: `Fine. I'll agree to amend rather than reject, IF we get a commitment to fix logo position in the same pass. That's Rule 2.3 of the brand guide — mandatory.` },
      { speaker: 'Performance-Marketer Critic', line: `Logo position is fine by me — it's a brand call. I want to add a micro-CTA below the primary. Historical data shows +7% CVR in this pattern.` },
      { speaker: 'Novelty Critic', line: `Seconded. Proceeding to Director synthesis. My amendment: flag headline template for iteration 2.` },
      { speaker: 'Creative Director', line: `Synthesis complete. Approved for iteration with corrections: (1) Space Grotesk typeface, (2) logo bottom-left, (3) micro-CTA added, (4) headline template variation noted for next run.` },
    ],
  };
}

function buildEvalScores(brief: BriefData): EvalScores {
  const base = Math.random() * 20;
  return {
    brandFit: Math.round(65 + base + (brief.files.length * 3)),
    novelty: Math.round(70 + (Math.random() * 15)),
    predictedPerformance: Math.round(72 + base),
    overallScore: 0, // computed below
    breakdown: {
      brandFitReason: `Embedding similarity to uploaded brand corpus (${brief.files.length} files): 0.81 cosine distance. Color palette overlap: 91%. Tone match: High (brand uses "${brief.tone}" voice in 78% of approved assets).`,
      noveltyReason: `Cosine distance from last 12 approved concepts: 0.71. Distinctiveness vs. 34 competitor ads scraped from Meta Ad Library: High. Detected potential template reuse in headline structure — minor flag.`,
      predictedPerfReason: `Lightweight regression model (trained on 2.3k historical ad performance records) predicts CTR in top quartile for ${brief.platform}. Strong product-dominant composition is a top-3 predictor for this vertical.`,
    },
  };
}

function buildRationale(brief: BriefData): RationaleTrace {
  const brandName = brief.brandName.split(' - ')[0];
  return {
    conceptName: `${brandName} — Bold ${brief.tone} Hero`,
    platform: brief.platform,
    headline: `MOVE BOLD. BE ${brandName.toUpperCase()}.`,
    tagline: `Performance activewear engineered for those who don't stop.`,
    colorPalette: ['#7C3AED', '#0F172A', '#A78BFA', '#F1F5F9'],
    layoutDescription: `Product hero image (40% canvas, centered) on dark gradient background. Headline top-left, bold 72px. CTA button bottom-center with secondary micro-CTA beneath. ${brandName} logo bottom-left per brand guide rule 2.3.`,
    decisions: [
      {
        decision: `Use Space Grotesk 700 as primary typeface`,
        rule: `Rule 1.2: All digital assets must use approved typeface stack (Space Grotesk 700 primary, Outfit 400 secondary)`,
        ruleSource: `${brandName} Brand Book v3.1 — Typography`,
        confidence: 99,
      },
      {
        decision: `Dark gradient background (#0F172A → #1E1B4B)`,
        rule: `Rule 3.1: Performance ad formats must use high-contrast backgrounds to maximize product pop`,
        ruleSource: `${brandName} Ad Creative Guidelines — Format Standards`,
        confidence: 91,
      },
      {
        decision: `CTA text: "Shop Now — 30% Off" in #FFFFFF on violet button`,
        rule: `Performance pattern: Direct-response CTAs with urgency + discount outperform generic "Learn More" by 22% in sports vertical`,
        ruleSource: `Performance-Marketer Critic recommendation + historical CTR model`,
        confidence: 84,
      },
      {
        decision: `Logo at bottom-left, 8% canvas width clearance`,
        rule: `Rule 2.3: Logo placement must be bottom-left or bottom-right on landscape/square formats with minimum clear space`,
        ruleSource: `${brandName} Brand Book v3.1 — Logo Usage`,
        confidence: 100,
      },
      {
        decision: `Product occupies 40% of canvas area with highest z-index`,
        rule: `Market Signal: Product-dominant compositions outperform lifestyle-dominant by 18% on ${brief.platform} this quarter per Meta Ad Library analysis`,
        ruleSource: `Market Signal Agent — Weekly Hypothesis Feed`,
        confidence: 78,
      },
    ],
    hanlonReframe: brief.tone.includes('Futuristic') || brief.tone.includes('Bold')
      ? `Previous feedback flagged as "too dark" was re-analyzed via Hanlon's Razor: the stakeholder's device had a miscalibrated display (auto-brightness at 40%). The dark gradient is correct for the brief — not a design error but a viewing-environment mismatch. Design retained as-is.`
      : null,
    competitorGap: `Meta Ad Library scan (last 7 days, sports apparel, US+UK): 84% of competitor ads use flat white backgrounds with studio photography. Zero competitors are using dark-gradient + kinetic-type treatment. This creates a strong pattern interrupt for the target audience — estimated attention uplift +2.1s view-time based on eye-tracking benchmark data.`,
    suggestedIterations: [
      `Iteration A (Novelty): Replace static headline with typographic motion (CSS animation) — estimated +0.09 distinctiveness score`,
      `Iteration B (Performance): A/B test "30% Off" vs "Free Next-Day Delivery" in CTA — Marketer Critic flags delivery incentive as stronger motivator for repeat purchasers`,
      `Iteration C (Localization): Spawn Localization Agent to produce UK/AUS variants with regional copy and currency formatting`,
      `Iteration D (Format): Spawn Motion Agent to generate a 15-second video variant from this static concept for Reels/TikTok`,
    ],
  };
}

// ─── MAIN SIMULATION FUNCTION ─────────────────────────────────────────────────
export async function runAgentSimulation(
  brief: BriefData,
  onStep: (step: SimStep) => void
): Promise<void> {
  const ts = () => new Date().toLocaleTimeString('en-US', { hour12: false });

  const steps: SimStep[] = [
    // 1: Director boots up
    {
      delayMs: 300,
      activeAgent: 'director',
      logEntry: {
        agentName: 'System',
        role: 'Orchestrator',
        message: `Pipeline initialized. Brief received: "${brief.brandName}" for ${brief.platform}. ${brief.files.length} brand asset(s) loaded into RAG context.`,
        status: 'done',
        timestamp: ts(),
      },
    },
    {
      delayMs: 800,
      activeAgent: 'director',
      logEntry: {
        agentName: 'Creative Director',
        role: 'Director Agent',
        message: `Analyzing brief & brand context... Tone: ${brief.tone}. Platform constraints loaded. Checking Market Signal Agent feed for live competitor hypotheses.`,
        status: 'thinking',
        timestamp: ts(),
      },
    },
    // 2: Market Signal Agent fires
    {
      delayMs: 1200,
      activeAgent: 'director',
      spawnedAgents: ['Market Signal'],
      logEntry: {
        agentName: 'Creative Director',
        role: 'Director Agent',
        message: `Spawning Market Signal Agent. Querying Meta Ad Library + platform trend index for ${brief.platform.split(' ')[0]} in sports apparel vertical...`,
        status: 'thinking',
        timestamp: ts(),
      },
    },
    {
      delayMs: 1800,
      activeAgent: 'director',
      logEntry: {
        agentName: 'Market Signal Agent',
        role: 'Spawned Sub-Agent',
        message: `Hypothesis confirmed: Dark-gradient + product-dominant compositions have 0% adoption by top-10 competitors this week (scanned 147 live ads). Pattern interrupt opportunity is HIGH. CTR prediction model rates this gap at 0.84 confidence. Feeding to Director brief.`,
        status: 'done',
        timestamp: ts(),
      },
    },
    // 3: Director → Designer handoff
    {
      delayMs: 900,
      activeAgent: 'designer',
      logEntry: {
        agentName: 'Creative Director',
        role: 'Director Agent',
        message: `Market signal integrated. Handing enriched brief to Senior Designer Agent. Key constraint: exploit dark-gradient gap. Must use ${brief.tone} tone architecture.`,
        status: 'done',
        timestamp: ts(),
      },
    },
    {
      delayMs: 1400,
      activeAgent: 'designer',
      logEntry: {
        agentName: 'Senior Designer',
        role: 'Designer Agent',
        message: `Generating concept architecture: hero product shot (40% canvas), Space Grotesk 700 headline, dark gradient background, violet primary CTA, bottom-left logo per brand rule 2.3. Composing layout decision tree...`,
        status: 'thinking',
        timestamp: ts(),
      },
    },
    // 4: Persona Simulation runs
    {
      delayMs: 1600,
      activeAgent: 'designer',
      spawnedAgents: ['Market Signal', 'Persona Simulation'],
      logEntry: {
        agentName: 'Senior Designer',
        role: 'Designer Agent',
        message: `Spawning Persona Simulation Agent. Running concept past 3 target audience personas (18–25 fitness enthusiast, 26–35 urban professional, gym owner) before escalating to Critic Panel...`,
        status: 'thinking',
        timestamp: ts(),
      },
    },
    {
      delayMs: 2200,
      activeAgent: 'designer',
      logEntry: {
        agentName: 'Persona Simulation Agent',
        role: 'Spawned Sub-Agent',
        message: `Persona 1 (18–25 fitness): "Bold, feels premium. Would stop scrolling." — PASS\nPersona 2 (26–35 professional): "Strong product focus. CTA is clear." — PASS\nPersona 3 (gym owner): "Price point not communicated early enough." — FLAG\nRecommendation: Add price anchor or discount signal in top 30% of canvas.`,
        status: 'done',
        timestamp: ts(),
      },
    },
    // 5: Adversarial Critic Panel
    {
      delayMs: 900,
      activeAgent: 'purist',
      logEntry: {
        agentName: 'Senior Designer',
        role: 'Designer Agent',
        message: `Persona simulation complete. Concept updated: added "30% Off" discount signal in upper-right. Escalating to Adversarial Critique Panel for structured debate...`,
        status: 'done',
        timestamp: ts(),
      },
    },
    {
      delayMs: 1100,
      activeAgent: 'purist',
      logEntry: {
        agentName: 'Brand-Purist Critic',
        role: 'Critic Panel',
        message: `Initiating brand compliance audit. Checking: typeface (Space Grotesk 700 required), logo placement (rule 2.3), color palette, contrast ratios (WCAG AA), clear space rules...`,
        status: 'thinking',
        timestamp: ts(),
      },
    },
    {
      delayMs: 1400,
      activeAgent: 'marketer',
      logEntry: {
        agentName: 'Performance-Marketer Critic',
        role: 'Critic Panel',
        message: `Running CTR prediction model. Evaluating: CTA placement, headline character count, product-to-canvas ratio, directional cues, urgency signals, AIDA structure...`,
        status: 'thinking',
        timestamp: ts(),
      },
    },
    {
      delayMs: 1400,
      activeAgent: 'novelty',
      logEntry: {
        agentName: 'Novelty Critic',
        role: 'Critic Panel',
        message: `Computing embedding distance from last 12 approved concepts and 147 competitor ads. Checking for template reuse patterns, genericness indicators, and competitor parity...`,
        status: 'thinking',
        timestamp: ts(),
      },
    },
    // 6: Debate + Synthesis
    {
      delayMs: 1800,
      activeAgent: 'director',
      logEntry: {
        agentName: 'Critic Panel',
        role: 'Multi-Agent Debate',
        message: `All critics have voted. Initiating structured debate protocol. Brand-Purist: AMEND (68). Performance-Marketer: APPROVE (82). Novelty: APPROVE (74). Conflict detected — escalating to Director for synthesis...`,
        status: 'done',
        timestamp: ts(),
      },
      debateRound: buildDebateRound(brief),
    },
    // 7: Director synthesizes
    {
      delayMs: 1200,
      activeAgent: 'director',
      logEntry: {
        agentName: 'Creative Director',
        role: 'Director Agent',
        message: `Synthesis complete. Directing iteration: (1) typeface → Space Grotesk 700, (2) logo → bottom-left per rule 2.3, (3) micro-CTA added below primary. Concept approved-with-amendments. Generating rationale trace and eval scores...`,
        status: 'done',
        timestamp: ts(),
      },
    },
    // 8: Eval harness runs
    {
      delayMs: 1000,
      activeAgent: null,
      logEntry: {
        agentName: 'System',
        role: 'Eval Harness',
        message: `Running evaluation harness on final concept. Scoring: Brand Fit (embedding similarity), Novelty (distance score), Predicted Performance (CTR regression model)...`,
        status: 'thinking',
        timestamp: ts(),
      },
    },
    {
      delayMs: 1600,
      activeAgent: null,
      logEntry: {
        agentName: 'System',
        role: 'Eval Harness',
        message: `Evaluation complete. Scores logged. XDR trace generated. Asset ready for HITL review (confidence-weighted: HIGH confidence → auto-queue for approval).`,
        status: 'done',
        timestamp: ts(),
      },
    },
  ];

  for (const step of steps) {
    await new Promise((r) => setTimeout(r, step.delayMs));
    onStep(step);
  }

  // Final: build & emit eval scores and rationale
  const evalScores = buildEvalScores(brief);
  evalScores.overallScore = Math.round((evalScores.brandFit + evalScores.novelty + evalScores.predictedPerformance) / 3);
  const rationale = buildRationale(brief);

  const historyEntry: HistoricalEntry = {
    id: crypto.randomUUID(),
    conceptName: rationale.conceptName,
    timestamp: new Date().toLocaleTimeString('en-US'),
    scores: evalScores,
    status: 'iterated',
  };

  onStep({ delayMs: 0, evalScores, rationale, historyEntry });
}
