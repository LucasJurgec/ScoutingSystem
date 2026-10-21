import { useRef, useEffect } from 'react';
import * as d3 from 'd3';
import './StatPageComponents/ExpectedCompare.css';


const BARS = [
    { label: 'Goals',   actual: 'goals',   expected: 'xg' },
    { label: 'Assists', actual: 'assists', expected: 'xa' },
];

function ExpectedStatChart({ row }) {
    const ref = useRef(null);
    const tipRef = useRef(null);

    // season has goals but no xG/xA -> draw nothing
    const hasXg = row.xg != null && row.xa != null;

    useEffect(() => {
        if (!hasXg) return;

        const data = BARS.map(b => ({
            label: b.label,
            actual: Number(row[b.actual]) || 0,
            expected: Number(row[b.expected]) || 0,
        }));

        const W = 280, H = 210, m = { top: 20, right: 10, bottom: 28, left: 30 };
        const iw = W - m.left - m.right;
        const ih = H - m.top - m.bottom;

        const svg = d3.select(ref.current);
        svg.selectAll('*').remove(); // clear previous season's render

        const g = svg
            .attr('viewBox', `0 0 ${W} ${H}`)
            .append('g')
            .attr('transform', `translate(${m.left},${m.top})`);

        const x = d3.scaleBand()
            .domain(data.map(d => d.label))
            .range([0, iw])
            .padding(0.4);

        const max = d3.max(data, d => Math.max(d.actual, d.expected)) * 1.15 || 1;
        const y = d3.scaleLinear().domain([0, max]).range([ih, 0]);

        // y axis
        g.append('g')
            .call(d3.axisLeft(y).ticks(5))
            .attr('class', 'stat-axis');

        // x axis
        g.append('g')
            .attr('transform', `translate(0,${ih})`)
            .call(d3.axisBottom(x))
            .attr('class', 'stat-axis');

        // faint gridlines across the plot
        g.append('g')
            .attr('class', 'stat-grid')
            .call(d3.axisLeft(y).ticks(5).tickSize(-iw).tickFormat(''));

        // actual bars
        g.selectAll('.stat-bar')
            .data(data)
            .join('rect')
            .attr('class', 'stat-bar')
            .attr('x', d => x(d.label))
            .attr('y', d => y(d.actual))
            .attr('width', x.bandwidth())
            .attr('height', d => ih - y(d.actual))
            .attr('rx', 4)
            .on('mouseover', (event, d) => {
                const tip = d3.select(tipRef.current);
                tip.style('opacity', 1)
                .html(`${d.label}: ${d.actual}<br>Expected: ${d.expected.toFixed(1)}`);
            })
            .on('mousemove', (event) => {
                const [mx, my] = d3.pointer(event, ref.current.parentNode);
                d3.select(tipRef.current)
                .style('left', `${mx + 12}px`)
                .style('top', `${my + 12}px`);
            })
            .on('mouseout', () => {
                d3.select(tipRef.current).style('opacity', 0);
            });

        // expected markers (the horizontal line across each bar)
        g.selectAll('.stat-mark')
            .data(data)
            .join('line')
            .attr('class', 'stat-mark')
            .attr('x1', d => x(d.label) - 4)
            .attr('x2', d => x(d.label) + x.bandwidth() + 4)
            .attr('y1', d => y(d.expected))
            .attr('y2', d => y(d.expected));


        // expected value labels
        g.selectAll('.stat-mark-label')
            .data(data)
            .join('text')
            .attr('class', 'stat-mark-label')
            .attr('x', d => x(d.label) + x.bandwidth() / 2)
            .attr('y', d => y(d.expected) - 6)
            .attr('text-anchor', 'middle')
            .text(d => d.expected.toFixed(1));
    }, [row, hasXg]);

    if (!hasXg) return null;

    return (
        <div className="stat-chart">
            <h4 className="stats-section-title">Output vs Expected Output</h4>
            <svg ref={ref} className="stat-chart-svg" />
            <div ref={tipRef} className="stat-tooltip" />
            <div className="stat-chart-legend">
                <span><i className="swatch swatch-bar" /> Actual</span>
                <span><i className="swatch swatch-mark" /> Expected</span>
            </div>
        </div>
    );
}

export default ExpectedStatChart;