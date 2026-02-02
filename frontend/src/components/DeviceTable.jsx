/**
 * Device Table Component.
 * Enhanced with MAC address, vendor, and OS detection columns.
 */

import { useState } from 'react';
import { StatusBadge } from './StatusBadge';
import { enrichDevice } from '../services/api';
import * as api from '../services/api';

export function DeviceTable({ devices, onDeviceClick, onRefresh }) {
    const [enrichingId, setEnrichingId] = useState(null);

    const handleEnrich = async (e, device) => {
        e.stopPropagation();
        setEnrichingId(device.id);
        try {
            await enrichDevice(device.id, true);
            onRefresh?.();
        } catch (err) {
            console.error('Enrich failed:', err);
        } finally {
            setEnrichingId(null);
        }
    };

    const handleWake = async (e, device) => {
        e.stopPropagation();
        if (!device.mac_address) {
            alert('No MAC address available. Click the 🔍 button to discover device details first.');
            return;
        }
        if (!confirm(`Send Wake-on-LAN packet to ${device.ip_address}?`)) return;
        try {
            await api.wakeDevice(device.mac_address);
            alert('Magic packet sent! ⚡');
        } catch (err) {
            alert('Failed to send WOL: ' + err.message);
        }
    };

    const handleSshTest = async (e, ip) => {
        e.stopPropagation();
        const user = prompt('Enter SSH Username:', 'root');
        if (!user) return;

        try {
            const password = prompt('Enter SSH Password (sent securely):');
            if (!password) return;

            alert('Testing connection... ⏳');
            const res = await api.testSsh(ip, user, password);
            alert(res.message);
        } catch (err) {
            alert('SSH Test Failed: ' + err.message);
        }
    };

    if (!devices || devices.length === 0) {
        return (
            <div className="card p-8 text-center">
                <p className="text-gray-500">No devices found.</p>
                <p className="text-sm text-gray-400 mt-2">
                    Add devices or run a subnet discovery scan.
                </p>
            </div>
        );
    }

    return (
        <div className="card overflow-hidden">
            <div className="overflow-x-auto">
                <table className="data-table">
                    <thead>
                        <tr>
                            <th>IP Address</th>
                            <th>Hostname</th>
                            <th>Status</th>
                            <th>Vendor</th>
                            <th>OS</th>
                            <th>Latency</th>
                            <th>Packet Loss</th>
                            <th>Last Seen</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {devices.map((device) => (
                            <tr
                                key={device.id}
                                onClick={() => onDeviceClick?.(device)}
                                className="cursor-pointer"
                            >
                                <td className="font-mono font-medium">{device.ip_address}</td>
                                <td className="text-gray-600">
                                    {device.hostname || <span className="text-gray-400">—</span>}
                                </td>
                                <td>
                                    <StatusBadge status={device.status} />
                                </td>
                                <td>
                                    {device.vendor ? (
                                        <span className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded text-xs font-medium">
                                            {device.vendor}
                                        </span>
                                    ) : (
                                        <span className="text-gray-400">—</span>
                                    )}
                                </td>
                                <td>
                                    {device.os_type ? (
                                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${getOsClass(device.os_type)}`}>
                                            {device.os_type}
                                        </span>
                                    ) : (
                                        <span className="text-gray-400">—</span>
                                    )}
                                </td>
                                <td>
                                    {device.latest_latency_ms != null ? (
                                        <span className={getLatencyClass(device.latest_latency_ms)}>
                                            {device.latest_latency_ms.toFixed(1)} ms
                                        </span>
                                    ) : (
                                        <span className="text-gray-400">—</span>
                                    )}
                                </td>
                                <td>
                                    {device.latest_packet_loss != null ? (
                                        <span className={getPacketLossClass(device.latest_packet_loss)}>
                                            {device.latest_packet_loss.toFixed(1)}%
                                        </span>
                                    ) : (
                                        <span className="text-gray-400">—</span>
                                    )}
                                </td>
                                <td className="text-gray-500 text-sm">
                                    {device.last_seen ? formatTimeAgo(device.last_seen) : '—'}
                                </td>
                                <td onClick={(e) => e.stopPropagation()} className="flex items-center gap-2">
                                    <button
                                        onClick={(e) => handleWake(e, device)}
                                        className={`p-1.5 rounded ${device.mac_address ? 'text-orange-600 hover:bg-orange-50' : 'text-gray-300 cursor-not-allowed'}`}
                                        title={device.mac_address ? 'Wake on LAN' : 'No MAC address - run discovery first'}
                                    >
                                        ⚡
                                    </button>
                                    <button
                                        onClick={(e) => handleSshTest(e, device.ip_address)}
                                        className="p-1.5 text-gray-600 hover:bg-gray-100 rounded"
                                        title="Test SSH Connection"
                                    >
                                        💻
                                    </button>
                                    <button
                                        onClick={(e) => handleEnrich(e, device)}
                                        disabled={enrichingId === device.id}
                                        className="p-1.5 text-indigo-600 hover:bg-indigo-50 rounded disabled:opacity-50"
                                        title="Deep Scan / Enrich"
                                    >
                                        {enrichingId === device.id ? '...' : '🔍'}
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

function getLatencyClass(latency) {
    if (latency >= 500) return 'text-red-600 font-medium';
    if (latency >= 100) return 'text-amber-600 font-medium';
    return 'text-emerald-600';
}

function getPacketLossClass(loss) {
    if (loss >= 50) return 'text-red-600 font-medium';
    if (loss >= 10) return 'text-amber-600 font-medium';
    return 'text-emerald-600';
}

function getOsClass(osType) {
    const os = osType?.toLowerCase() || '';
    if (os.includes('android')) return 'bg-green-100 text-green-700';
    if (os.includes('ios') || os.includes('macos')) return 'bg-gray-200 text-gray-800';
    if (os.includes('windows')) return 'bg-blue-100 text-blue-700';
    if (os.includes('linux') || os.includes('unix')) return 'bg-orange-100 text-orange-700';
    if (os.includes('network')) return 'bg-teal-100 text-teal-700';
    return 'bg-gray-100 text-gray-700';
}

function formatTimeAgo(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);

    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
}

export default DeviceTable;
