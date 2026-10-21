import { useApi } from '../api';
import { formatEuro } from './StatPageComponents/statUtils';
import DataView, { formatDate, humanize } from './DataView';

// "1 yr 8 mos left", flagged when under 12 months
function timeRemaining(expiry) {
    if (!expiry) return null;
    const end = new Date(expiry);
    const now = new Date();
    const months = (end.getFullYear() - now.getFullYear()) * 12 + (end.getMonth() - now.getMonth());
    if (end < now) return { text: 'Expired', warn: true };
    if (months < 1) return { text: 'Under 1 month left', warn: true };
    const years = Math.floor(months / 12);
    const rest = months % 12;
    const parts = [];
    if (years) parts.push(`${years} yr${years > 1 ? 's' : ''}`);
    if (rest) parts.push(`${rest} mo${rest > 1 ? 's' : ''}`);
    return { text: `${parts.join(' ')} left`, warn: months < 12 };
}

// ---------- clauses (contract_data JSON) ----------

const CLAUSE_TITLES = {
    sell_on: 'Sell-on clause',
    buyback: 'Buy-back clause',
    appearance_bonus: 'Appearance bonus',
    loyalty_bonus: 'Loyalty bonus',
};

// One readable line per clause type, following contract_clauses.schema.json.
// The backend adds from_club_name / club_name next to the ids.
function describeClause(c) {
    switch (c.type) {
        case 'sell_on':
            return `${c.percentage}% of a future transfer fee goes to ${c.from_club_name ?? `club #${c.from_club_id}`}`;
        case 'buyback': {
            const club = c.club_name ?? 'The selling club';
            const until = c.valid_until ? `, valid until ${formatDate(c.valid_until)}` : '';
            return `${club} can re-sign the player for ${formatEuro(c.amount_eur)}${until}`;
        }
        case 'appearance_bonus':
            return `${formatEuro(c.amount_eur)} once he reaches ${c.appearances_required} appearances`;
        case 'loyalty_bonus':
            return formatEuro(c.amount_eur);
        default:
            return null;
    }
}

function ClauseList({ clauses }) {
    return (
        <ul className="clause-list">
            {clauses.map((c, i) => {
                const { type, ...rest } = c;
                const title = type === 'custom' ? c.title : (CLAUSE_TITLES[type] ?? humanize(type ?? 'clause'));
                const line = describeClause(c);
                return (
                    <li key={i} className="clause">
                        <div className="clause-title">{title}</div>
                        {type === 'custom' ? (
                            <>
                                <p className="clause-text">{c.description}</p>
                                {c.details && Object.keys(c.details).length > 0 && <DataView data={c.details} nested />}
                            </>
                        ) : line ? (
                            <p className="clause-text">{line}</p>
                        ) : (
                            // a clause type we don't know about yet: just list its fields
                            <DataView data={rest} nested />
                        )}
                    </li>
                );
            })}
        </ul>
    );
}

function ContractInfo({ playerId }) {
    const { data, loading, error } = useApi(`/players/${playerId}/contract`);

    if (loading) return <p className="info-status">Loading contract info...</p>;
    if (error) return <p className="info-status">Could not load contract info. Check the API is running.</p>;
    if (!data) return <p className="info-status">No contract information on file for this player.</p>;

    const { contract_start, contract_expiry, weekly_wage, release_clause, contract_data } = data;
    const remaining = timeRemaining(contract_expiry);
    const clauses = Array.isArray(contract_data?.clauses) ? contract_data.clauses : null;

    return (
        <>
            <dl className="data-view">
                <div className="data-row">
                    <dt>Contract start</dt>
                    <dd>{contract_start ? formatDate(contract_start) : '–'}</dd>
                </div>
                <div className="data-row">
                    <dt>Contract expiry</dt>
                    <dd>
                        {contract_expiry ? formatDate(contract_expiry) : '–'}
                        {remaining && (
                            <span className={remaining.warn ? 'info-tag warn' : 'info-tag'}>{remaining.text}</span>
                        )}
                    </dd>
                </div>
                <div className="data-row">
                    <dt>Weekly wage</dt>
                    <dd>{weekly_wage != null ? `${formatEuro(weekly_wage)} / week` : '–'}</dd>
                </div>
                <div className="data-row">
                    <dt>Release clause</dt>
                    <dd>{release_clause != null ? formatEuro(release_clause) : '–'}</dd>
                </div>
            </dl>

            {/* no JSON file = no known extra clauses */}
            {contract_data && (
                <>
                    <h4 className="info-subtitle">
                        Extra clauses
                        {contract_data.last_updated && (
                            <span className="info-meta"> · updated {formatDate(contract_data.last_updated)}</span>
                        )}
                    </h4>
                    {clauses
                        ? <ClauseList clauses={clauses} />
                        : <DataView data={contract_data} skip={['player_id', 'last_updated']} />}
                </>
            )}
        </>
    );
}

export default ContractInfo;
