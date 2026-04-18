'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Mic, MicOff, Send } from 'lucide-react';

import { PageShell } from '@/components/layout/page-shell';
import { apiClient } from '@/lib/api-client';
import type { AssistantChatEnvelope, AssistantOrchestratorResponse } from '@/types/assistant';

type StatusKind = 'idle' | 'busy' | 'ok' | 'error';

interface QueryTurn {
  id: string;
  query: string;
  answer: string;
  error?: string;
  createdAt: string;
  trace: {
    route: string;
    queryType?: string;
    agentsUsed: string[];
    resourcesUsed: string[];
  };
}

const FIXED_USER_ID = 'default';
const VOICE_LANGUAGE = 'en-IN';

const styles = `
.assistant-canvas {
  display: grid;
  grid-template-columns: minmax(320px, 35%) minmax(0, 65%);
  gap: 18px;
  align-items: stretch;
  min-height: calc(100vh - 220px);
}

.assistant-pane {
  border: 1px solid var(--border);
  border-radius: 16px;
  background: var(--bg2);
  box-shadow: 0 18px 36px rgba(2, 6, 23, 0.3);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.assistant-pane.response-pane {
  height: calc(100vh - 220px);
}

.assistant-pane-head {
  padding: 16px;
  border-bottom: 1px solid var(--border);
}

.assistant-pane-title {
  margin: 0;
  font-size: 1.2rem;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.assistant-pane-body {
  padding: 16px;
  display: grid;
  gap: 12px;
  flex: 1;
  min-height: 0;
  align-content: start;
  grid-auto-rows: max-content;
}

.assistant-pane.response-pane .assistant-pane-body {
  overflow-y: auto;
  align-content: start;
  overscroll-behavior: contain;
  color: #111827;
}

.assistant-field {
  display: grid;
  gap: 6px;
}

.assistant-field label {
  font-size: 0.96rem;
  font-weight: 700;
  color: var(--muted);
}

.assistant-textarea {
  min-height: 170px;
  resize: vertical;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--bg3);
  color: var(--text);
  padding: 12px;
  font-family: inherit;
  font-size: 1.04rem;
  outline: none;
}

.assistant-textarea:focus {
  border-color: var(--indigo);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.22);
}

.assistant-actions {
  display: grid;
  grid-template-columns: 44px 1fr auto;
  gap: 8px;
  align-items: stretch;
}

.assistant-btn {
  border: 1px solid transparent;
  border-radius: 10px;
  min-height: 40px;
  padding: 0 14px;
  font-family: inherit;
  font-weight: 700;
  font-size: 1.02rem;
  cursor: pointer;
  transition: transform 120ms ease, opacity 120ms ease;
}

.assistant-btn:hover:not(:disabled) {
  transform: translateY(-1px);
}

.assistant-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.assistant-btn.primary {
  background: var(--indigo);
  color: #eef2ff;
}

.assistant-btn.secondary {
  background: var(--bg3);
  border-color: var(--border);
  color: var(--text);
}

.assistant-btn.icon {
  min-width: 42px;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #7c3aed;
  color: #f5f3ff;
}

.assistant-btn.icon.recording {
  background: #f97316;
  color: #1f1300;
}

.assistant-features {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.assistant-feature-chip {
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--bg3);
  color: var(--muted);
  font-size: 0.9rem;
  padding: 5px 10px;
}

.assistant-status {
  margin: 0;
  font-size: 0.87rem;
  color: var(--muted);
}

.assistant-status.busy {
  color: #f59e0b;
}

.assistant-status.ok {
  color: var(--emerald);
}

.assistant-status.error {
  color: var(--rose);
}

.results-empty {
  margin: 0;
  color: #111827;
  font-size: 1.03rem;
}

.turn-list {
  display: grid;
  gap: 16px;
}

.turn-item {
  border-bottom: 1px solid var(--border);
  padding: 2px 0 14px;
}

.turn-item:last-child {
  border-bottom: none;
  padding-bottom: 4px;
}

.turn-time {
  margin: 0 0 6px;
  color: #4b5563;
  font-size: 0.9rem;
}

.turn-query,
.turn-answer {
  margin: 0 0 8px;
  line-height: 1.55;
  font-size: 1.05rem;
}

.turn-query {
  color: #1d4ed8;
  white-space: pre-wrap;
}

.turn-answer {
  color: #111827;
  white-space: normal;
}

.turn-answer.markdown {
  white-space: normal;
}

.turn-answer.error {
  color: var(--rose);
}

.turn-answer.markdown p {
  margin: 0 0 4px;
}

.turn-answer.markdown p:last-child {
  margin-bottom: 0;
}

.turn-answer.markdown ul,
.turn-answer.markdown ol {
  margin: 0 0 4px 18px;
  padding: 0;
}

.turn-answer.markdown li {
  margin: 0 0 4px;
}

.turn-answer.markdown code {
  background: rgba(148, 163, 184, 0.16);
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 6px;
  padding: 1px 5px;
  font-size: 0.84em;
}

.turn-answer.markdown pre {
  margin: 0 0 5px;
  padding: 10px;
  background: rgba(2, 6, 23, 0.6);
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: auto;
}

.turn-answer.markdown pre code {
  background: transparent;
  border: none;
  padding: 0;
}

.turn-answer.markdown a {
  color: #a5b4fc;
  text-decoration: underline;
}

.turn-trace {
  margin: 0 0 2px;
  color: #374151;
  font-size: 0.9rem;
  line-height: 1.5;
}

@media (max-width: 1080px) {
  .assistant-canvas {
    grid-template-columns: 1fr;
    min-height: auto;
  }

  .assistant-pane.response-pane {
    height: 58vh;
  }

  .assistant-pane.response-pane .assistant-pane-body {
    max-height: none;
  }

  .assistant-actions {
    grid-template-columns: 44px 1fr;
  }

  .assistant-actions .assistant-btn.secondary {
    grid-column: 1 / -1;
  }
}
`;

