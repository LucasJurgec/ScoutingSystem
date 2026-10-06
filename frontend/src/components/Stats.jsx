import { useState } from 'react';
import './Stats.css';
import { STAT_LABELS, STAT_SECTIONS, formatStat } from './statUtils';

const OUTFIELD_SECTIONS = ['general', 'attacking', 'defending', 'discipline'];
const GOALKEEPER_SECTIONS = ['general', 'goalkeeping', 'discipline'];

function Stats({ seasons, isGoalkeeper }) {
    // default to the most recent season
    const [index, setIndex] = useState(seasons.length - 1);

    if (seasons.length === 0) {
        return <p className="stats-empty">No season stats recorded for this player.</p>;
    }

    const season = seasons[Math.min(index, seasons.length - 1)];
    const sections = isGoalkeeper ? GOALKEEPER_SECTIONS : OUTFIELD_SECTIONS;

    return (
        <div className="stats">
            <h4 className="stats-title">Season Stats</h4>

            <div className="season-buttons">
                {seasons.map((s, i) => (
                    <button
                        key={s.season_id}
                        className={s.season_id === season.season_id ? 'season-btn active' : 'season-btn'}
                        onClick={() => setIndex(i)}
                    >
                        {s.season_name}
                    </button>
                ))}
            </div>

            <p className="stats-club">{season.clubs.join(' / ')}</p>

            {sections.map(id => (
                <div key={id} className="stats-section">
                    <h4 className="stats-section-title">{STAT_SECTIONS[id].title}</h4>
                    <div className="stats-grid">
                        {STAT_SECTIONS[id].keys.map(key => (
                            <p key={key}>
                                {STAT_LABELS[key]}: <b>{formatStat(key, season[key])}</b>
                            </p>
                        ))}
                    </div>
                </div>
            ))}
        </div>
    );
}

export default Stats;
