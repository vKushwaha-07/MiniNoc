import { useState } from 'react';
import * as api from '../services/api';

export function InternetHealthWidget() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const runCheck = async () => {
        setLoading(true);
        setError(null);
        try {
            const result = await api.runSpeedtest();
            setData(result);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="card p-6 h-full">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">Internet Health Monitor</h2>

            {!data && !loading && !error && (
                <div className="text-center py-8">
                    <p className="text-gray-500 mb-4">Check connectivity & speed</p>
                    <button onClick={runCheck} className="btn btn-primary">
                        Run Diagnostics
                    </button>
                </div>
            )}

            {loading && (
                <div className="text-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
                    <p className="text-gray-600">Running speedtest & bandwidth checks...</p>
                    <p className="text-xs text-gray-400 mt-2">This may take up to 30 seconds</p>
                </div>
            )}

            {error && (
                <div className="text-center py-8">
                    <p className="text-red-600 mb-4">Test Failed: {error}</p>
                    <button onClick={runCheck} className="btn btn-sm btn-outline">Retry</button>
                </div>
            )}

            {data && !loading && (
                <div className="space-y-6">
                    {/* Status Badge */}
                    <div className={`p-4 rounded-lg flex items-center justify-between ${data.status === 'UP' ? 'bg-emerald-50 text-emerald-800' : 'bg-red-50 text-red-800'
                        }`}>
                        <div className="flex items-center gap-2">
                            <span className="font-bold text-lg">Internet is {data.status}</span>
                        </div>
                        <button onClick={runCheck} className="btn btn-xs btn-white">
                            ↻
                        </button>
                    </div>

                    {/* Latency Grid */}
                    <div className="grid grid-cols-2 gap-4">
                        <div className="p-3 bg-gray-50 rounded-lg">
                            <p className="text-xs text-gray-500 mb-1">Google DNS</p>
                            <p className="font-mono font-bold text-gray-800">{data.latency_google} ms</p>
                        </div>
                        <div className="p-3 bg-gray-50 rounded-lg">
                            <p className="text-xs text-gray-500 mb-1">Cloudflare</p>
                            <p className="font-mono font-bold text-gray-800">{data.latency_cloudflare} ms</p>
                        </div>
                    </div>

                    {/* Bandwidth */}
                    <div className="space-y-3">
                        <div>
                            <div className="flex justify-between text-sm mb-1">
                                <span className="text-gray-500">Download</span>
                                <span className="font-bold text-blue-600">{data.download_mbps?.toFixed(1)} Mbps</span>
                            </div>
                            <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                                <div className="h-full bg-blue-500 rounded-full" style={{ width: '100%' }}></div>
                            </div>
                        </div>
                        <div>
                            <div className="flex justify-between text-sm mb-1">
                                <span className="text-gray-500">Upload</span>
                                <span className="font-bold text-indigo-600">{data.upload_mbps?.toFixed(1)} Mbps</span>
                            </div>
                            <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                                <div className="h-full bg-indigo-500 rounded-full" style={{ width: '100%' }}></div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
