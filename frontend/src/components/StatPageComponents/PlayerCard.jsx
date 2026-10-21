import './PlayerCard.css';
import { Link } from 'react-router-dom';

const SILHOUETTE = '/images/PlayerSilhouette.png';

// "2001-09-05" -> "5 Sep 2001"
const formatDate = (iso) =>
    new Date(iso).toLocaleDateString('en-AU', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });

// 185 -> 6'1"
const toFeetInches = (cm) => {
    const inches = Math.round(cm / 2.54);
    return `${Math.floor(inches / 12)}'${inches % 12}"`;
};

// hide a broken flag/logo instead of showing a broken image icon
const hideImage = (e) => { e.currentTarget.style.display = 'none'; };

function PlayerCard({ player }) {
    const {
        first_name, last_name, date_of_birth, age, height, player_img,
        nation_name, nation_flag, club_name, club_logo, league_name, status,
    } = player;

    // free agents / retired players have no club
    const clubText = club_name ?? (status === 'Active' ? 'Unknown' : status);

    return (
        <div>
            <div className="player-header">
                <img
                    className="img-profile-pic"
                    src={player_img || SILHOUETTE}
                    alt={`${first_name ?? ''} ${last_name}`.trim()}
                    onError={(e) => {
                        if (!e.currentTarget.src.endsWith(SILHOUETTE)) e.currentTarget.src = SILHOUETTE;
                    }}
                />
                <div className="header-info">
                    {first_name && <h4 className="name">{first_name}</h4>}
                    <h4 className="name">{last_name}</h4>

                    <p>DOB: <b>{formatDate(date_of_birth)}</b> Age: <b>{age}</b></p>
                    <p>
                        Height:{' '}
                        {height
                            ? <><b>{height}</b> cm / <b>{toFeetInches(height)}</b></>
                            : <b>–</b>}
                    </p>
                </div>
            </div>

            <div className="nation-club-container">
                <div className="nation">
                    <p>Nation: <b>{nation_name}</b></p>
                    {nation_flag && (
                        <img className="nation-flag" src={nation_flag} alt={nation_name} onError={hideImage} />
                    )}
                </div>

                <div className="club">
                    <p>Current Club: <b>{clubText}</b></p>
                    {club_logo && (
                        <img className="club-logo" src={club_logo} alt={club_name} onError={hideImage} />
                    )}
                </div>

                {club_name && league_name && (
                    <p>League: <b>{league_name}</b></p>
                )}

                <Link to="/" className="back-button">&larr; Back to Players List</Link>
            </div>
        </div>
    );
}

export default PlayerCard;
