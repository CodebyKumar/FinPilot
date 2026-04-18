'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { PageShell } from '@/components/layout/page-shell';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

const styles = `
:root {
  --page: #f7f9fb;
  --ink: #171717;
  --muted: #5f6368;
  --line: #d7dde3;
  --panel: #ffffff;
  --teal: #0f766e;
  --teal-dark: #115e59;
  --rose: #be123c;
  --green: #15803d;
  --amber: #b45309;
  --shadow: 0 16px 40px rgba(23, 23, 23, 0.08);
}

.voice-assistant-container {
  display: grid;
  gap: 20px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  padding: 24px;
  background: var(--page);
}

.panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 14px;
  box-shadow: var(--shadow);
  overflow: hidden;
}

.panel-head {
  align-items: flex-start;
  border-bottom: 1px solid var(--line);
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 18px;
}

.panel-head h2 {
  margin: 0 0 6px;
  font-size: 1.25rem;
  color: var(--ink);
  font-weight: 700;
}

.panel-head p {
  margin: 0;
  line-height: 1.45;
  color: var(--muted);
  font-size: 0.9rem;
}

.tag {
  align-self: flex-start;
  border-radius: 8px;
  color: #ffffff;
  flex: 0 0 auto;
  font-size: 0.8rem;
  font-weight: 800;
  padding: 6px 9px;
  background: var(--teal);
}

.body {
  display: grid;
  gap: 16px;
  padding: 18px;
}

.agent-panel {
  grid-column: 1 / -1;
}

.agent-layout {
  display: grid;
  gap: 18px;
  grid-template-columns: minmax(260px, 0.72fr) minmax(0, 1.28fr);
}

.agent-controls {
  display: grid;
  gap: 16px;
  min-width: 0;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.button {
  border: 0;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 700;
  min-height: 44px;
  padding: 0 16px;
  transition: transform 120ms ease, background 120ms ease, opacity 120ms ease;
  font-family: inherit;
  font-size: 0.95rem;
}

.button:hover:not(:disabled) {
  transform: translateY(-1px);
}

.button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
  transform: none;
}

.button.primary {
  background: var(--teal);
  color: #ffffff;
}

.button.primary:hover:not(:disabled) {
  background: var(--teal-dark);
}

.button.secondary {
  background: #e8eef2;
  color: var(--ink);
}

.button.danger {
  background: var(--rose);
  color: #ffffff;
}

.conversation {
  display: grid;
  gap: 12px;
  max-height: 460px;
  min-height: 300px;
  overflow: auto;
  padding: 14px;
  background: #f3f6f8;
  border: 1px solid var(--line);
  border-radius: 8px;
}

.turn {
  background: #ffffff;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px;
}

.turn strong {
  display: block;
  font-size: 0.84rem;
  margin-bottom: 6px;
  font-weight: 700;
}

.turn.user strong {
  color: var(--rose);
}

.turn.assistant strong {
  color: var(--teal);
}

.turn p {
  line-height: 1.45;
  margin: 0;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
  color: var(--ink);
  font-size: 0.95rem;
}

.message {
  color: var(--muted);
  font-size: 0.94rem;
  min-height: 22px;
  padding: 8px 12px;
  background: #f3f6f8;
  border-radius: 6px;
}

.message.error {
  color: var(--rose);
  font-weight: 700;
  background: rgba(190, 18, 60, 0.1);
}

.message.ok {
  color: var(--green);
  font-weight: 700;
  background: rgba(21, 128, 61, 0.1);
}

.meter {
  background: #e8eef2;
  border-radius: 8px;
  height: 10px;
  overflow: hidden;
}

.meter span {
  background: var(--rose);
  display: block;
  height: 100%;
  transition: width 160ms ease;
  width: 0%;
}

.form-group {
  display: grid;
  gap: 8px;
}

.form-group label {
  color: var(--muted);
  display: block;
  font-size: 0.92rem;
  font-weight: 700;
}

.form-group select,
.form-group input {
  background: #ffffff;
  border: 1px solid var(--line);
  border-radius: 8px;
  color: var(--ink);
  outline: 0;
  padding: 11px 12px;
  font-family: inherit;
  font-size: 0.95rem;
}

.form-group select:focus,
.form-group input:focus {
  border-color: var(--teal);
  box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.14);
}

audio {
  width: 100%;
}

.controls-section {
  display: grid;
  gap: 12px;
}

@media (max-width: 920px) {
  .voice-assistant-container {
    grid-template-columns: 1fr;
  }
  
  .agent-layout {
    grid-template-columns: 1fr;
  }
}
`;

