import { useEffect, useState } from 'react';
import axios from 'axios';
import { API_BASE } from '../../api';

function ShortlistButton({ playerId }) {
    const [shortlisted, setShortlisted] = useState(false);
    const [ready, setReady] = useState(false);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        let cancelled = false;
        setReady(false);
        setError(null);
        axios.get(`${API_BASE}/shortlist/${playerId}`)
            .then(res => { if (!cancelled) setShortlisted(res.data.shortlisted); })
            .catch(err => {
                if (cancelled) return;
                console.error(err);
                setError('Could not check the shortlist.');
            })
            .finally(() => { if (!cancelled) setReady(true); });
        return () => { cancelled = true; };
    }, [playerId]);

    const toggle = () => {
        const next = !shortlisted;
        setShortlisted(next); // update straight away, roll back if the request fails
        setSaving(true);
        setError(null);
        const request = next
            ? axios.post(`${API_BASE}/shortlist/${playerId}`)
            : axios.delete(`${API_BASE}/shortlist/${playerId}`);
        request
            .catch(err => {
                console.error(err);
                setShortlisted(!next);
                setError('Could not update the shortlist.');
            })
            .finally(() => setSaving(false));
    };

    return (
        <>
            <button
                className={`detail-btn shortlist-btn${shortlisted ? ' is-shortlisted' : ''}`}
                onClick={toggle}
                disabled={!ready || saving}
                aria-pressed={shortlisted}
            >
                {shortlisted ? 'Shortlisted' : 'Add to shortlist'}
            </button>
            {error && <p className="shortlist-error">{error}</p>}
        </>
    );
}

export default ShortlistButton;