function normalizeChatEnvelope(payload: unknown): AssistantChatEnvelope {
  if (payload && typeof payload === 'object') {
    const value = payload as Record<string, unknown>;
    if ('answered' in value || 'response' in value || 'error' in value) {
      return value as AssistantChatEnvelope;
    }
    if (value.data && typeof value.data === 'object') {
      return value.data as AssistantChatEnvelope;
    }
  }
  return {};
}

async function readErrorPayload(response: Response): Promise<string> {
  const text = await response.text();
  try {
    const parsed = JSON.parse(text);
    if (parsed?.detail) {
      return typeof parsed.detail === 'string' ? parsed.detail : JSON.stringify(parsed.detail);
    }
    return JSON.stringify(parsed);
  } catch {
    return text || `Request failed with status ${response.status}`;
  }
}

function deriveFallbackTrace(response: AssistantOrchestratorResponse): QueryTurn['trace'] {
  const route = String(response.capability || 'general');
  const capabilityResult =
    response.capability_result && typeof response.capability_result === 'object'
      ? response.capability_result
      : {};
  const nested =
    capabilityResult &&
    typeof capabilityResult === 'object' &&
    'result' in capabilityResult &&
    (capabilityResult as Record<string, unknown>).result &&
    typeof (capabilityResult as Record<string, unknown>).result === 'object'
      ? ((capabilityResult as Record<string, unknown>).result as Record<string, unknown>)
      : (capabilityResult as Record<string, unknown>);

  const queryType = typeof nested.query_type === 'string' ? nested.query_type : undefined;
  const resourcesByRoute: Record<string, string[]> = {
    bookkeeping: ['transactions', 'bookkeeping_entries'],
    deadline: ['deadlines', 'compliance_calendar'],
    report: ['profiles', 'reports', 'transactions'],
    general: ['transactions', 'deadlines'],
  };

  return {
    route,
    queryType,
    agentsUsed: [`${route}_capability`, 'synthesize_response'],
    resourcesUsed: resourcesByRoute[route] || ['transactions'],
  };
}

function compactQueryText(value: string): string {
  return value.replace(/\s+/g, ' ').trim();
}

