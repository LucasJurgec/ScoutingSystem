import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { API_BASE } from '../api';
import './AssistantPage.css';

// Talks to the chatbot backend: POST { message, history } -> { answer, steps, models_used }.
// Point this at whatever route wraps chatbot.ask() in your API.
const CHAT_ENDPOINT = `${API_BASE}/chat`;
const HISTORY_TURNS = 6; // match the backend so we don't send more than it keeps

const EXAMPLES = [
    'Who are the top scorers this season?',
    'Most valuable active players under 21',
    'Find U23 midfielders who are good passers',
    'Which contracts expire in the next 12 months?',
];

// Collapsible panel showing the tool calls behind an answer (SQL + report searches).
function ToolSteps({ steps }) {
    if (!steps || steps.length === 0) return null;
    return (
        <details className="tool-steps">
            <summary>{steps.length} tool {steps.length === 1 ? 'call' : 'calls'}</summary>
            {steps.map((s, i) => (
                <div key={i} className="tool-step">
                    <span className="tool-name">{s.tool}</span>
                    <pre>{s.tool === 'run_sql'
                        ? (s.input?.query ?? '').trim()
                        : JSON.stringify(s.input, null, 2)}</pre>
                </div>
            ))}
        </details>
    );
}

function AssistantPage() {
    const [messages, setMessages] = useState([]); // { role, content, steps?, models? }
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const scrollRef = useRef(null);
    const inputRef = useRef(null);

    // keep the latest message in view
    useEffect(() => {
        scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
    }, [messages, loading]);

    const send = async (text) => {
        const message = (text ?? input).trim();
        if (!message || loading) return;

        // send only {role, content} for prior turns; backend slices to HISTORY_TURNS too
        const history = messages
            .slice(-HISTORY_TURNS)
            .map(m => ({ role: m.role, content: m.content }));

        setMessages(prev => [...prev, { role: 'user', content: message }]);
        setInput('');
        setError(null);
        setLoading(true);

        try {
            const res = await axios.post(CHAT_ENDPOINT, { message, history });
            const { answer, steps, models_used } = res.data;
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: answer,
                steps: steps || [],
                models: models_used || [],
            }]);
        } catch (err) {
            console.error(err);
            setError(`Could not reach the assistant. Check the API is running at ${API_BASE}.`);
        } finally {
            setLoading(false);
            inputRef.current?.focus();
        }
    };

    const onKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            send();
        }
    };

    return (
        <div className="assistant-page">
            <div className="assistant-header">
                <h1 className="title">Scouting Assistant</h1>
                <nav className="page-nav">
                    <Link to="/" className="nav-btn">← Scouting</Link>
                    <Link to="/shortlist" className="nav-btn">Shortlist</Link>
                </nav>
            </div>

            <div className="chat-window" ref={scrollRef}>
                {messages.length === 0 && !loading && (
                    <div className="chat-empty">
                        <p>Ask about players, stats, or scouting reports.</p>
                        <div className="example-chips">
                            {EXAMPLES.map(ex => (
                                <button key={ex} className="example-chip" onClick={() => send(ex)}>
                                    {ex}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {messages.map((m, i) => (
                    <div key={i} className={`msg msg-${m.role}`}>
                        <div className="msg-bubble">{m.content}</div>
                        {m.role === 'assistant' && <ToolSteps steps={m.steps} />}
                        {m.role === 'assistant' && m.models?.length > 0 && (
                            <div className="msg-meta">answered by {m.models.join(', ')}</div>
                        )}
                    </div>
                ))}

                {loading && (
                    <div className="msg msg-assistant">
                        <div className="msg-bubble thinking">
                            <span></span><span></span><span></span>
                        </div>
                    </div>
                )}

                {error && <p className="chat-error">{error}</p>}
            </div>

            <div className="chat-input-bar">
                <textarea
                    ref={inputRef}
                    className="chat-input"
                    rows={1}
                    placeholder="Ask the scouting assistant..."
                    aria-label="Ask the scouting assistant"
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={onKeyDown}
                    disabled={loading}
                />
                <button
                    className="send-btn"
                    onClick={() => send()}
                    disabled={loading || !input.trim()}
                >
                    Send
                </button>
            </div>
        </div>
    );
}

export default AssistantPage;
