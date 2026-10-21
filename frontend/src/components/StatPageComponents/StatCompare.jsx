import { useRef, useEffect, useMemo, useState } from 'react';
import * as d3 from 'd3';
import './StatPageComponents/StatCompare.css';
import { STAT_LABELS, formatStat } from './statUtils';

// 5 axes per position, all stats we actually have now
const RADAR_CONFIG = {
    GK: ['saves', 'save_pct', 'clean_sheets', 'penalty_saved', 'points_per_match'],
    CB: ['tackles_won', 'interceptions', 'goals', 'minutes_played', 'points_per_match'],
    LB: ['tackles_won', 'interceptions', 'crosses', 'assists', 'key_passes'],
    RB: ['tackles_won', 'interceptions', 'crosses', 'assists', 'key_passes'],
    DM: ['tackles_won', 'interceptions', 'key_passes', 'fouls_drawn', 'points_per_match'],
    CM: ['goals', 'assists', 'key_passes', 'xa', 'tackles_won'],
    AM: ['goals', 'assists', 'key_passes', 'xg', 'xa'],
    LM: ['goals', 'assists', 'key_passes', 'crosses', 'xa'],
    RM: ['goals', 'assists', 'key_passes', 'crosses', 'xa'],
    LW: ['goals', 'assists', 'shots_on_target', 'xg', 'xa'],
    RW: ['goals', 'assists', 'shots_on_target', 'xg', 'xa'],
    ST: ['goals', 'xg', 'shots_total', 'shots_on_target', 'assists'],
};

const COLOUR_A = '#FA5252';
const COLOUR_B = '#00cc00';

const WIDTH = 600;
const HEIGHT = 440;
const RADIUS = 140;

// Every season-club row becomes its own option. A season split across two
// clubs shows as "2024-25 (Arsenal)" and "2024-25 (Chelsea)".
function toEntries(seasons) {
    return seasons.flatMap(s =>
        s.rows.map(row => ({
            ...row,
            label: s.rows.length > 1 ? `${s.season_name} (${row.club_name})` : s.season_name,
        }))
    );
}

// default comparison: latest entry vs the latest entry from an EARLIER season
function defaultIndexB(entries) {
    const a = entries[entries.length - 1];
    for (let i = entries.length - 2; i >= 0; i--) {
        if (entries[i].season_id !== a.season_id) return i;
    }
    return -1; // only one season -> show a single shape
}

function StatCompare({ seasons, position }) {
    const entries = useMemo(() => toEntries(seasons), [seasons]);

    const [indexA, setIndexA] = useState(entries.length - 1);
    const [indexB, setIndexB] = useState(() => (entries.length ? defaultIndexB(entries) : -1));

    const axes = RADAR_CONFIG[position] ?? RADAR_CONFIG.CM;

    // Each axis is scaled to the player's best season-club row for that stat,
    // so a point on the outer ring = their career best (in our data).
    const maxes = useMemo(
        () => axes.map(key => Math.max(0, ...entries.map(e => Number(e[key]) || 0)) * 1.1),
        [axes, entries]
    );

    const seasonA = entries[indexA] ?? null;
    const seasonB = indexB >= 0 ? entries[indexB] ?? null : null;

    const svgRef = useRef(null);

    useEffect(() => {
        if (!svgRef.current) return;

        const svg = d3.select(svgRef.current);
        svg.selectAll('*').remove();

        const g = svg.append('g').attr('transform', `translate(${WIDTH / 2}, ${HEIGHT / 2})`);
        const angleSlice = (Math.PI * 2) / axes.length;

        const pointFor = (value, i) => {
            const angle = angleSlice * i - Math.PI / 2;
            const r = maxes[i] ? ((Number(value) || 0) / maxes[i]) * RADIUS : 0;
            return [r * Math.cos(angle), r * Math.sin(angle)];
        };

        // grid rings
        for (let level = 1; level <= 5; level++) {
            g.append('circle')
                .attr('r', (RADIUS / 5) * level)
                .attr('fill', 'none')
                .attr('stroke', '#ccc')
                .attr('stroke-width', 0.5);
        }

        // axis lines + labels (anchored away from the centre so long labels don't clip)
        axes.forEach((key, i) => {
            const angle = angleSlice * i - Math.PI / 2;
            const x = RADIUS * Math.cos(angle);
            const y = RADIUS * Math.sin(angle);

            g.append('line')
                .attr('x1', 0).attr('y1', 0)
                .attr('x2', x).attr('y2', y)
                .attr('stroke', '#999');

            g.append('text')
                .attr('x', x * 1.15)
                .attr('y', y * 1.15)
                .attr('text-anchor', Math.abs(x) < 1 ? 'middle' : x > 0 ? 'start' : 'end')
                .attr('dominant-baseline', 'middle')
                .attr('font-size', '14px')
                .attr('font-weight', 'bold')
                .attr('fill', 'white')
                .text(STAT_LABELS[key]);
        });

        // shared tooltip, hidden until a point is hovered
        const tooltip = g.append('text')
            .attr('text-anchor', 'middle')
            .attr('font-size', '14px')
            .attr('font-weight', 'bold')
            .attr('fill', 'white')
            .attr('opacity', 0)
            .style('pointer-events', 'none');

        const drawPolygon = (season, colour) => {
            if (!season) return;
            const values = axes.map(key => season[key]);
            const points = values.map((v, i) => pointFor(v, i));

            g.append('path')
                .attr('d', d3.line()(points) + 'Z')
                .attr('fill', colour)
                .attr('fill-opacity', 0.2)
                .attr('stroke', colour)
                .attr('stroke-width', 2)
                .style('pointer-events', 'none');

            points.forEach(([x, y], i) => {
                g.append('circle')
                    .attr('cx', x)
                    .attr('cy', y)
                    .attr('r', 4)
                    .attr('fill', colour)
                    .style('cursor', 'pointer')
                    .on('mouseover', function () {
                        d3.select(this).attr('r', 6);
                        tooltip
                            .attr('x', x)
                            .attr('y', y - 12)
                            .text(formatStat(axes[i], values[i]))
                            .attr('opacity', 1)
                            .raise();
                    })
                    .on('mouseout', function () {
                        d3.select(this).attr('r', 4);
                        tooltip.attr('opacity', 0);
                    });
            });
        };

        drawPolygon(seasonB, COLOUR_B); // B first so A sits on top
        drawPolygon(seasonA, COLOUR_A);
    }, [axes, maxes, seasonA, seasonB]);

    if (entries.length === 0) return null;

    return (
        <div className="compare">
            <h4 className="compare-title">Season Comparison</h4>

            <div className="compare-controls">
                <label>
                    <span className="swatch" style={{ background: COLOUR_A }} />
                    <select value={indexA} onChange={e => setIndexA(Number(e.target.value))}>
                        {entries.map((e, i) => (
                            <option key={e.stat_id} value={i}>{e.label}</option>
                        ))}
                    </select>
                </label>

                <span>vs</span>

                <label>
                    <span className="swatch" style={{ background: COLOUR_B }} />
                    <select value={indexB} onChange={e => setIndexB(Number(e.target.value))}>
                        <option value={-1}>None</option>
                        {entries.map((e, i) => (
                            <option key={e.stat_id} value={i}>{e.label}</option>
                        ))}
                    </select>
                </label>
            </div>

            <svg ref={svgRef} className="radar" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} />
        </div>
    );
}

export default StatCompare;
