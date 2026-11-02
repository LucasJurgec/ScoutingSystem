import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { API_BASE } from '../api';
import './SelectPage.css';     // reuse the list/row styles
import './ShortlistPage.css';
import { formatEuro } from './StatPageComponents/statUtils';

const SILHOUETTE = '/images/PlayerSilhouette.png';
const POSITIONS = ['Goalkeeper', 'Defender', 'Midfielder', 'Attacker'];

const fullName = (p) => [p.first_name, p.last_name].filter(Boolean).join(' ');
const hideImage = (e) => { e.currentTarget.style.visibility = 'hidden'; };

// The shortlist is small, so it's fetched once and filtered/sorted in the browser.
const SORTERS = {
    added: (a, b) => new Date(b.added_at) - new Date(a.added_at),
    value: (a, b) => (b.market_value ?? -1) - (a.market_value ?? -1),
    name: (a, b) =>
        (a.last_name ?? '').localeCompare(b.last_name ?? '') ||
        (a.first_name ?? '').localeCompare(b.first_name ?? ''),
};

// ---- CSV column picker ----------------------------------------------------
// `field` is the key the /shortlist API returns. A column only shows up in the
// picker if at least one player actually has that key, so the stat/contract
// options appear automatically once the backend query returns them.
// `value` is optional; without it the raw field is exported.
const CSV_COLUMNS = [
    // Profile
    { key: 'position', label: 'Position', group: 'Profile', field: 'position_general',
      value: p => p.position_advanced || p.position_general, on: true },
    { key: 'age', label: 'Age', group: 'Profile', field: 'age', on: true },
    { key: 'club', label: 'Club', group: 'Profile', field: 'club_name',
      value: p => p.club_name ?? p.status, on: true },
    { key: 'nation', label: 'Nation', group: 'Profile', field: 'nation_name', on: true },
    { key: 'value', label: 'Market value (€)', group: 'Profile', field: 'market_value', on: true },
    { key: 'added', label: 'Date added', group: 'Profile', field: 'added_at',
      value: p => String(p.added_at ?? '').slice(0, 10) },

    // Season stats (2025/26) — match these field names to your SQL aliases
    { key: 'apps', label: 'Appearances', group: 'Season stats', field: 'appearances' },
    { key: 'minutes', label: 'Minutes', group: 'Season stats', field: 'minutes' },
    { key: 'goals', label: 'Goals', group: 'Season stats', field: 'goals' },
    { key: 'assists', label: 'Assists', group: 'Season stats', field: 'assists' },
    { key: 'xg', label: 'xG', group: 'Season stats', field: 'xg' },
    { key: 'xa', label: 'xA', group: 'Season stats', field: 'xa' },
    { key: 'key_passes', label: 'Key passes', group: 'Season stats', field: 'key_passes' },
    { key: 'clean_sheets', label: 'Clean sheets', group: 'Season stats', field: 'clean_sheets' },

    // Contract
    { key: 'expiry', label: 'Contract expiry', group: 'Contract', field: 'contract_expiry',
      value: p => String(p.contract_expiry ?? '').slice(0, 10) },
    { key: 'wage', label: 'Weekly wage (€)', group: 'Contract', field: 'weekly_wage' },
    { key: 'release', label: 'Release clause (€)', group: 'Contract', field: 'release_clause' },
    { key: 'clauses', label: 'Extra clauses', group: 'Contract', field: 'extra_clauses' },

    // Scouting (MongoDB)
    { key: 'has_report', label: 'Has scouting report', group: 'Scouting', field: 'has_report' },
    { key: 'report_updated', label: 'Report last updated', group: 'Scouting', field: 'report_updated',
      value: p => String(p.report_updated ?? '').slice(0, 10) },
];

const DEFAULT_COLS = CSV_COLUMNS.filter(c => c.on).map(c => c.key);
const getValue = (col, p) => (col.value ? col.value(p) : p[col.field]);

const STORAGE_KEY = 'shortlist-csv-columns';
const loadSavedColumns = () => {
    try {
        const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
        if (Array.isArray(saved)) return saved;
    } catch { /* storage blocked or corrupt — fall back to defaults */ }
    return DEFAULT_COLS;
};

