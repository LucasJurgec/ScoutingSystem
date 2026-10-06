import { useState, useEffect, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import './StatPage.css';
import PlayerCard from './PlayerCard';
import Position from './Position';
import Stats from './Stats';
import MarketValue from './MarketValue';
import StatCompare from './StatCompare';
import { groupSeasons, primaryPosition } from './statUtils';

// Set VITE_API_URL in frontend/.env when it's deployed
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function StatPage() {
    const { playerId } = useParams();
    const [player, setPlayer] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        setLoading(true);
        setError(null);
        axios.get(`${API_BASE}/players/${playerId}`)
            .then(response => setPlayer(response.data))
            .catch(err => {
                console.error(err);
                setError(err.response?.status === 404
                    ? 'Player not found.'
                    : 'Could not load this player. Check the API is running.');
            })
            .finally(() => setLoading(false));
    }, [playerId]);

    // one entry per season, each holding 1+ club rows, oldest -> newest
    const seasons = useMemo(() => (player ? groupSeasons(player.stats) : []), [player]);

    if (loading) return <div className="stat-page-status">Loading...</div>;
    if (error) return <div className="stat-page-status">{error}</div>;
    if (!player) return null;

    const primary = primaryPosition(player);
    const isGoalkeeper = player.position_general === 'Goalkeeper';

    return (
        <div className="stat-page">
            <div className="left-panel">
                <PlayerCard player={player} />
                <Position primary={primary} secondary={player.positions} />
                <MarketValue value={player.market_value} />
            </div>

            <div className="right-panel">
                {/* keys reset the selected season when you move to another player */}
                <Stats
                    key={`stats-${player.player_id}`}
                    seasons={seasons}
                    isGoalkeeper={isGoalkeeper}
                />
                <StatCompare
                    key={`radar-${player.player_id}`}
                    seasons={seasons}
                    position={primary}
                />
            </div>
        </div>
    );
}

export default StatPage;
