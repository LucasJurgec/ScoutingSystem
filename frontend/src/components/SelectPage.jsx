import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { API_BASE } from '../api';
import './SelectPage.css';
import { formatEuro } from './statUtils';

const PAGE_SIZE = 50;
const SILHOUETTE = '/images/PlayerSilhouette.png';
const POSITIONS = ['Goalkeeper', 'Defender', 'Midfielder', 'Attacker'];

const fullName = (p) => [p.first_name, p.last_name].filter(Boolean).join(' ');
const hideImage = (e) => { e.currentTarget.style.visibility = 'hidden'; };

function SelectPage() {
    // Filters live in the URL (?league_id=10&position=Attacker...), so pressing
    // back from a player page returns you to the same filtered list.
    const [params, setParams] = useSearchParams();
    const filters = {
        search: params.get('search') ?? '',
        league_id: params.get('league_id') ?? '',
        club_id: params.get('club_id') ?? '',
        nation_code: params.get('nation_code') ?? '',
        position: params.get('position') ?? '',
        status: params.get('status') ?? 'Active',   // 'all' = no status filter
        sort: params.get('sort') ?? 'value',
    };
    const queryKey = params.toString();

    const [searchText, setSearchText] = useState(filters.search);
    const [leagues, setLeagues] = useState([]);
    const [clubs, setClubs] = useState([]);
    const [nations, setNations] = useState([]);

    const [players, setPlayers] = useState([]);
    const [hasMore, setHasMore] = useState(false);
    const [loading, setLoading] = useState(true);
    const [loadingMore, setLoadingMore] = useState(false);
    const [error, setError] = useState(null);

    const updateParam = (key, value) => {
        setParams(prev => {
            const next = new URLSearchParams(prev);
            if (value === '' || value == null) next.delete(key);
            else next.set(key, value);
            if (key === 'league_id') next.delete('club_id'); // club list depends on the league
            return next;
        }, { replace: true });
    };

    const clearFilters = () => {
        setSearchText('');
        setParams({}, { replace: true });
    };

    const buildQuery = (offset) => {
        const q = { limit: PAGE_SIZE, offset, sort: filters.sort };
        ['search', 'league_id', 'club_id', 'nation_code', 'position'].forEach(key => {
            if (filters[key]) q[key] = filters[key];
        });
        if (filters.status !== 'all') q.status = filters.status;
        return q;
    };

    // dropdown options, loaded once
    useEffect(() => {
        Promise.all([
            axios.get(`${API_BASE}/leagues`),
            axios.get(`${API_BASE}/clubs`),
            axios.get(`${API_BASE}/nations`),
        ])
            .then(([l, c, n]) => {
                setLeagues(l.data);
                setClubs(c.data);
                setNations(n.data);
            })
            .catch(err => console.error('Could not load filter options', err));
    }, []);

    // wait until typing stops for 300ms before searching
    useEffect(() => {
        const timer = setTimeout(() => {
            if (searchText.trim() !== filters.search) updateParam('search', searchText.trim());
        }, 300);
        return () => clearTimeout(timer);
    }, [searchText]); // eslint-disable-line react-hooks/exhaustive-deps

    // refetch the first page whenever the filters change
    useEffect(() => {
        let cancelled = false; // ignore responses from an older filter set
        setLoading(true);
        setError(null);
        axios.get(`${API_BASE}/players`, { params: buildQuery(0) })
            .then(res => {
                if (cancelled) return;
                setPlayers(res.data);
                setHasMore(res.data.length === PAGE_SIZE);
            })
            .catch(err => {
                if (cancelled) return;
                console.error(err);
                setError(`Could not load players. Check the API is running at ${API_BASE}.`);
            })
            .finally(() => { if (!cancelled) setLoading(false); });
        return () => { cancelled = true; };
    }, [queryKey]); // eslint-disable-line react-hooks/exhaustive-deps

    const loadMore = () => {
        setLoadingMore(true);
        axios.get(`${API_BASE}/players`, { params: buildQuery(players.length) })
            .then(res => {
                setPlayers(prev => [...prev, ...res.data]);
                setHasMore(res.data.length === PAGE_SIZE);
            })
            .catch(err => console.error(err))
            .finally(() => setLoadingMore(false));
    };

    const visibleClubs = filters.league_id
        ? clubs.filter(c => String(c.league_id) === filters.league_id)
        : clubs;

    const hasActiveFilters =
        filters.search || filters.league_id || filters.club_id || filters.nation_code ||
        filters.position || filters.status !== 'Active' || filters.sort !== 'value';

    return (
        <div className="select-page">
            <h1 className="title select-title">Scouting System</h1>

            <input
                className="search-input"
                type="search"
                placeholder="Search players by name"
                aria-label="Search players by name"
                value={searchText}
                onChange={e => setSearchText(e.target.value)}
            />

            <div className="filters">
                <select aria-label="League" value={filters.league_id} onChange={e => updateParam('league_id', e.target.value)}>
                    <option value="">All leagues</option>
                    {leagues.map(l => <option key={l.league_id} value={l.league_id}>{l.league_name}</option>)}
                </select>

                <select aria-label="Club" value={filters.club_id} onChange={e => updateParam('club_id', e.target.value)}>
                    <option value="">All clubs</option>
                    {visibleClubs.map(c => <option key={c.club_id} value={c.club_id}>{c.club_name}</option>)}
                </select>

                <select aria-label="Nation" value={filters.nation_code} onChange={e => updateParam('nation_code', e.target.value)}>
                    <option value="">All nations</option>
                    {nations.map(n => <option key={n.nation_code} value={n.nation_code}>{n.nation_name}</option>)}
                </select>

                <select aria-label="Position" value={filters.position} onChange={e => updateParam('position', e.target.value)}>
                    <option value="">All positions</option>
                    {POSITIONS.map(p => <option key={p} value={p}>{p}s</option>)}
                </select>

                <select aria-label="Status" value={filters.status} onChange={e => updateParam('status', e.target.value)}>
                    <option value="Active">Active players</option>
                    <option value="Free Agent">Free agents</option>
                    <option value="Retired">Retired</option>
                    <option value="all">All players</option>
                </select>

                <select aria-label="Sort by" value={filters.sort} onChange={e => updateParam('sort', e.target.value)}>
                    <option value="value">Highest value</option>
                    <option value="name">Name A–Z</option>
                </select>

                {hasActiveFilters && (
                    <button className="clear-btn" onClick={clearFilters}>Clear filters</button>
                )}
            </div>

            <div className="player-row player-row-header" aria-hidden="true">
                <span />
                <span>Player</span>
                <span>Position</span>
                <span className="col-age">Age</span>
                <span className="col-club">Club</span>
                <span className="col-nation">Nation</span>
                <span className="col-value">Value</span>
            </div>

            {loading && <p className="list-status">Loading players...</p>}
            {!loading && error && <p className="list-status">{error}</p>}
            {!loading && !error && players.length === 0 && (
                <div className="list-status">
                    <p>No players match these filters.</p>
                    <button className="clear-btn" onClick={clearFilters}>Clear filters</button>
                </div>
            )}

            {!loading && !error && players.map(p => (
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
                    <span className="col-value">{formatEuro(p.market_value)}</span>
                </Link>
            ))}

            {!loading && !error && hasMore && (
                <button className="load-more" onClick={loadMore} disabled={loadingMore}>
                    {loadingMore ? 'Loading...' : 'Load more players'}
                </button>
            )}
        </div>
    );
}

export default SelectPage;
