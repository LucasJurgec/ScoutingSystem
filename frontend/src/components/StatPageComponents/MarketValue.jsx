import './StatPageComponents/MarketValue.css';

// Rough fixed rates, fine for the prototype
const CURRENCIES = [
    { code: 'EUR', rate: 1 },
    { code: 'GBP', rate: 0.863 },
    { code: 'AUD', rate: 1.66 },
];

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

function MarketValue({ value }) {
    return (
        <div className="market-container">
            <p className="market-title"><b>Current Market Value</b></p>
            {value == null
                ? <p>Unknown</p>
                : CURRENCIES.map(({ code, rate }) => (
                    <p key={code}>{formatMoney(value * rate, code)}</p>
                ))}
        </div>
    );
}

export default MarketValue;
