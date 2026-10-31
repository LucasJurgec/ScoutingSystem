import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API_BASE } from '../api';
import './LoginPage.css';

function LoginPage() {
    const navigate = useNavigate();
    const location = useLocation();
    // where to go after logging in (set by the admin page when it redirects here)
    const redirectTo = location.state?.from ?? '/admin';

    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState(null);
    const [submitting, setSubmitting] = useState(false);

    // already logged in? skip the form
    useEffect(() => {
        axios.get(`${API_BASE}/auth/me`, { withCredentials: true })
            .then(() => navigate(redirectTo, { replace: true }))
            .catch(() => { /* not logged in, show the form */ });
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!username.trim() || !password) {
            setError('Enter a username and password.');
            return;
        }
        setSubmitting(true);
        setError(null);

        axios.post(
            `${API_BASE}/auth/login`,
            { username: username.trim(), password },
            { withCredentials: true } // needed so the session cookie is saved
        )
            .then(() => navigate(redirectTo, { replace: true }))
            .catch(err => {
                if (err.response?.status === 401) {
                    setError('Invalid username or password.');
                } else {
                    console.error(err);
                    setError(`Could not reach the server. Check the API is running at ${API_BASE}.`);
                }
                setPassword('');
            })
            .finally(() => setSubmitting(false));
    };

    return (
        <div className="login-page">
            <Link to="/" className="nav-btn login-back">← Back</Link>

            <form className="login-card" onSubmit={handleSubmit} noValidate>
                <h1 className="login-title">Admin Login</h1>

                <label className="login-label" htmlFor="username">Username</label>
                <input
                    id="username"
                    className="login-input"
                    type="text"
                    autoComplete="username"
                    autoFocus
                    value={username}
                    onChange={e => setUsername(e.target.value)}
                />

                <label className="login-label" htmlFor="password">Password</label>
                <input
                    id="password"
                    className="login-input"
                    type="password"
                    autoComplete="current-password"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                />

                {error && <p className="login-error" role="alert">{error}</p>}

                <button className="login-btn" type="submit" disabled={submitting}>
                    {submitting ? 'Logging in...' : 'Log in'}
                </button>
            </form>
        </div>
    );
}

export default LoginPage;
