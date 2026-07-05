import type { AgentLog, DebateRound, CriticVote, EvalScores, HistoricalEntry, RationaleTrace, BriefData } from './types';

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

const API_BASE = 'http://localhost:8000/v1';

export async function runAgentSimulation(
  brief: BriefData,
  onStep: (step: SimStep) => void
): Promise<void> {
  const ts = () => new Date().toLocaleTimeString('en-US', { hour12: false });
  
  // 1. Ensure brand exists, or create a mock brand ID for now if we haven't implemented full brand management in UI
  let brandId = 'b0000000-0000-0000-0000-000000000000'; // Default test brand
  
  try {
    // Try to create the brand
    const brandRes = await fetch(`${API_BASE}/brands`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        name: brief.brandName,
        description: 'Frontend generated brand'
      })
    });
    
    if (brandRes.ok) {
      const data = await brandRes.json();
      brandId = data.brand_id;
    } else if (brandRes.status === 400) {
      // Already exists, just use a dummy or try to fetch (Backend doesn't have list brands yet, so we'll just ignore for now and assume the mock brand is fine or handle it properly if we had a get brand by name)
    }
  } catch (e) {
    console.warn("Failed to create brand, using test UUID", e);
  }

  // 2. Submit the brief to create a job
  let jobId = '';
  try {
    const res = await fetch(`${API_BASE}/jobs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        brand_id: brandId,
        brief: brief.brief,
        platform: brief.platform,
        tone: brief.tone,
        uploaded_asset_keys: []
      })
    });
    
    if (!res.ok) {
      throw new Error(`Failed to create job: ${await res.text()}`);
    }
    
    const data = await res.json();
    jobId = data.job_id;
  } catch (err: any) {
    onStep({
      delayMs: 0,
      error: err.message,
      logEntry: { agentName: 'System', role: 'Error', message: err.message, status: 'error', timestamp: ts() }
    });
    return;
  }

  // 3. Connect to SSE Stream
  return new Promise((resolve, reject) => {
    const eventSource = new EventSource(`${API_BASE}/jobs/${jobId}/stream`);

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log("SSE Event:", data);

      if (data.event === 'connected') {
        onStep({
          delayMs: 0,
          logEntry: { agentName: 'System', role: 'Orchestrator', message: `Connected to pipeline. Job ID: ${jobId}`, status: 'done', timestamp: ts() }
        });
        return;
      }

      // Handle normal status messages
      if (data.status) {
        // Map backend state to frontend visualizer
        onStep({
          delayMs: 0,
          logEntry: {
            agentName: data.agent || 'System',
            role: 'Agent',
            message: `Status: ${data.status} ${data.message ? '- ' + data.message : ''}`,
            status: data.status === 'error' ? 'error' : 'done',
            timestamp: ts()
          },
          activeAgent: data.agent,
        });

        if (data.status === 'complete' || data.status === 'error') {
          eventSource.close();
          
          if (data.status === 'complete') {
            // Fetch final job data
            fetch(`${API_BASE}/jobs/${jobId}`)
              .then(res => res.json())
              .then(jobData => {
                onStep({
                  delayMs: 0,
                  generatedImageUrl: jobData.generated_image_url,
                  evalScores: jobData.eval_scores,
                  rationale: jobData.rationale,
                  logEntry: {
                    agentName: 'System',
                    role: 'Complete',
                    message: `Job complete. Image URL: ${jobData.generated_image_url}`,
                    status: 'done',
                    timestamp: ts()
                  }
                });
              });
          }
          resolve();
        }
      }
    };

    eventSource.onerror = (err) => {
      console.error("EventSource failed:", err);
      eventSource.close();
      resolve(); // or reject
    };
  });
}
