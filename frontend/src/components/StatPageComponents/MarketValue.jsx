import { useEffect, useMemo, useRef, useState } from 'react';
import * as d3 from 'd3';
import { formatDate } from '../DataView';
import './MarketValue.css';

// Rough fixed rates, fine for the prototype
const CURRENCIES = [
    { code: 'EUR', rate: 1 },
    { code: 'GBP', rate: 0.863 },
    { code: 'AUD', rate: 1.66 },
];

const MAX_POINTS = 20;  // only chart the most recent 20 valuations
const HEIGHT = 220;
const MARGIN = { top: 14, right: 16, bottom: 28, left: 52 };

// 85000000 -> "EUR 85M", 300000 -> "EUR 300K"
const formatMoney = (value, code) =>
    new Intl.NumberFormat('en-AU', {
        style: 'currency',
        currency: code,
        currencyDisplay: 'code',
        notation: 'compact',
        minimumFractionDigits: 0,
        maximumFractionDigits: 1,
    }).format(value);

// axis labels: 85000000 -> "€85M"
const shortEuro = (v) => `€${d3.format('.3~s')(v).replace('G', 'B').replace('k', 'K')}`;

function MarketValue({ value, history = [] }) {
    const wrapRef = useRef(null);
    const svgRef = useRef(null);
    const [width, setWidth] = useState(0);
    const [hoverIndex, setHoverIndex] = useState(null);

    // oldest -> newest, then keep the last 10
    const allPoints = useMemo(() => (history ?? [])
        .filter(h => h.market_value != null && h.value_date)
        .map(h => ({ date: new Date(h.value_date), value: Number(h.market_value), raw: h.value_date }))
        .sort((a, b) => a.date - b.date), [history]);
    const points = useMemo(() => allPoints.slice(-MAX_POINTS), [allPoints]);
    const capped = allPoints.length > MAX_POINTS;

    // chart follows the width of its container
    useEffect(() => {
        const el = wrapRef.current;
        if (!el) return;
        const ro = new ResizeObserver(([entry]) => setWidth(Math.floor(entry.contentRect.width)));
        ro.observe(el);
        return () => ro.disconnect();
    }, []);

    useEffect(() => setHoverIndex(null), [history]); // new player -> clear the tooltip

    const scales = useMemo(() => {
        if (!width || points.length === 0) return null;
        const innerW = width - MARGIN.left - MARGIN.right;
        const innerH = HEIGHT - MARGIN.top - MARGIN.bottom;

        let [x0, x1] = d3.extent(points, d => d.date);
        if (+x0 === +x1) { // a single valuation: give it some room either side
            x0 = d3.timeMonth.offset(x0, -6);
            x1 = d3.timeMonth.offset(x1, 6);
        }
        const x = d3.scaleTime().domain([x0, x1]).range([0, innerW]);

        const [lo, hi] = d3.extent(points, d => d.value);
        const pad = (hi - lo) * 0.15 || hi * 0.15 || 1;
        const y = d3.scaleLinear()
            .domain([Math.max(0, lo - pad), hi + pad])
            .nice(4)
            .range([innerH, 0]);

        return { x, y, innerW, innerH };
    }, [width, points]);

    // draw axes, grid, line and points with d3
    useEffect(() => {
        const svg = d3.select(svgRef.current);
        svg.selectAll('*').remove();
        if (!scales) return;
        const { x, y, innerW, innerH } = scales;

        const g = svg.append('g').attr('transform', `translate(${MARGIN.left},${MARGIN.top})`);

        g.append('g')
            .attr('class', 'mv-grid')
            .call(d3.axisLeft(y).ticks(4).tickSize(-innerW).tickPadding(8).tickFormat(shortEuro))
            .call(axis => axis.select('.domain').remove());

        g.append('g')
            .attr('class', 'mv-axis')
            .attr('transform', `translate(0,${innerH})`)
            .call(d3.axisBottom(x)
                .ticks(Math.max(2, Math.min(points.length, Math.floor(innerW / 70))))
                .tickFormat(d3.timeFormat("%b '%y"))
                .tickSizeOuter(0));

        g.append('path')
            .datum(points)
            .attr('class', 'mv-line')
            .attr('d', d3.line().x(d => x(d.date)).y(d => y(d.value)));

        g.selectAll('circle.mv-point')
            .data(points)
            .join('circle')
            .attr('class', 'mv-point')
            .attr('cx', d => x(d.date))
            .attr('cy', d => y(d.value))
            .attr('r', 4);
    }, [scales, points]);

    // hover: snap to the nearest valuation along the x axis
    const handlePointerMove = (e) => {
        if (!scales) return;
        const rect = svgRef.current.getBoundingClientRect();
        const px = e.clientX - rect.left - MARGIN.left;
        const i = d3.leastIndex(points, d => Math.abs(scales.x(d.date) - px));
        setHoverIndex(i ?? null);
    };

    // keyboard: arrow keys step through the points
    const handleKeyDown = (e) => {
        if (!points.length) return;
        if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
            e.preventDefault();
            const step = e.key === 'ArrowRight' ? 1 : -1;
            setHoverIndex(i => Math.min(points.length - 1, Math.max(0, (i ?? points.length - 1) + step)));
        } else if (e.key === 'Escape') {
            setHoverIndex(null);
        }
    };

    const hovered = scales && hoverIndex != null ? points[hoverIndex] : null;
    const prev = hovered && hoverIndex > 0 ? points[hoverIndex - 1] : null;
    const hx = hovered ? scales.x(hovered.date) : 0;
    const hy = hovered ? scales.y(hovered.value) : 0;
    const change = prev ? hovered.value - prev.value : null;

    const first = points[0];
    const last = points[points.length - 1];
    const ariaLabel = points.length
        ? `Market value chart, ${points.length} valuations from ${formatDate(first.raw)} (${shortEuro(first.value)}) to ${formatDate(last.raw)} (${shortEuro(last.value)}). Use the arrow keys to read each value.`
        : 'No market value history';

    return (
        <div className="market-container">
            <p className="market-title"><b>Current Market Value</b></p>
            {value == null
                ? <p>Unknown</p>
                : (
                    <p className="market-current">
                        <span className="market-current-main">{formatMoney(value, 'EUR')}</span>
                        {CURRENCIES.filter(c => c.code !== 'EUR').map(({ code, rate }) => (
                            <span key={code} className="market-current-alt">{formatMoney(value * rate, code)}</span>
                        ))}
                    </p>
                )}

            <div
                ref={wrapRef}
                className="mv-chart"
                style={{ height: points.length ? HEIGHT : 'auto' }}
                tabIndex={points.length ? 0 : -1}
                role="img"
                aria-label={ariaLabel}
                onPointerMove={handlePointerMove}
                onPointerLeave={() => setHoverIndex(null)}
                onKeyDown={handleKeyDown}
                onBlur={() => setHoverIndex(null)}
            >
                {points.length === 0 && <p className="mv-empty">No market value history.</p>}
                <svg ref={svgRef} width={width} height={points.length ? HEIGHT : 0} />

                {hovered && (
                    <>
                        <div
                            className="mv-crosshair"
                            style={{ left: MARGIN.left + hx, top: MARGIN.top, height: scales.innerH }}
                        />
                        <div
                            className="mv-focus"
                            style={{ left: MARGIN.left + hx, top: MARGIN.top + hy }}
                        />
                        <div
                            className={`mv-tooltip ${hx > scales.innerW * 0.6 ? 'left' : 'right'} ${hy < 60 ? 'below' : 'above'}`}
                            style={{ left: MARGIN.left + hx, top: MARGIN.top + hy }}
                        >
                            <div className="mv-tooltip-date">{formatDate(hovered.raw)}</div>
                            <div className="mv-tooltip-value">{formatMoney(hovered.value, 'EUR')}</div>
                            {change != null && (
                                <div className="mv-tooltip-change">
                                    {change === 0 ? 'No change' : `${change > 0 ? '+' : '−'}${shortEuro(Math.abs(change))} vs previous`}
                                </div>
                            )}
                        </div>
                    </>
                )}
            </div>

            {capped && (
                <p className="mv-cap-note">
                    Showing the {MAX_POINTS} most recent of {allPoints.length} valuations
                </p>
            )}
        </div>
    );
}

export default MarketValue;
