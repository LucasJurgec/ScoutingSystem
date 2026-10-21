import { useState } from 'react';
import './Position.css';

// ids match the position_advanced enum in the database
const POSITIONS = [
    { id: 'GK', label: 'Goalkeeper', x: 150, y: 330 },

    { id: 'CB', label: 'Centre Back', x: 150, y: 280 },
    { id: 'LB', label: 'Left Back', x: 50, y: 280 },
    { id: 'RB', label: 'Right Back', x: 250, y: 280 },

    { id: 'DM', label: 'Defensive Midfielder', x: 150, y: 220 },
    { id: 'CM', label: 'Centre Midfielder', x: 150, y: 175 },
    { id: 'AM', label: 'Attacking Midfielder', x: 150, y: 130 },

    { id: 'LM', label: 'Left Midfielder', x: 50, y: 175 },
    { id: 'RM', label: 'Right Midfielder', x: 250, y: 175 },

    { id: 'LW', label: 'Left Wing', x: 50, y: 70 },
    { id: 'RW', label: 'Right Wing', x: 250, y: 70 },
    { id: 'ST', label: 'Striker', x: 150, y: 70 },
];

const COLOURS = {
    primary: '#3366ff',
    secondary: '#99c2ff',
    other: '#cc3300',
};

// primary = player.position_advanced, secondary = the player_position list
function Position({ primary, secondary = [] }) {
    const [hoveredPos, setHoveredPos] = useState(null);

    const roleOf = (id) => {
        if (id === primary) return 'primary';
        if (secondary.includes(id)) return 'secondary';
        return 'other';
    };

    return (
        <div className="position">
            <svg className="pitch" viewBox="0 0 300 350" xmlns="http://www.w3.org/2000/svg">
                {/* pitch size and colour */}
                <rect x="0" y="0" width="300" height="350" fill="#004d00"/>

                {/* white outline */}
                <line x1="0" y1="0" x2="300" y2="0" stroke="white" strokeWidth="5"/>
                <line x1="0" y1="0" x2="0" y2="350" stroke="white" strokeWidth="5"/>
                <line x1="300" y1="350" x2="300" y2="0" stroke="white" strokeWidth="5"/>
                <line x1="300" y1="350" x2="0" y2="350" stroke="white" strokeWidth="5"/>

                {/* half way line and circle */}
                <line x1="0" y1="175" x2="300" y2="175" stroke="white" strokeWidth="3"/>
                <circle cx="150" cy="175" r="40" fill="none" stroke="white" strokeWidth="3"/>

                {/* attacking box */}
                <line x1="110" y1="0" x2="110" y2="20" stroke="white" strokeWidth="3"/>
                <line x1="190" y1="0" x2="190" y2="20" stroke="white" strokeWidth="3"/>
                <line x1="108.5" y1="20" x2="191.5" y2="20" stroke="white" strokeWidth="3"/>

                <line x1="85" y1="0" x2="85" y2="45" stroke="white" strokeWidth="3"/>
                <line x1="215" y1="0" x2="215" y2="45" stroke="white" strokeWidth="3"/>
                <line x1="83.5" y1="45" x2="216.5" y2="45" stroke="white" strokeWidth="3"/>

                <path d="M 120 45 A 40 40 0 0 0 180 45" fill="none" stroke="white" strokeWidth="3"/>

                {/* defensive box */}
                <line x1="110" y1="350" x2="110" y2="330" stroke="white" strokeWidth="3"/>
                <line x1="190" y1="350" x2="190" y2="330" stroke="white" strokeWidth="3"/>
                <line x1="108.5" y1="330" x2="191.5" y2="330" stroke="white" strokeWidth="3"/>

                <line x1="85" y1="350" x2="85" y2="305" stroke="white" strokeWidth="3"/>
                <line x1="215" y1="350" x2="215" y2="305" stroke="white" strokeWidth="3"/>
                <line x1="83.5" y1="305" x2="216.5" y2="305" stroke="white" strokeWidth="3"/>

                <path d="M 120 305 A 40 40 0 0 1 180 305" fill="none" stroke="white" strokeWidth="3"/>

                {/* player position circles */}
                {POSITIONS.map((pos) => {
                    const role = roleOf(pos.id);
                    const label = role === 'other'
                        ? pos.label
                        : `${pos.label} (${role === 'primary' ? 'Primary' : 'Secondary'})`;

                    // keep the tooltip inside the pitch for the wide positions
                    const boxWidth = label.length * 6;
                    const boxX = Math.min(Math.max(pos.x - boxWidth / 2, 2), 298 - boxWidth);

                    return (
                        <g key={pos.id}>
                            <circle
                                cx={pos.x}
                                cy={pos.y}
                                r={14}
                                fill={COLOURS[role]}
                                stroke="black"
                                strokeWidth={3}
                                onMouseEnter={() => setHoveredPos(pos.id)}
                                onMouseLeave={() => setHoveredPos(null)}
                            />
                            {hoveredPos === pos.id && (
                                <g pointerEvents="none">
                                    <rect x={boxX} y={pos.y - 30} width={boxWidth} height="20" fill="black" rx="4"/>
                                    <text x={boxX + boxWidth / 2} y={pos.y - 16} fill="white" fontSize="10" textAnchor="middle">
                                        {label}
                                    </text>
                                </g>
                            )}
                        </g>
                    );
                })}
            </svg>

            <div className="position-legend">
                <span className="legend-item">
                    <span className="legend-dot" style={{ background: COLOURS.primary }} /> Primary position
                </span>
                <span className="legend-item">
                    <span className="legend-dot" style={{ background: COLOURS.secondary }} /> Secondary positions
                </span>
            </div>
        </div>
    );
}

export default Position;
