/**
 * Scan Control Panel Component.
 * Controls for subnet discovery, health checks, stop scanning, and clear devices.
 */

import { useState, useRef, useEffect } from 'react';
import * as api from '../services/api';

export function ScanPanel({ onScanComplete }) {
    const [subnet, setSubnet] = useState('');
    const [isScanning, setIsScanning] = useState(false);
    const [scanResult, setScanResult] = useState(null);
    const [error, setError] = useState(null);
    const [isClearing, setIsClearing] = useState(false);
    const abortControllerRef = useRef(null);

    // Load local subnet on mount
    useEffect(() => {
        const loadLocalNet = async () => {
            try {
                const info = await api.getLocalNetwork();
                if (info && info.subnet) {
                    setSubnet(info.subnet);
                }
            } catch (err) {
                // Fallback to default if API fails
                setSubnet('192.168.1.0/24');
            }
        };
        loadLocalNet();
    }, []);

    const handleDiscover = async () => {
        setIsScanning(true);
        setError(null);
        setScanResult(null);
        abortControllerRef.current = new AbortController();

        try {
            const result = await api.discoverSubnet(subnet);
            setScanResult(result);
            onScanComplete?.();
        } catch (err) {
            if (err.name !== 'AbortError') {
                setError(err.message);
            }
        } finally {
            setIsScanning(false);
            abortControllerRef.current = null;
        }
    };

    const handleHealthCheck = async () => {
        setIsScanning(true);
        setError(null);
        setScanResult(null);

        try {
            const result = await api.triggerHealthCheck();
            setScanResult(result);
            onScanComplete?.();
        } catch (err) {
            setError(err.message);
        } finally {
            setIsScanning(false);
        }
    };

    const handleStopScan = () => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }
        setIsScanning(false);
        setScanResult(null);
        setError('Scan stopped by user');
    };

    const handleClearDevices = async () => {
        if (!window.confirm('Are you sure you want to delete ALL devices? This cannot be undone.')) {
            return;
        }

        setIsClearing(true);
        setError(null);
        setScanResult(null);

        try {
            await api.deleteAllDevices();
            setScanResult({ message: 'All devices cleared successfully' });
            onScanComplete?.();
        } catch (err) {
            setError(err.message);
        } finally {
            setIsClearing(false);
        }
    };

    return (
        <div className="card p-5">
            <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2 font-outfit">
                <span>🔍</span> Scan Controls
            </h3>

            {/* Subnet Discovery */}
            <div className="mb-4">
                <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
                    Subnet Discovery
                </label>
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={subnet}
                        onChange={(e) => setSubnet(e.target.value)}
                        placeholder="192.168.1.0/24"
                        disabled={isScanning}
                        className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm font-mono focus:ring-2 focus:ring-[#22819A] focus:border-[#22819A] outline-none disabled:bg-gray-100"
                    />
                    {isScanning ? (
                        <button
                            onClick={handleStopScan}
                            className="btn bg-red-500 text-white hover:bg-red-600"
                        >
                            ⏹ Stop
                        </button>
                    ) : (
                        <button
                            onClick={handleDiscover}
                            className="btn btn-primary"
                        >
                            Discover
                        </button>
                    )}
                </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-2 pt-4 border-t border-gray-100">
                <button
                    onClick={handleHealthCheck}
                    disabled={isScanning || isClearing}
                    className="flex-1 btn bg-gray-100 text-gray-700 hover:bg-gray-200 disabled:opacity-50"
                >
                    {isScanning ? 'Running...' : '🔄 Health Check'}
                </button>
                <button
                    onClick={handleClearDevices}
                    disabled={isScanning || isClearing}
                    className="btn bg-red-50 text-red-600 hover:bg-red-100 disabled:opacity-50"
                >
                    {isClearing ? 'Clearing...' : '🗑️ Clear All'}
                </button>
            </div>

            {/* Results */}
            {error && (
                <div className="mt-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
                    {error}
                </div>
            )}

            {scanResult && (
                <div className="mt-4 p-3 bg-emerald-50 text-emerald-700 rounded-lg text-sm">
                    {scanResult.message ? (
                        <p className="font-medium">{scanResult.message}</p>
                    ) : (
                        <>
                            <p className="font-medium">Scan Complete</p>
                            {scanResult.reachable_hosts !== undefined && (
                                <p>Found {scanResult.reachable_hosts} reachable hosts</p>
                            )}
                            {scanResult.new_devices_added !== undefined && (
                                <p>Added {scanResult.new_devices_added} new devices</p>
                            )}
                            {scanResult.devices_up !== undefined && (
                                <p>{scanResult.devices_up} UP / {scanResult.devices_down} DOWN</p>
                            )}
                            {scanResult.duration_seconds && (
                                <p className="text-xs mt-1 opacity-75">
                                    Duration: {scanResult.duration_seconds?.toFixed(2)}s
                                </p>
                            )}
                        </>
                    )}
                </div>
            )}
        </div>
    );
}

export default ScanPanel;
