import type { AgentLog, DebateRound, EvalScores, HistoricalEntry, RationaleTrace, BriefData } from './types';

// ─── STEP TYPES ──────────────────────────────────────────────────────────────
export interface SimStep {
  delayMs: number;
  logEntry?: AgentLog;
  activeAgent?: string | null;
  spawnedAgents?: string[];
  debateRound?: DebateRound;
  evalScores?: EvalScores;
  rationale?: RationaleTrace;
  historyEntry?: HistoricalEntry;
  generatedImageUrl?: string;
  error?: string;
}

const API_BASE = `${import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'}/v1`;

async function authorizedFetch(path: string, token: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  headers.set('Authorization', `Bearer ${token}`);
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (response.status === 401) {
    sessionStorage.removeItem('access_token');
    window.location.assign('/login');
  }
  return response;
}

export async function runAgentSimulation(
  brief: BriefData,
  onStep: (step: SimStep) => void
): Promise<void> {
  const ts = () => new Date().toLocaleTimeString('en-US', { hour12: false });
  const token = sessionStorage.getItem('access_token');

  const reportError = (error: unknown) => {
    const message = error instanceof Error ? error.message : 'An unexpected API error occurred.';
    onStep({
      delayMs: 0,
      error: message,
      logEntry: { agentName: 'System', role: 'Error', message, status: 'error', timestamp: ts() },
    });
  };

  if (!token) {
    reportError(new Error('Your session has expired. Please sign in again.'));
    return;
  }

  try {
    const brandRes = await authorizedFetch('/brands', token, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        name: brief.brandName,
        description: 'Frontend generated brand'
      })
    });

    if (!brandRes.ok) {
      const body = await brandRes.json().catch(() => null);
      throw new Error(body?.detail ?? `Brand creation failed (${brandRes.status}).`);
    }
    const brand = await brandRes.json();

    const jobResponse = await authorizedFetch('/jobs', token, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        brand_id: brand.brand_id,
        brief: brief.prompt,
        platform: brief.platform,
        tone: brief.tone,
        uploaded_asset_keys: []
      })
    });

    if (!jobResponse.ok) {
      const body = await jobResponse.json().catch(() => null);
      throw new Error(body?.detail ?? `Job creation failed (${jobResponse.status}).`);
    }
    const job = await jobResponse.json();

    const streamResponse = await authorizedFetch(`/jobs/${job.job_id}/stream`, token, {
      headers: { Accept: 'text/event-stream' },
    });
    if (!streamResponse.ok || !streamResponse.body) {
      const body = await streamResponse.json().catch(() => null);
      throw new Error(body?.detail ?? `Progress stream failed (${streamResponse.status}).`);
    }

    const reader = streamResponse.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let finished = false;

    while (!finished) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      const frames = buffer.split(/\r?\n\r?\n/);
      buffer = frames.pop() ?? '';

      for (const frame of frames) {
        const eventData = frame.split(/\r?\n/).find(line => line.startsWith('data:'))?.slice(5).trim();
        if (!eventData) continue;

        const data = JSON.parse(eventData) as {
          event?: string;
          status?: string;
          agent?: string;
          message?: string;
        };

        if (data.event === 'connected') {
          onStep({
            delayMs: 0,
            logEntry: {
              agentName: 'System', role: 'Orchestrator',
              message: `Connected to pipeline. Job ID: ${job.job_id}`,
              status: 'done', timestamp: ts(),
            },
          });
          continue;
        }

        if (data.status) {
          onStep({
            delayMs: 0,
            logEntry: {
              agentName: data.agent || 'System',
              role: 'Agent',
              message: `Status: ${data.status}${data.message ? ` - ${data.message}` : ''}`,
              status: data.status === 'error' ? 'error' : 'done',
              timestamp: ts(),
            },
            activeAgent: data.agent,
          });
        }

        if (data.status === 'complete') {
          const resultResponse = await authorizedFetch(`/jobs/${job.job_id}`, token);
          if (!resultResponse.ok) throw new Error(`Could not load job result (${resultResponse.status}).`);
          const result = await resultResponse.json();
          onStep({
            delayMs: 0,
            generatedImageUrl: result.generated_image_url,
            evalScores: result.eval_scores,
            rationale: result.rationale,
            logEntry: {
              agentName: 'System', role: 'Complete',
              message: 'Job complete.', status: 'done', timestamp: ts(),
            },
          });
          finished = true;
        } else if (data.status === 'error') {
          throw new Error(data.message ?? 'The generation pipeline failed.');
        }
      }

      if (done) finished = true;
    }
  } catch (error) {
    reportError(error);
  }
}
