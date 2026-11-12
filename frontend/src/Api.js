import { useEffect, useState } from 'react';
import axios from 'axios';
 
// Set VITE_API_URL in frontend/.env when it's deployed
export const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
 
// Small fetch hook: const { data, loading, error } = useApi('/players/3333/contract')
export function useApi(path) {
    const [state, setState] = useState({ data: null, loading: true, error: null });
 
    useEffect(() => {
        let cancelled = false;
        setState({ data: null, loading: true, error: null });
        axios.get(`${API_BASE}${path}`)
            .then(res => { if (!cancelled) setState({ data: res.data, loading: false, error: null }); })
            .catch(err => {
                console.error(err);
                if (!cancelled) setState({ data: null, loading: false, error: err });
            });
        return () => { cancelled = true; };
    }, [path]);
 
    return state;
} 