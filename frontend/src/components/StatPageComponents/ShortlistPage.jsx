import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { API_BASE } from '../api';
import './SelectPage.css';     // reuse the list/row styles
import './StatPageComponents/ShortlistPage.css';
import { formatEuro } from './statUtils';

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

function ShortlistPage() {
    const [players, setPlayers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [actionError, setActionError] = useState(null);

    const [search, setSearch] = useState('');
    const [position, setPosition] = useState('');
    const [sort, setSort] = useState('added');

    useEffect(() => {
        axios.get(`${API_BASE}/shortlist`)
            .then(res => setPlayers(res.data))
            .catch(err => {
                console.error(err);
                setError(`Could not load the shortlist. Check the API is running at ${API_BASE}.`);
            })
            .finally(() => setLoading(false));
    }, []);

    const visible = useMemo(() => {
        const term = search.trim().toLowerCase();
        return players
            .filter(p => !term || fullName(p).toLowerCase().includes(term))
            .filter(p => !position || p.position_general === position)
            .sort(SORTERS[sort]);
    }, [players, search, position, sort]);

    const totalValue = players.reduce((sum, p) => sum + (Number(p.market_value) || 0), 0);
    const hasActiveFilters = search || position || sort !== 'added';

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

                {hasActiveFilters && (
                    <button className="clear-btn" onClick={clearFilters}>Clear filters</button>
                )}
            </div>

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
