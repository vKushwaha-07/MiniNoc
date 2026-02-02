/**
 * Top Navigation Bar Component.
 * Displays branding, last scan time, auto-refresh toggle, and theme toggle.
 */

import { useState, useEffect } from 'react';

export function TopBar({ lastScan, onRefresh, autoRefresh, onAutoRefreshChange, theme, onToggleTheme }) {
    const [currentTime, setCurrentTime] = useState(new Date());

    useEffect(() => {
        const interval = setInterval(() => setCurrentTime(new Date()), 1000);
        return () => clearInterval(interval);
    }, []);

    const isDark = theme === 'dark';

    return (
        <header style={{
            backgroundColor: 'var(--bg-secondary)',
            borderBottom: '1px solid var(--border-light)'
        }} className="shadow-sm">
            <div className="px-6 py-4 flex items-center justify-between">
                {/* Branding */}
                <div className="flex items-center gap-3">
                    <div
                        className="w-10 h-10 rounded-xl flex items-center justify-center shadow-md"
                        style={{ backgroundColor: 'var(--accent-primary)' }}
                    >
                        <span className="text-white font-bold text-lg font-outfit">N</span>
                    </div>
                    <div>
                        <h1 className="text-xl font-bold font-outfit tracking-tight" style={{ color: 'var(--text-primary)' }}>
                            Mini NOC
                        </h1>
                        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Network Operations Center</p>
                    </div>
                </div>

                {/* Status & Controls */}
                <div className="flex items-center gap-4">
                    {/* Last Scan */}
                    <div className="text-right hidden md:block">
                        <p className="text-xs uppercase tracking-wide font-semibold" style={{ color: 'var(--text-muted)' }}>
                            Last Scan
                        </p>
                        <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                            {lastScan ? formatTimestamp(lastScan) : 'Never'}
                        </p>
                    </div>

                    {/* Auto Refresh Toggle */}
                    <label
                        className="flex items-center gap-2 cursor-pointer px-3 py-1.5 rounded-lg border"
                        style={{
                            backgroundColor: 'var(--bg-tertiary)',
                            borderColor: 'var(--border-light)'
                        }}
                    >
                        <span className="text-xs font-semibold" style={{ color: 'var(--text-secondary)' }}>
                            Auto-refresh
                        </span>
                        <div className="relative">
                            <input
                                type="checkbox"
                                checked={autoRefresh}
                                onChange={(e) => onAutoRefreshChange?.(e.target.checked)}
                                className="sr-only peer"
                            />
                            <div
                                className="w-9 h-5 rounded-full transition-colors"
                                style={{ backgroundColor: autoRefresh ? 'var(--accent-primary)' : 'var(--border-light)' }}
                            ></div>
                            <div
                                className="absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-all"
                                style={{ left: autoRefresh ? '18px' : '2px' }}
                            ></div>
                        </div>
                    </label>

                    {/* Theme Toggle */}
                    <button
                        onClick={onToggleTheme}
                        className="w-10 h-10 rounded-lg flex items-center justify-center transition-all"
                        style={{
                            backgroundColor: 'var(--bg-tertiary)',
                            color: 'var(--text-primary)'
                        }}
                        title={isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
                    >
                        {isDark ? (
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                            </svg>
                        ) : (
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                            </svg>
                        )}
                    </button>

                    {/* Refresh Button */}
                    <button onClick={onRefresh} className="btn btn-primary">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                        </svg>
                        Refresh
                    </button>

                    {/* Current Time */}
                    <div
                        className="text-sm font-mono tabular-nums px-3 py-1.5 rounded-lg"
                        style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-secondary)' }}
                    >
                        {currentTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                </div>
            </div>
        </header>
    );
}

function formatTimestamp(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);

    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export default TopBar;
