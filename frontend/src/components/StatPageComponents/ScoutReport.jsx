import { useApi } from '../../api';
import DataView, { humanize } from '../DataView';

// Fields holding the written report. Any other long string counts too.
const TEXT_KEYS = ['report_text', 'content', 'summary', 'report', 'notes', 'text', 'body'];
const HIDDEN_KEYS = ['player_id', '_id', 'embedding'];

const isLongText = (key, value) =>
    typeof value === 'string' && (value.length > 150 || TEXT_KEYS.includes(key.toLowerCase()));

// Turns the report text into blocks:
//   "Strengths:"  -> heading
//   "- something" -> bullet (consecutive bullets share one list)
//   anything else -> paragraph
// Lines are trimmed, so the indentation in the stored text doesn't matter.
function parseReport(text) {
    const blocks = [];
    text.split('\n').map(line => line.trim()).forEach(line => {
        if (!line) return;
        if (/^[-•*]\s+/.test(line)) {
            const item = line.replace(/^[-•*]\s+/, '');
            const last = blocks[blocks.length - 1];
            if (last?.type === 'list') last.items.push(item);
            else blocks.push({ type: 'list', items: [item] });
        } else if (line.endsWith(':') && line.length <= 40) {
            blocks.push({ type: 'heading', text: line.slice(0, -1) });
        } else {
            blocks.push({ type: 'para', text: line });
        }
    });
    return blocks;
}

// green for strengths, red for weaknesses/concerns
const toneOf = (heading) => {
    if (/strength/i.test(heading)) return 'pos';
    if (/weakness|concern|risk/i.test(heading)) return 'neg';
    return '';
};

function ReportBody({ text }) {
    let tone = '';
    return parseReport(text).map((block, i) => {
        if (block.type === 'heading') {
            tone = toneOf(block.text);
            return <h4 key={i} className={`report-heading ${tone}`}>{block.text}</h4>;
        }
        if (block.type === 'list') {
            return (
                <ul key={i} className={`report-list ${tone}`}>
                    {block.items.map((item, j) => <li key={j}>{item}</li>)}
                </ul>
            );
        }
        return <p key={i} className="report-para">{block.text}</p>;
    });
}

function ScoutReport({ playerId }) {
    const { data, loading, error } = useApi(`/players/${playerId}/report`);

    if (loading) return <p className="info-status">Loading scouting report...</p>;
    if (error) {
        return (
            <p className="info-status">
                {error.response?.status === 503
                    ? 'Scouting reports are unavailable right now (MongoDB could not be reached).'
                    : 'Could not load the scouting report. Check the API is running.'}
            </p>
        );
    }
    if (!data) return <p className="info-status">No scouting report on file for this player.</p>;

    // split the document into details (date, source...) and the written report
    const details = {};
    const texts = [];
    Object.entries(data).forEach(([key, value]) => {
        if (HIDDEN_KEYS.includes(key)) return;
        if (isLongText(key, value)) texts.push([key, value]);
        else details[key] = value;
    });

    return (
        <>
            <DataView data={details} />
            {texts.map(([key, value]) => (
                <div key={key} className="report-text">
                    {texts.length > 1 && <h4 className="info-subtitle">{humanize(key)}</h4>}
                    <ReportBody text={value} />
                </div>
            ))}
        </>
    );
}

export default ScoutReport;
