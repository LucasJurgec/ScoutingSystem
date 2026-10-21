import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { API_BASE } from '../api';
import { formatEuro } from './StatPageComponents/statUtils';
import './LeagueSummaryPage.css';

const COLUMNS = [
    { key: 'club_name', label: 'Team' },
    { key: 'squad_size', label: 'Squad' },
    { key: 'avg_age', label: 'Avg age' },
    { key: 'avg_market_value', label: 'Avg value', money: true },
    { key: 'top_market_value', label: 'Top value', money: true },
    { key: 'top_value_player', label: 'Top value player' },
    { key: 'total_goals', label: 'Goals' },
    { key: 'top_scorer', label: 'Top scorer' },
    { key: 'top_scorer_goals', label: 'Scr. goals' },
    { key: 'top_assister', label: 'Top assister' },
    { key: 'top_assister_assists', label: 'Assists' },
];

function LeagueSummaryPage() {
    const [leagues, setLeagues] = useState([]);
    const [leagueId, setLeagueId] = useState('');
    const [rows, setRows] = useState([]);
    const [loading, setLoading] = useState(true);
    const [sortKey, setSortKey] = useState('avg_market_value');
    const [sortDir, setSortDir] = useState('desc');
    const [files, setFiles] = useState([]);
    const [generating, setGenerating] = useState(false);

    const loadFiles = () =>
        axios.get(`${API_BASE}/reports/league-summary/files`).then(r => setFiles(r.data)).catch(console.error);

    useEffect(() => {
        axios.get(`${API_BASE}/leagues`).then(r => setLeagues(r.data)).catch(console.error);
        loadFiles();
    }, []);

    useEffect(() => {
        setLoading(true);
        axios.get(`${API_BASE}/reports/league-summary`, { params: leagueId ? { league_id: leagueId } : {} })
        .then(r => setRows(r.data)).catch(console.error).finally(() => setLoading(false));
    }, [leagueId]);

    const sorted = [...rows].sort((a, b) => {
        const av = a[sortKey], bv = b[sortKey];
        if (av == null) return 1;
        if (bv == null) return -1;
        const cmp = typeof av === 'number' && typeof bv === 'number'
            ? av - bv : String(av).localeCompare(String(bv));
        return sortDir === 'asc' ? cmp : -cmp;
    });

    const toggleSort = (key) =>
        key === sortKey ? setSortDir(d => d === 'asc' ? 'desc' : 'asc') : (setSortKey(key), setSortDir('desc'));

        const downloadView = () => {
            const esc = v => { const s = String(v ?? ''); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
        const csv = [COLUMNS.map(c => c.label).join(',')]
            .concat(sorted.map(r => COLUMNS.map(c => esc(r[c.key])).join(','))).join('\n');
        const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
        const a = document.createElement('a');
        const lg = leagues.find(l => String(l.league_id) === leagueId);
        a.href = url;
        a.download = `league_summary_${lg ? lg.league_name.replace(/\s+/g, '_') : 'all'}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    };

    const generateNow = () => {
        setGenerating(true);
        axios.post(`${API_BASE}/reports/league-summary/generate`).then(loadFiles)
            .catch(console.error).finally(() => setGenerating(false));
    };

  return (
    <div className="select-page">
      <div className="select-header">
        <h1 className="title select-title">League Summary</h1>
        <nav className="page-nav">
          <Link to="/" className="nav-btn">Players</Link>
          <Link to="/ShortlistPage" className="nav-btn">Shortlist</Link>
        </nav>
      </div>

      <div className="filters">
        <select value={leagueId} onChange={e => setLeagueId(e.target.value)} aria-label="League">
          <option value="">All leagues</option>
          {leagues.map(l => <option key={l.league_id} value={l.league_id}>{l.league_name}</option>)}
        </select>
        <button className="nav-btn" onClick={downloadView} disabled={!sorted.length}>Download CSV</button>
      </div>

      {loading ? <p className="list-status">Loading…</p> : (
        <div className="table-wrap">
          <table className="summary-table">
            <thead>
              <tr>{COLUMNS.map(c => (
                <th key={c.key} onClick={() => toggleSort(c.key)}>
                  {c.label}{sortKey === c.key ? (sortDir === 'asc' ? ' ▲' : ' ▼') : ''}
                </th>))}</tr>
            </thead>
            <tbody>
              {sorted.map((r, i) => (
                <tr key={i}>{COLUMNS.map(c => (
                  <td key={c.key}>{r[c.key] == null ? '–' : c.money ? formatEuro(r[c.key]) : r[c.key]}</td>
                ))}</tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="weekly-reports">
        <div className="weekly-head">
          <h2>Weekly reports</h2>
          <button className="nav-btn" onClick={generateNow} disabled={generating}>
            {generating ? 'Generating…' : 'Generate now'}
          </button>
        </div>
        {files.length === 0 ? <p className="list-status">No reports generated yet.</p> : (
          <ul className="file-list">
            {files.map(f => (
              <li key={f.name}>
                <a href={`${API_BASE}/reports/league-summary/files/${encodeURIComponent(f.name)}`}>{f.name}</a>
                <span>{new Date(f.generated_at).toLocaleString()}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export default LeagueSummaryPage;