function ShortlistPage() {
    const [players, setPlayers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [actionError, setActionError] = useState(null);

    const [search, setSearch] = useState('');
    const [position, setPosition] = useState('');
    const [sort, setSort] = useState('added');

    const [csvCols, setCsvCols] = useState(loadSavedColumns);
    const [showCols, setShowCols] = useState(false);

    useEffect(() => {
        axios.get(`${API_BASE}/shortlist`)
            .then(res => setPlayers(res.data))
            .catch(err => {
                console.error(err);
                setError(`Could not load the shortlist. Check the API is running at ${API_BASE}.`);
            })
            .finally(() => setLoading(false));
    }, []);

    // remember the user's column choice between visits
    useEffect(() => {
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify(csvCols)); } catch { /* ignore */ }
    }, [csvCols]);

    const visible = useMemo(() => {
        const term = search.trim().toLowerCase();
        return players
            .filter(p => !term || fullName(p).toLowerCase().includes(term))
            .filter(p => !position || p.position_general === position)
            .sort(SORTERS[sort]);
    }, [players, search, position, sort]);

    // only offer columns the API actually sent
    const availableCols = useMemo(
        () => CSV_COLUMNS.filter(c => players.some(p => c.field in p)),
        [players],
    );
    const chosenCols = availableCols.filter(c => csvCols.includes(c.key));   // keeps CSV_COLUMNS order
    const colGroups = [...new Set(availableCols.map(c => c.group))];

    const toggleCol = (key) =>
        setCsvCols(prev => (prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]));

    const totalValue = players.reduce((sum, p) => sum + (Number(p.market_value) || 0), 0);
    const hasActiveFilters = search || position || sort !== 'added';

    const downloadCsv = () => {
        const esc = (v) => {
            const s = String(v ?? '');
            return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
        };
        const headers = ['First name', 'Last name', ...chosenCols.map(c => c.label)];
        const rows = visible.map(p => [
            p.first_name,
            p.last_name,
            ...chosenCols.map(c => getValue(c, p)),
        ]);
        // BOM so Excel reads UTF-8 properly (Mbappé, Ødegaard, etc.)
        const csv = '﻿' + [headers, ...rows].map(r => r.map(esc).join(',')).join('\r\n');

        const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
        const a = document.createElement('a');
        a.href = url;
        a.download = `shortlist-${new Date().toLocaleDateString('en-CA')}.csv`;   // YYYY-MM-DD, local time
        a.click();
        setTimeout(() => URL.revokeObjectURL(url), 0);
    };

    const clearFilters = () => {
        setSearch('');
        setPosition('');
        setSort('added');
    };

    const remove = (e, player) => {
        e.preventDefault();      // the button sits inside the row's <Link>
        e.stopPropagation();
        setActionError(null);
        setPlayers(prev => prev.filter(p => p.player_id !== player.player_id));
        axios.delete(`${API_BASE}/shortlist/${player.player_id}`)
            .catch(err => {
                console.error(err);
                setPlayers(prev => [...prev, player]);   // put them back
                setActionError(`Could not remove ${fullName(player)}. Try again.`);
            });
    };

    return (
        <div className="select-page">
            <div className="select-header">
                <h1 className="title select-title">Shortlist</h1>
                <nav className="page-nav">
                    <Link to="/" className="nav-btn">All players</Link>
                    <Link to="/assistant" className="nav-btn nav-btn-primary">AI Assistant</Link>
                </nav>
            </div>

            {!loading && !error && players.length > 0 && (
                <p className="shortlist-summary">
                    {players.length} {players.length === 1 ? 'player' : 'players'} · combined value {formatEuro(totalValue)}
                </p>
            )}

            <input
                className="search-input"
                type="search"
                placeholder="Search your shortlist"
                aria-label="Search your shortlist"
                value={search}
                onChange={e => setSearch(e.target.value)}
            />

            <div className="filters">
                <select aria-label="Position" value={position} onChange={e => setPosition(e.target.value)}>
                    <option value="">All positions</option>
                    {POSITIONS.map(p => <option key={p} value={p}>{p}s</option>)}
                </select>

                <select aria-label="Sort by" value={sort} onChange={e => setSort(e.target.value)}>
                    <option value="added">Recently added</option>
                    <option value="value">Highest value</option>
                    <option value="name">Name A–Z</option>
                </select>

                <button
                    className="nav-btn"
                    onClick={() => setShowCols(s => !s)}
                    aria-expanded={showCols}
                    aria-controls="csv-columns"
                    disabled={!players.length}
                >
                    CSV columns ({chosenCols.length + 1})
                </button>

                <button className="nav-btn" onClick={downloadCsv} disabled={!visible.length}>Download CSV</button>

                {hasActiveFilters && (
                    <button className="clear-btn" onClick={clearFilters}>Clear filters</button>
                )}
            </div>

            {showCols && players.length > 0 && (
                <div id="csv-columns" className="csv-columns">
                    <p className="csv-columns-note">
                        Name is always included. The export uses the {visible.length} {visible.length === 1 ? 'player' : 'players'} currently
                        shown, in the current sort order.
                    </p>

                    {colGroups.map(group => (
                        <fieldset key={group} className="csv-group">
                            <legend>{group}</legend>
                            <div className="csv-chips">
                                {availableCols.filter(c => c.group === group).map(c => {
                                    const on = csvCols.includes(c.key);
                                    return (
                                        <button
                                            key={c.key}
                                            type="button"
                                            className={`csv-chip${on ? ' is-on' : ''}`}
                                            aria-pressed={on}
                                            onClick={() => toggleCol(c.key)}
                                        >
                                            {on && <span aria-hidden="true">✓ </span>}{c.label}
                                        </button>
                                    );
                                })}
                            </div>
                        </fieldset>
                    ))}

                    <div className="csv-columns-actions">
                        <button className="clear-btn" onClick={() => setCsvCols(availableCols.map(c => c.key))}>Select all</button>
                        <button className="clear-btn" onClick={() => setCsvCols([])}>Name only</button>
                        <button className="clear-btn" onClick={() => setCsvCols(DEFAULT_COLS)}>Reset</button>
                    </div>
                </div>
            )}

            {actionError && <p className="shortlist-error">{actionError}</p>}

            <div className="player-row player-row-header" aria-hidden="true">
                <span />
                <span>Player</span>
                <span>Position</span>
                <span className="col-age">Age</span>
                <span className="col-club">Club</span>
                <span className="col-nation">Nation</span>
                <span className="col-value">Value</span>
            </div>

            {loading && <p className="list-status">Loading shortlist...</p>}
            {!loading && error && <p className="list-status">{error}</p>}

            {!loading && !error && players.length === 0 && (
                <div className="list-status">
                    <p>Your shortlist is empty. Open a player and hit "Add to shortlist".</p>
                    <Link to="/" className="clear-btn">Browse players</Link>
                </div>
            )}

            {!loading && !error && players.length > 0 && visible.length === 0 && (
                <div className="list-status">
                    <p>No shortlisted players match these filters.</p>
                    <button className="clear-btn" onClick={clearFilters}>Clear filters</button>
                </div>
            )}

            {!loading && !error && visible.map(p => (
                <Link key={p.player_id} to={`/player/${p.player_id}`} className="player-row">
                    <img
                        className="row-img"
                        src={p.player_img || SILHOUETTE}
                        alt=""
                        loading="lazy"
                        onError={(e) => {
                            if (!e.currentTarget.src.endsWith(SILHOUETTE)) e.currentTarget.src = SILHOUETTE;
                        }}
                    />
                    <span className="truncate row-name">{fullName(p)}</span>
                    <span>{p.position_advanced || p.position_general}</span>
                    <span className="col-age">{p.age ?? '–'}</span>
                    <span className="col-club row-badge">
                        {p.club_logo && <img src={p.club_logo} alt="" onError={hideImage} />}
                        <span className="truncate">{p.club_name ?? p.status}</span>
                    </span>
                    <span className="col-nation row-badge">
                        {p.nation_flag && <img src={p.nation_flag} alt="" onError={hideImage} />}
                        <span className="truncate">{p.nation_name}</span>
                    </span>
                    <span className="col-value shortlist-value">
                        {formatEuro(p.market_value)}
                        <button
                            className="remove-btn"
                            onClick={(e) => remove(e, p)}
                            aria-label={`Remove ${fullName(p)} from shortlist`}
                            title="Remove from shortlist"
                        >
                            ✕
                        </button>
                    </span>
                </Link>
            ))}
        </div>
    );
}

export default ShortlistPage;