function compactAnswerText(value: string): string {
  return value
    .replace(/\r\n/g, '\n')
    .replace(/[ \t]+$/gm, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

function buildTurnFromResponse(query: string, response: AssistantOrchestratorResponse, error?: string): QueryTurn {
  const tracePayload = response.trace;
  const fallback = deriveFallbackTrace(response);

  const route = typeof tracePayload?.route === 'string' ? tracePayload.route : fallback.route;
  const queryType = typeof tracePayload?.query_type === 'string' ? tracePayload.query_type : fallback.queryType;
  const agentsUsed = Array.isArray(tracePayload?.agents_used) && tracePayload?.agents_used.length
    ? tracePayload.agents_used.map((item) => String(item))
    : fallback.agentsUsed;
  const resourcesUsed = Array.isArray(tracePayload?.resources_used) && tracePayload?.resources_used.length
    ? tracePayload.resources_used.map((item) => String(item))
    : fallback.resourcesUsed;

  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    query: compactQueryText(query) || query.trim(),
    answer: compactAnswerText(String(response.agent_response || '')) || 'No output returned.',
    error,
    createdAt: new Date().toISOString(),
    trace: {
      route,
      queryType,
      agentsUsed,
      resourcesUsed,
    },
  };
}

function formatTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export default function AssistantPage() {
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState<{ text: string; kind: StatusKind }>({ text: 'Ready', kind: 'ok' });
  const [turns, setTurns] = useState<QueryTurn[]>([]);

  const [isSending, setIsSending] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);

  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const voiceApiBase = `${(process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '')}/voice-agent`;
  const markdown = useMemo(() => {
    const MarkdownItRuntime = require('markdown-it');
    const parser = new MarkdownItRuntime({
      html: false,
      breaks: true,
      linkify: true,
      typographer: true,
    });
    return parser;
  }, []);

  const setStatusMessage = useCallback((text: string, kind: StatusKind = 'idle') => {
    setStatus({ text, kind });
  }, []);

  const releaseRecorder = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    recorderRef.current = null;
  }, []);

  const transcribeVoiceBlob = useCallback(
    async (blob: Blob) => {
      if (blob.size < 1024) {
        setStatusMessage('No speech detected. Please try again.', 'error');
        return;
      }

      setIsTranscribing(true);
      setStatusMessage('Transcribing voice query...', 'busy');

      try {
        const file = new File([blob], 'assistant-query.webm', { type: blob.type || 'audio/webm' });
        const formData = new FormData();
        formData.append('file', file);
        formData.append('language_code', VOICE_LANGUAGE);
        formData.append('model', 'saaras:v3');
        formData.append('mode', 'transcribe');

        const sttResponse = await fetch(`${voiceApiBase}/stt/transcribe`, {
          method: 'POST',
          body: formData,
        });

        if (!sttResponse.ok) {
          throw new Error(await readErrorPayload(sttResponse));
        }

        const sttData = await sttResponse.json();
        const transcript = String(sttData?.transcript || '').trim();

        if (!transcript) {
          setStatusMessage('Transcription is empty. Try once more.', 'error');
          return;
        }

        setQuery((prev) => (prev.trim() ? `${prev.trim()}\n${transcript}` : transcript));
        setStatusMessage('Voice text added to your query.', 'ok');
      } catch (error: unknown) {
        const message = error instanceof Error ? error.message : 'Voice transcription failed.';
        setStatusMessage(message, 'error');
      } finally {
        setIsTranscribing(false);
      }
    },
    [setStatusMessage, voiceApiBase]
  );

  const startVoiceCapture = useCallback(async () => {
    if (isRecording || isTranscribing) {
      return;
    }

    if (!window.isSecureContext) {
      setStatusMessage('Microphone needs localhost or HTTPS secure context.', 'error');
      return;
    }

    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setStatusMessage('This browser does not support voice capture.', 'error');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];

      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/webm')
          ? 'audio/webm'
          : '';

      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      recorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        const recordedChunks = [...chunksRef.current];
        chunksRef.current = [];
        releaseRecorder();
        const recordedBlob = new Blob(recordedChunks, { type: mimeType || 'audio/webm' });
        await transcribeVoiceBlob(recordedBlob);
      };

      recorder.start(250);
      setIsRecording(true);
      setStatusMessage('Listening...', 'busy');
    } catch (error: unknown) {
      releaseRecorder();
      const message = error instanceof Error ? error.message : 'Unable to access microphone.';
      setStatusMessage(message, 'error');
    }
  }, [isRecording, isTranscribing, releaseRecorder, setStatusMessage, transcribeVoiceBlob]);

  const stopVoiceCapture = useCallback(() => {
    if (!recorderRef.current || recorderRef.current.state !== 'recording') {
      return;
    }
    setIsRecording(false);
    setStatusMessage('Stopping capture...', 'busy');
    recorderRef.current.stop();
  }, [setStatusMessage]);

  const toggleVoiceCapture = useCallback(() => {
    if (isRecording) {
      stopVoiceCapture();
      return;
    }
    void startVoiceCapture();
  }, [isRecording, startVoiceCapture, stopVoiceCapture]);

  const runAssistantQuery = useCallback(async () => {
    const baseQuery = query.trim();
    if (!baseQuery) {
      setStatusMessage('Please enter a query first.', 'error');
      return;
    }

    setQuery('');

    setIsSending(true);
    setStatusMessage('Running assistant...', 'busy');

    try {
      const apiResponse = await apiClient.assistantChat({
        user_id: FIXED_USER_ID,
        message: baseQuery,
      });
      const envelope = normalizeChatEnvelope(apiResponse);

      if (!envelope.answered || !envelope.response) {
        throw new Error(envelope.error || 'Assistant did not return valid data.');
      }

      const turn = buildTurnFromResponse(baseQuery, envelope.response);
      setTurns((prev) => [turn, ...prev]);
      setStatusMessage('Response ready.', 'ok');
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Query execution failed.';
      const fallbackResponse: AssistantOrchestratorResponse = {
        user_id: FIXED_USER_ID,
        input_query: baseQuery,
        agent_response: message,
        capability: 'general',
      };
      const failedTurn = buildTurnFromResponse(baseQuery, fallbackResponse, message);
      setTurns((prev) => [failedTurn, ...prev]);
      setStatusMessage(message, 'error');
    } finally {
      setIsSending(false);
    }
  }, [query, setStatusMessage]);

  const clearAll = useCallback(() => {
    setQuery('');
    setStatusMessage('Ready', 'ok');
  }, [setStatusMessage]);

  useEffect(() => {
    return () => {
      releaseRecorder();
    };
  }, [releaseRecorder]);

  return (
    <PageShell
      title="Assistant"
      subtitle="Your AI finance assistant for bookkeeping, deadlines, and report guidance."
    >
      <style>{styles}</style>

      <div className="assistant-canvas">
        <section className="assistant-pane ask-pane" aria-labelledby="assistantInputTitle">
          <div className="assistant-pane-head">
            <h2 className="assistant-pane-title" id="assistantInputTitle">
              <Send size={15} /> Ask
            </h2>
          </div>

          <div className="assistant-pane-body">
            <div className="assistant-field">
              <label htmlFor="assistantQuery">Prompt</label>
              <textarea
                id="assistantQuery"
                className="assistant-textarea"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Example: show me the last 10 transactions"
              />
            </div>

            <div className="assistant-actions">
              <button
                className={`assistant-btn icon ${isRecording ? 'recording' : ''}`}
                type="button"
                onClick={toggleVoiceCapture}
                disabled={isSending || isTranscribing}
                aria-label={isRecording ? 'Stop recording' : 'Start recording'}
                title={isRecording ? 'Stop recording' : 'Start recording'}
              >
                {isRecording ? <MicOff size={16} /> : <Mic size={16} />}
              </button>
              <button
                className="assistant-btn primary"
                type="button"
                onClick={runAssistantQuery}
                disabled={isSending || isTranscribing}
              >
                <Send size={14} style={{ marginRight: 6 }} />
                {isSending ? 'Running...' : 'Run Query'}
              </button>
              <button
                className="assistant-btn secondary"
                type="button"
                onClick={clearAll}
                disabled={isSending || isRecording}
              >
                Clear
              </button>
            </div>

            <div className="assistant-features" aria-label="assistant features">
              <span className="assistant-feature-chip">Transaction Insights</span>
              <span className="assistant-feature-chip">Deadline Tracking</span>
              <span className="assistant-feature-chip">Report Guidance</span>
            </div>

            {(status.kind === 'busy' || status.kind === 'error') && (
              <p className={`assistant-status ${status.kind}`}>{status.text}</p>
            )}
          </div>
        </section>

        <section className="assistant-pane response-pane" aria-labelledby="assistantResultsTitle">
          <div className="assistant-pane-head">
            <h2 className="assistant-pane-title" id="assistantResultsTitle">Results</h2>
          </div>

          <div className="assistant-pane-body">
            {!turns.length ? (
              <p className="results-empty">Run a prompt to see your conversation history.</p>
            ) : (
              <div className="turn-list">
                {turns.map((turn) => {
                  const displayQuery = compactQueryText(turn.query || '');
                  const displayAnswer = compactAnswerText(turn.answer || '');

                  return (
                    <article key={turn.id} className="turn-item">
                      <p className="turn-time">{formatTime(turn.createdAt)}</p>
                      <p className="turn-query">{displayQuery}</p>
                      {turn.error ? (
                        <p className="turn-answer error">{displayAnswer}</p>
                      ) : (
                        <div
                          className="turn-answer markdown"
                          dangerouslySetInnerHTML={{ __html: markdown.render(displayAnswer) }}
                        />
                      )}

                      <p className="turn-trace">Agent Path: {turn.trace.route}</p>
                      {turn.trace.queryType && <p className="turn-trace">Query Type: {turn.trace.queryType}</p>}
                      <p className="turn-trace">Agents Used: {turn.trace.agentsUsed.join(', ')}</p>
                      <p className="turn-trace">Resources Used: {turn.trace.resourcesUsed.join(', ')}</p>
                    </article>
                  );
                })}
              </div>
            )}
          </div>
        </section>
      </div>
    </PageShell>
  );
}