export default function AssistantPage() {
  // State management
  const [conversation, setConversation] = useState<Message[]>([]);
  const [status, setStatus] = useState('Idle');
  const [statusType, setStatusType] = useState<'' | 'error' | 'ok'>('');
  const [recording, setRecording] = useState(false);
  const [meterWidth, setMeterWidth] = useState(0);
  const [selectedLanguage, setSelectedLanguage] = useState('en-IN');
  const [turnSeconds, setTurnSeconds] = useState(6);

  // Refs for agent state
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const autoStopTimerRef = useRef<NodeJS.Timeout | null>(null);
  const meterTimerRef = useRef<NodeJS.Timeout | null>(null);
  const audioRefRef = useRef<HTMLAudioElement | null>(null);
  const conversationRef = useRef<HTMLDivElement | null>(null);

  // API configuration
  const apiOrigin =
    typeof window !== 'undefined'
      ? (new URLSearchParams(window.location.search).get('api_origin') ||
          (window.localStorage?.getItem('voiceApiOrigin') || '')) ||
        (window.location.origin.includes(':8000')
          ? window.location.origin
          : 'http://127.0.0.1:8000')
      : 'http://127.0.0.1:8000';

  const voiceApiBase = `${apiOrigin.replace(/\/$/, '')}/voice-agent`;

  // Utility functions
  const setMessage = useCallback((text: string, kind: '' | 'error' | 'ok' = '') => {
    setStatus(text);
    setStatusType(kind);
  }, []);

  const readError = async (response: Response): Promise<string> => {
    const text = await response.text();
    try {
      const data = JSON.parse(text);
      return data.detail ? JSON.stringify(data.detail, null, 2) : JSON.stringify(data, null, 2);
    } catch {
      return text || `${response.status} ${response.statusText}`;
    }
  };

  const base64ToAudioBlob = (audioBase64: string, format: string) => {
    const binary = atob(audioBase64);
    const chunks = [];
    for (let offset = 0; offset < binary.length; offset += 1024) {
      const slice = binary.slice(offset, offset + 1024);
      const bytes = new Uint8Array(slice.length);
      for (let i = 0; i < slice.length; i++) {
        bytes[i] = slice.charCodeAt(i);
      }
      chunks.push(bytes);
    }
    const mime = format === 'wav' ? 'audio/wav' : `audio/${format}`;
    return new Blob(chunks, { type: mime });
  };

  const clearTimers = useCallback(() => {
    if (meterTimerRef.current) clearInterval(meterTimerRef.current);
    if (autoStopTimerRef.current) clearTimeout(autoStopTimerRef.current);
    meterTimerRef.current = null;
    autoStopTimerRef.current = null;
    setMeterWidth(0);
  }, []);

  const stopStream = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
  }, []);

  // Mic permission check
  const checkMicrophoneSupport = useCallback((): string => {
    if (!window.isSecureContext) {
      return 'Open this page as http://localhost:8000/. Browsers block microphone access on insecure origins.';
    }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      return 'This browser does not support microphone access. Use Chrome, Edge, or Firefox.';
    }
    if (!window.MediaRecorder) {
      return 'This browser does not support MediaRecorder. Use Chrome, Edge, or Firefox.';
    }
    return '';
  }, []);

  // Start listening
  const beginListening = useCallback(async () => {
    try {
      const supportMessage = checkMicrophoneSupport();
      if (supportMessage) {
        setMessage(supportMessage, 'error');
        return;
      }

      streamRef.current = await navigator.mediaDevices.getUserMedia({ audio: true });
      chunksRef.current = [];

      const recorderOptions = MediaRecorder.isTypeSupported('audio/webm')
        ? { mimeType: 'audio/webm' }
        : undefined;

      recorderRef.current = new MediaRecorder(streamRef.current, recorderOptions);

      recorderRef.current.ondataavailable = (event) => {
        chunksRef.current.push(event.data);
      };

      recorderRef.current.onstop = async () => {
        if (chunksRef.current.length > 0) {
          const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
          await processAgentTurn(blob);
        }
      };

      recorderRef.current.start(250);
      setRecording(true);
      setMessage('Listening...');

      let width = 12;
      meterTimerRef.current = setInterval(() => {
        width = Math.min(100, width + Math.random() * 20);
        setMeterWidth(width);
      }, 180);

      const turnMs = Math.max(2, Math.min(20, turnSeconds)) * 1000;
      autoStopTimerRef.current = setTimeout(() => {
        stopRecording();
      }, turnMs);
    } catch (error: any) {
      setMessage(error.message || 'Error accessing microphone', 'error');
      clearTimers();
      stopStream();
    }
  }, [checkMicrophoneSupport, setMessage, turnSeconds, clearTimers, stopStream]);

  const stopRecording = useCallback(() => {
    if (!recorderRef.current || recorderRef.current.state !== 'recording') return;
    clearTimers();
    setRecording(false);
    setMessage('Transcribing...');
    recorderRef.current.stop();
  }, [clearTimers, setMessage]);

  // Process turn: transcribe audio and get agent response
  const processAgentTurn = useCallback(
    async (blob: Blob) => {
      if (blob.size < 1024) {
        setMessage('No speech detected. Listening again...');
        setTimeout(beginListening, 500);
        return;
      }

      try {
        setMessage('Transcribing...');
        const file = new File([blob], 'agent-turn.webm', { type: blob.type });
        const form = new FormData();
        form.append('file', file);
        form.append('language_code', selectedLanguage);
        form.append('model', 'saaras:v3');
        form.append('mode', 'transcribe');

        const sttResponse = await fetch(`${voiceApiBase}/stt/transcribe`, {
          method: 'POST',
          body: form,
        });

        if (!sttResponse.ok) {
          throw new Error(await readError(sttResponse));
        }

        const sttData = await sttResponse.json();
        const transcript = (sttData.transcript || '').trim();

        if (!transcript) {
          setMessage('Could not understand. Listening again...');
          setTimeout(beginListening, 500);
          return;
        }

        // Add user message to conversation
        const newUserMessage: Message = { role: 'user', content: transcript };
        setConversation((prev) => [...prev, newUserMessage]);

        // Get agent response
        setMessage('Thinking...');
        const agentResponse = await fetch(`${voiceApiBase}/agent/respond`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: 'default',
            user_input: transcript,
            language_code: selectedLanguage,
          }),
        });

        if (!agentResponse.ok) {
          throw new Error(await readError(agentResponse));
        }

        const agentData = await agentResponse.json();
        const assistantText = (agentData.assistant_text || '').trim();

        if (!assistantText) {
          setMessage('No response from agent.');
          setTimeout(beginListening, 500);
          return;
        }

        // Add assistant message
        const newAssistantMessage: Message = { role: 'assistant', content: assistantText };
        setConversation((prev) => [...prev, newAssistantMessage]);

        // Play audio response
        await playAgentAudio(agentData.audio_base64, agentData.audio_format || 'wav');
      } catch (error: any) {
        setMessage(error.message || 'Error processing turn', 'error');
        clearTimers();
        stopStream();
      }
    },
    [selectedLanguage, voiceApiBase, readError, beginListening, clearTimers, stopStream]
  );

  const playAgentAudio = useCallback(
    async (audioBase64: string, format: string) => {
      const blob = base64ToAudioBlob(audioBase64, format);
      const audioUrl = URL.createObjectURL(blob);

      if (audioRefRef.current) {
        if (audioRefRef.current.src) URL.revokeObjectURL(audioRefRef.current.src);
        audioRefRef.current.src = audioUrl;
        setMessage('Speaking...');

        audioRefRef.current.onended = () => {
          setTimeout(beginListening, 450);
        };

        await audioRefRef.current.play();
      }
    },
    [beginListening, setMessage]
  );

  const startAgent = useCallback(async () => {
    const supportMessage = checkMicrophoneSupport();
    if (supportMessage) {
      setMessage(supportMessage, 'error');
      return;
    }

    await beginListening();
  }, [checkMicrophoneSupport, setMessage, beginListening]);

  const stopAgent = useCallback(() => {
    clearTimers();
    if (recorderRef.current && recorderRef.current.state === 'recording') {
      recorderRef.current.onstop = () => {
        stopStream();
      };
      recorderRef.current.stop();
    } else {
      stopStream();
    }

    if (audioRefRef.current) {
      audioRefRef.current.pause();
      audioRefRef.current.currentTime = 0;
    }

    setRecording(false);
    setMessage('Idle');
  }, [clearTimers, stopStream, setMessage]);

  const resetAgent = useCallback(() => {
    setConversation([]);
    if (audioRefRef.current && audioRefRef.current.src) {
      URL.revokeObjectURL(audioRefRef.current.src);
      audioRefRef.current.src = '';
    }
    setMessage('Idle');
  }, [setMessage]);

  useEffect(() => {
    if (conversationRef.current) {
      conversationRef.current.scrollTop = conversationRef.current.scrollHeight;
    }
  }, [conversation]);

  // Check API health on mount
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await fetch(`${voiceApiBase}/health`);
        if (response.ok) {
          const data = await response.json();
          console.log('Voice Agent Health:', data);
          setMessage('Ready', 'ok');
        } else {
          console.error('Health check failed:', response.status);
          setMessage(`API Error: ${response.status}`, 'error');
        }
      } catch (error: any) {
        console.error('Health check error:', error);
        setMessage(`Cannot reach API: ${error.message}`, 'error');
      }
    };
    checkHealth();
  }, [voiceApiBase, setMessage]);

  return (
    <PageShell
      title="Voice AI Assistant"
      subtitle="Chat with your financial assistant using voice"
    >
      <style>{styles}</style>

      <div className="voice-assistant-container">
        {/* Main Agent Panel */}
        <section className="panel agent-panel" aria-labelledby="agentTitle">
          <div className="panel-head">
            <div>
              <h2 id="agentTitle">Voice Agent</h2>
              <p>Speak with your AI financial assistant</p>
            </div>
            <span className="tag">Voice Chat</span>
          </div>

          <div className="body agent-layout">
            {/* Controls */}
            <div className="agent-controls">
              <div className="controls-section">
                <div className="form-group">
                  <label htmlFor="agentLanguage">Language</label>
                  <select
                    id="agentLanguage"
                    value={selectedLanguage}
                    onChange={(e) => setSelectedLanguage(e.target.value)}
                  >
                    <option value="en-IN">English (India)</option>
                    <option value="hi-IN">Hindi</option>
                    <option value="mr-IN">Marathi</option>
                    <option value="ta-IN">Tamil</option>
                    <option value="te-IN">Telugu</option>
                    <option value="kn-IN">Kannada</option>
                    <option value="ml-IN">Malayalam</option>
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="agentTurnSeconds">Turn Duration (seconds)</label>
                  <input
                    id="agentTurnSeconds"
                    type="number"
                    min="2"
                    max="30"
                    value={turnSeconds}
                    onChange={(e) => setTurnSeconds(Math.max(2, Math.min(30, parseInt(e.target.value) || 6)))}
                  />
                </div>

                <div className="form-group">
                  <label>Audio Meter</label>
                  <div className="meter">
                    <span style={{ width: `${meterWidth}%` }} />
                  </div>
                </div>
              </div>

              <div className="actions">
                <button
                  className="button primary"
                  onClick={startAgent}
                  disabled={recording}
                >
                  Start
                </button>
                <button
                  className="button secondary"
                  onClick={stopRecording}
                  disabled={!recording}
                >
                  Stop
                </button>
                <button
                  className="button danger"
                  onClick={stopAgent}
                  disabled={!recording}
                >
                  End
                </button>
              </div>

              <div className="actions">
                <button
                  className="button secondary"
                  onClick={resetAgent}
                  disabled={conversation.length === 0}
                >
                  Clear
                </button>
              </div>

              <div className={`message ${statusType}`}>{status}</div>

              <audio ref={audioRefRef} />
            </div>

            {/* Conversation */}
            <div
              ref={conversationRef}
              className="conversation"
            >
              {conversation.length === 0 ? (
                <div style={{ color: 'var(--muted)', fontStyle: 'italic' }}>
                  Your voice conversation will appear here
                </div>
              ) : (
                conversation.map((msg, idx) => (
                  <div key={idx} className={`turn ${msg.role}`}>
                    <strong>
                      {msg.role === 'user' ? 'You' : 'Assistant'} · {idx + 1}
                    </strong>
                    <p>{msg.content}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        </section>

        {/* Text-based Chat Panel */}
        <section className="panel" aria-labelledby="textChatTitle">
          <div className="panel-head">
            <div>
              <h2 id="textChatTitle">Features</h2>
              <p>Voice assistant capabilities</p>
            </div>
            <span className="tag">Info</span>
          </div>

          <div className="body">
            <div style={{ display: 'grid', gap: '1rem' }}>
              <div>
                <h3 style={{ margin: '0 0 0.5rem', fontSize: '0.95rem', fontWeight: 700, color: 'var(--ink)' }}>
                  Tax & Finance Support
                </h3>
                <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--muted)', lineHeight: 1.5 }}>
                  Ask about ITR filing, deductions, GST compliance, tax savings strategies, and more.
                </p>
              </div>

              <div>
                <h3 style={{ margin: '0 0 0.5rem', fontSize: '0.95rem', fontWeight: 700, color: 'var(--ink)' }}>
                  Multilingual
                </h3>
                <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--muted)', lineHeight: 1.5 }}>
                  Speak in English, Hindi, Marathi, Tamil, Telugu, Kannada, or Malayalam.
                </p>
              </div>

              <div>
                <h3 style={{ margin: '0 0 0.5rem', fontSize: '0.95rem', fontWeight: 700, color: 'var(--ink)' }}>
                  Natural Conversation
                </h3>
                <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--muted)', lineHeight: 1.5 }}>
                  Get conversational answers with step-by-step guidance for tax compliance.
                </p>
              </div>
            </div>
          </div>
        </section>
      </div>
    </PageShell>
  );
}
