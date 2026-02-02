/**
 * Alert Panel Component.
 * Displays active alerts with severity indicators.
 */

import { SeverityBadge } from './StatusBadge';
import * as api from '../services/api';

export function AlertPanel({ alerts, onRefresh }) {
    const handleResolve = async (alertId) => {
        try {
            await api.resolveAlert(alertId);
            onRefresh?.();
        } catch (error) {
            console.error('Failed to resolve alert:', error);
        }
    };

    const handleResolveAll = async () => {
        try {
            await api.resolveAllAlerts();
            onRefresh?.();
        } catch (error) {
            console.error('Failed to resolve alerts:', error);
        }
    };

    if (!alerts || alerts.length === 0) {
        return (
            <div className="card p-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2 font-outfit">
                    <span>🔔</span> Active Alerts
                </h3>
                <div className="text-center py-8">
                    <div className="text-4xl mb-2 text-emerald-500">✓</div>
                    <p className="text-gray-600 font-medium">No active alerts</p>
                    <p className="text-sm text-gray-400">All systems operating normally</p>
                </div>
            </div>
        );
    }

    return (
        <div className="card">
            <div className="p-4 border-b border-gray-100 flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-800 flex items-center gap-2 font-outfit">
                    <span>🔔</span> Active Alerts ({alerts.length})
                </h3>
                <button
                    onClick={handleResolveAll}
                    className="text-sm text-[#22819A] hover:text-[#1b667a] font-medium"
                >
                    Resolve All
                </button>
            </div>
            <div className="divide-y divide-gray-50 max-h-96 overflow-y-auto">
                {alerts.map((alert) => (
                    <div
                        key={alert.id}
                        className="p-4 hover:bg-gray-50 transition-colors animate-fadeIn"
                    >
                        <div className="flex items-start justify-between">
                            <div className="flex-1">
                                <div className="flex items-center gap-2 mb-1">
                                    <SeverityBadge severity={alert.severity} />
                                    <span className="text-sm text-gray-500 font-mono">
                                        {alert.device_ip}
                                    </span>
                                </div>
                                <p className="font-medium text-gray-800">{alert.title}</p>
                                {alert.message && (
                                    <p className="text-sm text-gray-500 mt-1">{alert.message}</p>
                                )}
                                <p className="text-xs text-gray-400 mt-2">
                                    {formatAlertTime(alert.created_at)}
                                </p>
                            </div>
                            <button
                                onClick={() => handleResolve(alert.id)}
                                className="ml-4 w-8 h-8 rounded-full bg-emerald-50 text-emerald-600 hover:bg-emerald-100 flex items-center justify-center transition-colors"
                                title="Resolve"
                            >
                                ✓
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

function formatAlertTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
}

export default AlertPanel;
