import axios from 'axios';
import { jsPDF } from 'jspdf';
import { API_BASE } from '../../api';
import { formatEuro } from './statUtils';
import { humanize, formatDate } from '../DataView';

async function fetchPlayer(id) {
    const [core, contract, report] = await Promise.all([
        axios.get(`${API_BASE}/players/${id}`).then(r => r.data).catch(() => null),
        axios.get(`${API_BASE}/players/${id}/contract`).then(r => r.data).catch(() => null),
        axios.get(`${API_BASE}/players/${id}/report`).then(r => r.data).catch(() => null),
    ]);
    return { core, contract, report };
}

const SKIP = ['player_id', '_id', 'embedding', 'last_updated'];
const MONEY = ['amount', 'fee', 'bonus', 'wage', 'value', 'price', 'salary', 'clause', '_eur'];

function fmt(key, v) {
    const k = key.toLowerCase();
    if (v === null || v === undefined || v === '') return 'None';
    if (typeof v === 'boolean') return v ? 'Yes' : 'No';
    if (typeof v === 'number') return (v >= 1000 && MONEY.some(h => k.includes(h))) ? formatEuro(v) : v.toLocaleString('en-AU');
    if (typeof v === 'string' && /^\d{4}-\d{2}-\d{2}/.test(v)) return formatDate(v);
    return String(v);
}

// flatten any nested object/array into ["Label: value", ...] lines with indentation
function toLines(obj, indent = 0) {
    const out = [];
    const pad = '  '.repeat(indent);
    for (const [k, v] of Object.entries(obj)) {
        if (SKIP.includes(k)) continue;
        if (v !== null && typeof v === 'object' && !Array.isArray(v)) {
        out.push(`${pad}${humanize(k)}:`);
        out.push(...toLines(v, indent + 1));
        } else if (Array.isArray(v)) {
        if (!v.length) { out.push(`${pad}${humanize(k)}: None`); continue; }
        out.push(`${pad}${humanize(k)}:`);
        v.forEach(item => {
            if (item && typeof item === 'object') out.push(...toLines(item, indent + 1));
            else out.push(`${'  '.repeat(indent + 1)}• ${fmt(k, item)}`);
        });
        } else {
        out.push(`${pad}${humanize(k)}: ${fmt(k, v)}`);
        }
    }
    return out;
}

export async function downloadSimilarPdf(targetId, matches) {
    const ids = [{ id: targetId, tag: 'Target player' },
                ...matches.map(m => ({ id: m.player_id, tag: `Similar player — ${m.similarity}% match` }))];
    const bundles = await Promise.all(ids.map(async x => ({ ...x, ...(await fetchPlayer(x.id)) })));

    const doc = new jsPDF({ unit: 'pt', format: 'a4' });
    const M = 40;                              // margin
    const W = doc.internal.pageSize.getWidth();
    const H = doc.internal.pageSize.getHeight();
    let y = M;

    const need = (h) => { if (y + h > H - M) { doc.addPage(); y = M; } };
    const write = (text, { size = 10, bold = false, color = '#111', gap = 2, indent = 0 } = {}) => {
        doc.setFont('helvetica', bold ? 'bold' : 'normal');
        doc.setFontSize(size);
        doc.setTextColor(color);
        const lines = doc.splitTextToSize(text, W - 2 * M - indent);   // wrap long text
        lines.forEach(line => {
        need(size + gap);
        doc.text(line, M + indent, y);
        y += size + gap;
        });
    };

    const targetName = bundles[0].core
        ? [bundles[0].core.first_name, bundles[0].core.last_name].filter(Boolean).join(' ')
        : 'player';

    write(`Similar players — ${targetName}`, { size: 16, bold: true });
    write(`Generated ${new Date().toLocaleString('en-AU')} · TheScoutSystem`, { size: 9, color: '#555', gap: 6 });

    for (const b of bundles) {
        if (!b.core) continue;
        y += 8;
        need(60);
        doc.setDrawColor('#cccccc');
        doc.line(M, y, W - M, y);               // divider between players
        y += 12;

        const club = b.core.club_name ?? b.core.status;
        const meta = [b.core.position_advanced || b.core.position_general, club, b.core.league_name].filter(Boolean).join('  ·  ');

        write(b.tag, { size: 8, color: '#1a73e8' });
        write([b.core.first_name, b.core.last_name].filter(Boolean).join(' '), { size: 13, bold: true });
        write(meta + (b.core.market_value ? `  ·  ${formatEuro(b.core.market_value)}` : ''), { size: 9, color: '#555', gap: 4 });

        write('Contract', { size: 10, bold: true, gap: 3 });
        if (b.contract) toLines(b.contract).forEach(l => write(l, { size: 9, indent: 6 }));
        else write('No contract information on file.', { size: 9, color: '#999', indent: 6 });

        write('Scouting report', { size: 10, bold: true, gap: 3 });
        if (b.report) toLines(b.report).forEach(l => write(l, { size: 9, indent: 6 }));
        else write('No scouting report on file.', { size: 9, color: '#999', indent: 6 });
    }

    doc.save(`similar_players_${targetName.replace(/\s+/g, '_')}.pdf`);
}