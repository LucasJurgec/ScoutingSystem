import { useState, useEffect, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { API_BASE } from '../api';
import './StatPage.css';
import PlayerCard from './PlayerCard';
import Position from './Position';
import Stats from './Stats';
import MarketValue from './MarketValue';
import StatCompare from './StatCompare';
import InfoModal from './InfoModal';
import ContractInfo from './ContractInfo';
import ScoutReport from './ScoutReport';
import { groupSeasons, primaryPosition } from './statUtils';
import SimilarPlayers from './SimilarPlayer';

function StatPage() {
    const { playerId } = useParams();
    const [player, setPlayer] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [openPanel, setOpenPanel] = useState(null); // null | 'contract' | 'report'

    useEffect(() => {
        setLoading(true);
        setError(null);
        setOpenPanel(null); 
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
    const name = [player.first_name, player.last_name].filter(Boolean).join(' ');
    const closePanel = () => setOpenPanel(null);

    return (
        <div className="stat-page">
            <div className="left-panel">
                <PlayerCard player={player} />
                <div className="detail-buttons">
                    <button className="detail-btn" onClick={() => setOpenPanel('contract')}>Contract info</button>
                    <button className="detail-btn" onClick={() => setOpenPanel('report')}>Scouting report</button>
                    <button className="detail-btn" onClick={() => setOpenPanel('similar')}>Similar players</button>
                </div>
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

            {/* contract, report and similarity model are only fetched when their pop-up opens */}
            <InfoModal title={`Contract info: ${name}`} open={openPanel === 'contract'} onClose={closePanel}>
                <ContractInfo playerId={player.player_id} />
            </InfoModal>
            <InfoModal title={`Scouting report: ${name}`} open={openPanel === 'report'} onClose={closePanel}>
                <ScoutReport playerId={player.player_id} />
            </InfoModal>
            <InfoModal title={`Similar players: ${name}`} open={openPanel === 'similar'} onClose={closePanel}>
                <SimilarPlayers playerId={player.player_id} />
            </InfoModal>
        </div>
    );
}

export default StatPage;
