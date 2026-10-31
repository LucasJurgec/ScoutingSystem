import { useApi } from '../../api';
import { formatEuro } from './statUtils';
import { formatDate } from '../DataView';

// null fee = not known, 0 = free transfer
const feeText = (fee) => {
    if (fee == null) return 'Fee unknown';
    if (Number(fee) === 0) return 'Free transfer';
    return formatEuro(fee);
};

function Club({ name, logo }) {
    return (
        <span className="transfer-club">
            {logo && <img src={logo} alt="" onError={e => { e.currentTarget.style.visibility = 'hidden'; }} />}
            <span>{name ?? 'Unknown club'}</span>
        </span>
    );
}

function TransferHistory({ playerId }) {
    const { data, loading, error } = useApi(`/players/${playerId}/transfers`);

    if (loading) return <p className="info-status">Loading transfer history...</p>;
    if (error) return <p className="info-status">Could not load transfer history. Check the API is running.</p>;
    if (!data?.length) return <p className="info-status">No transfers on record for this player.</p>;

    const knownFees = data.filter(t => t.transfer_fee != null);
    const totalFees = knownFees.reduce((sum, t) => sum + Number(t.transfer_fee), 0);

    return (
        <>
            <p className="info-meta transfer-summary">
                {data.length} transfer{data.length === 1 ? '' : 's'}
                {totalFees > 0 && ` · ${formatEuro(totalFees)} in known fees`}
                {knownFees.length < data.length && ` · ${data.length - knownFees.length} fee${data.length - knownFees.length === 1 ? '' : 's'} unknown`}
            </p>

            <ul className="transfer-list">
                {data.map((t, i) => (
                    <li key={t.transfer_id ?? i} className="transfer">
                        <span className="transfer-date">
                            {t.transfer_date ? formatDate(t.transfer_date) : 'Date unknown'}
                        </span>
                        <span className="transfer-move">
                            <Club name={t.from_club_name} logo={t.from_club_logo} />
                            <span className="transfer-arrow" aria-label="to">→</span>
                            <Club name={t.to_club_name} logo={t.to_club_logo} />
                        </span>
                        <span className={t.transfer_fee == null ? 'transfer-fee unknown' : 'transfer-fee'}>
                            {feeText(t.transfer_fee)}
                        </span>
                    </li>
                ))}
            </ul>
        </>
    );
}

export default TransferHistory;
