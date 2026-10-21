import { formatEuro } from './StatPageComponents/statUtils';

// Renders any JSON object as a labelled list. Used for contract_data and
// the scouting report, since their keys vary from player to player.

const MONEY_HINTS = ['amount', 'fee', 'bonus', 'wage', 'value', 'price', 'salary', 'clause', '_eur'];
const PERCENT_HINTS = ['percent', 'percentage', 'pct'];

const isPlainObject = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);

// "sell_on_clause" -> "Sell on clause"
export const humanize = (key) => {
    const text = key
        .replace(/_eur$/, '')                  // amount_eur -> amount (formatted in € anyway)
        .replace(/([a-z])([A-Z])/g, '$1 $2')
        .replace(/_/g, ' ')
        .toLowerCase();
    return text.charAt(0).toUpperCase() + text.slice(1);
};

export const formatDate = (value) =>
    new Date(value).toLocaleDateString('en-AU', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });

function formatValue(key, value) {
    const k = key.toLowerCase();
    // a key that's there but null means "confirmed none"
    if (value === null || value === undefined) return 'None';
    if (typeof value === 'boolean') return value ? 'Yes' : 'No';
    if (typeof value === 'number') {
        if (PERCENT_HINTS.some(h => k.includes(h))) return `${value}%`;
        if (value >= 1000 && MONEY_HINTS.some(h => k.includes(h))) return formatEuro(value);
        return value.toLocaleString('en-AU');
    }
    if (typeof value === 'string') {
        if (/^\d{4}-\d{2}-\d{2}/.test(value)) return formatDate(value);
        if (/^[a-z]+(_[a-z]+)+$/.test(value)) return value.replace(/_/g, ' '); // "any_club" -> "any club"
        return value;
    }
    return String(value);
}

function renderValue(key, value) {
    if (Array.isArray(value)) {
        if (value.length === 0) return 'None';
        return (
            <ul className="data-list">
                {value.map((item, i) => (
                    <li key={i}>{isPlainObject(item) ? <DataView data={item} /> : formatValue(key, item)}</li>
                ))}
            </ul>
        );
    }
    if (isPlainObject(value)) {
        return Object.keys(value).length ? <DataView data={value} nested /> : 'None';
    }
    return formatValue(key, value);
}

function DataView({ data, skip = [], nested = false }) {
    const entries = Object.entries(data).filter(([key]) => !skip.includes(key));
    if (entries.length === 0) return null;

    return (
        <dl className={nested ? 'data-view nested' : 'data-view'}>
            {entries.map(([key, value]) => (
                <div key={key} className="data-row">
                    <dt>{humanize(key)}</dt>
                    <dd>{renderValue(key, value)}</dd>
                </div>
            ))}
        </dl>
    );
}

export default DataView;
