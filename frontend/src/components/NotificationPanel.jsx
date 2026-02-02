/**
 * Notification Settings Panel.
 * Configure email, webhooks, and test notifications.
 */

import { useState, useEffect } from 'react';
import { getNotificationConfig, updateNotificationConfig, testNotification } from '../services/api';

export function NotificationPanel() {
    const [config, setConfig] = useState({
        smtp_enabled: false,
        smtp_host: '',
        smtp_port: 587,
        smtp_user: '',
        smtp_password: '',
        smtp_from: '',
        smtp_to: [],
        webhook_slack_url: '',
        webhook_discord_url: '',
        webhook_teams_url: '',
        sound_enabled: true,
    });
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [testing, setTesting] = useState(null);
    const [message, setMessage] = useState('');
    const [expanded, setExpanded] = useState(false);

    useEffect(() => {
        loadConfig();
    }, []);

    const loadConfig = async () => {
        try {
            const data = await getNotificationConfig();
            if (data.configured) {
                setConfig(prev => ({ ...prev, ...data }));
            }
        } catch (err) {
            console.error('Failed to load config:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        setSaving(true);
        setMessage('');
        try {
            await updateNotificationConfig(config);
            setMessage('✅ Configuration saved!');
        } catch (err) {
            setMessage('❌ Failed to save: ' + err.message);
        } finally {
            setSaving(false);
        }
    };

    const handleTest = async (channel) => {
        setTesting(channel);
        setMessage('');
        try {
            const result = await testNotification(channel, 'Test notification from Mini NOC');
            setMessage(result.success ? `✅ ${channel} test sent!` : `❌ ${channel} test failed`);
        } catch (err) {
            setMessage(`❌ ${channel} error: ${err.message}`);
        } finally {
            setTesting(null);
        }
    };

    if (loading) {
        return <div className="card p-4 text-gray-500">Loading notifications...</div>;
    }

    return (
        <div className="card">
            <div
                className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50"
                onClick={() => setExpanded(!expanded)}
            >
                <h3 className="font-semibold text-gray-800 flex items-center gap-2">
                    🔔 Notification Settings
                </h3>
                <span className="text-gray-400">{expanded ? '▼' : '▶'}</span>
            </div>

            {expanded && (
                <div className="p-4 pt-0 border-t border-gray-100">
                    {message && (
                        <div className="mb-4 p-2 bg-gray-100 rounded text-sm">{message}</div>
                    )}

                    {/* Email Settings */}
                    <div className="mb-6">
                        <h4 className="font-medium text-gray-700 mb-3 flex items-center gap-2">
                            📧 Email (SMTP)
                            <label className="flex items-center gap-1 text-sm">
                                <input
                                    type="checkbox"
                                    checked={config.smtp_enabled}
                                    onChange={(e) => setConfig({ ...config, smtp_enabled: e.target.checked })}
                                />
                                Enabled
                            </label>
                        </h4>
                        {config.smtp_enabled && (
                            <div className="grid grid-cols-2 gap-3">
                                <input
                                    type="text"
                                    placeholder="SMTP Host"
                                    value={config.smtp_host || ''}
                                    onChange={(e) => setConfig({ ...config, smtp_host: e.target.value })}
                                    className="input-field"
                                />
                                <input
                                    type="number"
                                    placeholder="Port"
                                    value={config.smtp_port}
                                    onChange={(e) => setConfig({ ...config, smtp_port: parseInt(e.target.value) })}
                                    className="input-field"
                                />
                                <input
                                    type="text"
                                    placeholder="Username"
                                    value={config.smtp_user || ''}
                                    onChange={(e) => setConfig({ ...config, smtp_user: e.target.value })}
                                    className="input-field"
                                />
                                <input
                                    type="password"
                                    placeholder="Password"
                                    value={config.smtp_password || ''}
                                    onChange={(e) => setConfig({ ...config, smtp_password: e.target.value })}
                                    className="input-field"
                                />
                                <input
                                    type="email"
                                    placeholder="From Email"
                                    value={config.smtp_from || ''}
                                    onChange={(e) => setConfig({ ...config, smtp_from: e.target.value })}
                                    className="input-field"
                                />
                                <div className="flex gap-2">
                                    <input
                                        type="email"
                                        placeholder="To Email(s), comma-separated"
                                        value={config.smtp_to?.join(', ') || ''}
                                        onChange={(e) => setConfig({ ...config, smtp_to: e.target.value.split(',').map(s => s.trim()) })}
                                        className="input-field flex-1"
                                    />
                                    <button
                                        onClick={() => handleTest('email')}
                                        disabled={testing === 'email'}
                                        className="btn-secondary text-sm"
                                    >
                                        {testing === 'email' ? '...' : 'Test'}
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Webhook Settings */}
                    <div className="mb-6">
                        <h4 className="font-medium text-gray-700 mb-3">🔗 Webhooks</h4>
                        <div className="space-y-3">
                            <div className="flex gap-2">
                                <span className="w-20 text-sm text-gray-600 flex items-center">Slack</span>
                                <input
                                    type="url"
                                    placeholder="https://hooks.slack.com/services/..."
                                    value={config.webhook_slack_url || ''}
                                    onChange={(e) => setConfig({ ...config, webhook_slack_url: e.target.value })}
                                    className="input-field flex-1"
                                />
                                <button
                                    onClick={() => handleTest('slack')}
                                    disabled={testing === 'slack' || !config.webhook_slack_url}
                                    className="btn-secondary text-sm"
                                >
                                    {testing === 'slack' ? '...' : 'Test'}
                                </button>
                            </div>
                            <div className="flex gap-2">
                                <span className="w-20 text-sm text-gray-600 flex items-center">Discord</span>
                                <input
                                    type="url"
                                    placeholder="https://discord.com/api/webhooks/..."
                                    value={config.webhook_discord_url || ''}
                                    onChange={(e) => setConfig({ ...config, webhook_discord_url: e.target.value })}
                                    className="input-field flex-1"
                                />
                                <button
                                    onClick={() => handleTest('discord')}
                                    disabled={testing === 'discord' || !config.webhook_discord_url}
                                    className="btn-secondary text-sm"
                                >
                                    {testing === 'discord' ? '...' : 'Test'}
                                </button>
                            </div>
                            <div className="flex gap-2">
                                <span className="w-20 text-sm text-gray-600 flex items-center">Teams</span>
                                <input
                                    type="url"
                                    placeholder="https://outlook.office.com/webhook/..."
                                    value={config.webhook_teams_url || ''}
                                    onChange={(e) => setConfig({ ...config, webhook_teams_url: e.target.value })}
                                    className="input-field flex-1"
                                />
                                <button
                                    onClick={() => handleTest('teams')}
                                    disabled={testing === 'teams' || !config.webhook_teams_url}
                                    className="btn-secondary text-sm"
                                >
                                    {testing === 'teams' ? '...' : 'Test'}
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* Sound Settings */}
                    <div className="mb-6">
                        <label className="flex items-center gap-2">
                            <input
                                type="checkbox"
                                checked={config.sound_enabled}
                                onChange={(e) => setConfig({ ...config, sound_enabled: e.target.checked })}
                            />
                            <span className="text-gray-700">🔊 Enable browser sound alerts for critical events</span>
                        </label>
                    </div>

                    {/* Save Button */}
                    <button
                        onClick={handleSave}
                        disabled={saving}
                        className="btn-primary w-full"
                    >
                        {saving ? 'Saving...' : 'Save Notification Settings'}
                    </button>
                </div>
            )}
        </div>
    );
}

export default NotificationPanel;
