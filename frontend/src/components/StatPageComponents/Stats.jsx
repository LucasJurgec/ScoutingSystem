import { useState } from 'react';
import './Stats.css';
import { STAT_LABELS, STAT_SECTIONS, formatStat } from './StatPageComponents/statUtils';
import ExpectedStatChart from './StatPageComponents/ExpectedCompare';

const OUTFIELD_SECTIONS = ['general', 'attacking', 'defending', 'discipline'];
const GOALKEEPER_SECTIONS = ['general', 'goalkeeping', 'discipline'];

const hideImage = (e) => { e.currentTarget.style.display = 'none'; };

function ClubLabel({ row }) {
    return (
        <>
            {row.club_logo && <img className="club-btn-logo" src={row.club_logo} alt="" onError={hideImage} />}
            {row.club_name}
        </>
    );
}

// seasons = output of groupSeasons(): one entry per season, each with 1+ club rows
function Stats({ seasons, isGoalkeeper }) {
    const [seasonIndex, setSeasonIndex] = useState(seasons.length - 1); // latest season
    const [clubIndex, setClubIndex] = useState(0);

    if (seasons.length === 0) {
        return <p className="stats-empty">No season stats recorded for this player.</p>;
    }

    const season = seasons[Math.min(seasonIndex, seasons.length - 1)];
    const row = season.rows[Math.min(clubIndex, season.rows.length - 1)];
    const sections = isGoalkeeper ? GOALKEEPER_SECTIONS : OUTFIELD_SECTIONS;

    const selectSeason = (i) => {
        setSeasonIndex(i);
        setClubIndex(0); // new season -> back to its first club
    };

    return (
        <div className="stats">
            <h4 className="stats-title">Season Stats</h4>

            <div className="season-buttons">
                {seasons.map((s, i) => (
                    <button
                        key={s.season_id}
                        className={s.season_id === season.season_id ? 'season-btn active' : 'season-btn'}
                        onClick={() => selectSeason(i)}
                    >
                        {s.season_name}
                    </button>
                ))}
            </div>

            {/* more than one club that season -> pick which one */}
            {season.rows.length > 1 ? (
                <div className="club-buttons">
                    {season.rows.map((r, i) => (
                        <button
                            key={r.stat_id}
                            className={r.stat_id === row.stat_id ? 'club-btn active' : 'club-btn'}
                            onClick={() => setClubIndex(i)}
                        >
                            <ClubLabel row={r} />
                        </button>
                    ))}
                </div>
            ) : (
                <p className="stats-club"><ClubLabel row={row} /></p>
            )}

            {sections.map(id => (
                <div key={id} className="stats-section">
                    <h4 className="stats-section-title">{STAT_SECTIONS[id].title}</h4>
                    <div className="stats-grid">
                        {STAT_SECTIONS[id].keys.map(key => (
                            <p key={key}>
                                {STAT_LABELS[key]}: <b>{formatStat(key, row[key])}</b>
                            </p>
                        ))}
                    </div>
                </div>
            ))}
            <div>
                <ExpectedStatChart row={row} />
            </div>
        </div>
    );
}

export default Stats;
