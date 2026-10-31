import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API_BASE } from '../api';
import './AdminPage.css';

// Saved queries for the dropdown. Adjust table/column names to match your schema.
const EXAMPLES = [
    { label: 'Show all tables', sql: 'SHOW TABLES;' },
    { label: 'Describe the player table', sql: 'DESCRIBE player;' },
    {
        label: 'Players per status',
        sql: 'SELECT status, COUNT(*) AS players\nFROM player\nGROUP BY status;',
    },
    {
        label: 'Data check: active players with no club',
        sql: "SELECT player_id, first_name, last_name\nFROM player\nWHERE status = 'Active' AND club_id IS NULL;",
    },
];

const auth = { withCredentials: true }; // send the session cookie

function AdminPage() {
    const navigate = useNavigate();
    const [user, setUser] = useState(null);       // null = still checking
    const [sql, setSql] = useState('SHOW TABLES;');
    const [result, setResult] = useState(null);   // { columns, rows, row_count, truncated }
    const [error, setError] = useState(null);
    const [running, setRunning] = useState(false);
    const [elapsed, setElapsed] = useState(null);

    const goToLogin = () => navigate('/login', { replace: true, state: { from: '/admin' } });

    // page-load check: not logged in -> login page
    useEffect(() => {
        axios.get(`${API_BASE}/auth/me`, auth)
            .then(res => setUser(res.data))
            .catch(goToLogin);
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    const runQuery = () => {
        if (!sql.trim() || running) return;
        setRunning(true);
        setError(null);
        const start = performance.now();

        axios.post(`${API_BASE}/admin/query`, { sql }, auth)
            .then(res => {
                setResult(res.data);
                setElapsed(Math.round(performance.now() - start));
            })
            .catch(err => {
                if (err.response?.status === 401) return goToLogin(); // session expired
                setResult(null);
                setError(err.response?.data?.detail ?? `Could not reach the API at ${API_BASE}.`);
            })
            .finally(() => setRunning(false));
    };

    const logout = () => {
        axios.post(`${API_BASE}/auth/logout`, {}, auth)
            .finally(() => navigate('/', { replace: true }));
    };

    // Ctrl+Enter / Cmd+Enter runs the query
    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            runQuery();
        }
    };

    if (!user) return <p className="admin-status">Checking login...</p>;

    return (
        <div className="admin-page">
            <div className="admin-header">
                <h1 className="admin-title">Admin Query Console</h1>
                <div className="admin-header-actions">
                    <span className="admin-user">Logged in as <strong>{user.username}</strong></span>
                    <Link to="/" className="nav-btn">← Back</Link>
                    <button className="nav-btn" onClick={logout}>Log out</button>
                </div>
            </div>

            <div className="admin-toolbar">
                <select
                    aria-label="Example queries"
                    value=""
                    onChange={e => { if (e.target.value !== '') setSql(EXAMPLES[e.target.value].sql); }}
                >
                    <option value="">Example queries…</option>
                    {EXAMPLES.map((ex, i) => <option key={ex.label} value={i}>{ex.label}</option>)}
                </select>
                <span className="admin-hint">Read-only: SELECT, SHOW, DESCRIBE, EXPLAIN. One statement at a time.</span>
            </div>

            <textarea
                className="admin-editor"
                aria-label="SQL query"
                spellCheck={false}
                value={sql}
                onChange={e => setSql(e.target.value)}
                onKeyDown={handleKeyDown}
            />

            <button className="admin-run" onClick={runQuery} disabled={running || !sql.trim()}>
                {running ? 'Running...' : 'Run query'} <span className="admin-shortcut">Ctrl+Enter</span>
            </button>

            {error && <pre className="admin-error" role="alert">{error}</pre>}

            {result && !error && (
                <section className="admin-results">
                    <p className="admin-meta">
                        {result.row_count} row{result.row_count === 1 ? '' : 's'}
                        {result.truncated && ` (showing first ${result.rows.length})`}
                        {elapsed != null && ` · ${elapsed} ms`}
                    </p>

                    {result.columns.length > 0 && (
                        <div className="admin-table-wrap">
                            <table className="admin-table">
                                <thead>
                                    <tr>{result.columns.map(c => <th key={c}>{c}</th>)}</tr>
                                </thead>
                                <tbody>
                                    {result.rows.map((row, i) => (
                                        <tr key={i}>
                                            {row.map((v, j) => (
                                                <td key={j}>
                                                    {v === null ? <span className="admin-null">NULL</span> : String(v)}
                                                </td>
                                            ))}
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </section>
            )}
        </div>
    );
}

export default AdminPage;
