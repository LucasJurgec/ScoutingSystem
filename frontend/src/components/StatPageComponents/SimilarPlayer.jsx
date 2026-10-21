import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { API_BASE } from '../../api';
import { downloadSimilarPdf } from './SimilarPlayersPDF';

function SimilarPlayers({ playerId }) {
    const [results, setResults] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [generating, setGenerating] = useState(false);

    useEffect(() => {
        setLoading(true);
        setError(null);
        axios.get(`${API_BASE}/players/${playerId}/similar`)
            .then(res => setResults(res.data.results))
            .catch(err => {
                setError(err.response?.status === 404
                    ? 'No similar-player data for this player.'
                    : 'Could not load similar players.');
            })
            .finally(() => setLoading(false));
    }, [playerId]);

    const handlePdf = async () => {
        setGenerating(true);
        try {
            await downloadSimilarPdf(playerId, results);
        } catch (e) {
            console.error('PDF failed', e);
        } finally {
            setGenerating(false);
        }
    };

    if (loading) return <div>Loading...</div>;
    if (error) return <div>{error}</div>;
    if (!results?.length) return <div>No similar players found.</div>;

    return (
        <div>
            <ul className="similar-players">
                {results.map(p => (
                    <li key={p.player_id}>
                        <Link to={`/player/${p.player_id}`}>{p.name}</Link>
                        <span> — {p.similarity}% similar</span>
                    </li>
                ))}
            </ul>
            <button className="nav-btn" onClick={handlePdf} disabled={generating}>
                {generating ? 'Generating PDF…' : 'Download PDF report'}
            </button>
        </div>
    );
}

export default SimilarPlayers;