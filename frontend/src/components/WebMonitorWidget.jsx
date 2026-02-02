import { useState, useEffect } from 'react';
import * as api from '../services/api';

export function WebMonitorWidget() {
    const [targets, setTargets] = useState([]);
    const [results, setResults] = useState({});
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        loadTargets();
    }, []);

    const loadTargets = async () => {
        try {
            const list = await api.getWebTargets();
            setTargets(list);
            checkAll(list);
        } catch (err) {
            console.error(err);
        }
    };

    const checkAll = async (targetList) => {
        setLoading(true);
        // Simulate checking one by one or batch
        try {
            const res = await api.checkAllWebsites();
            const resMap = {};
            res.forEach(r => resMap[r.url] = r);
            setResults(resMap);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="card p-6 h-full flex flex-col">
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
                    <span>🌐</span> Web Monitor
                </h2>
                <button
                    onClick={() => checkAll(targets)}
                    className="btn btn-xs btn-outline"
                    disabled={loading}
                >
                    {loading ? 'Checking...' : 'Check Now'}
                </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-3">
                {targets.map((t) => {
                    const result = results[t.url];
                    return (
                        <div key={t.url} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-100">
                            <div className="flex items-center gap-3">
                                <div className={`w-3 h-3 rounded-full ${result
                                        ? (result.is_up ? 'bg-emerald-500' : 'bg-red-500')
                                        : 'bg-gray-300'
                                    }`}></div>
                                <div>
                                    <p className="font-medium text-sm text-gray-900">{t.name}</p>
                                    <a href={t.url} target="_blank" rel="noreferrer" className="text-xs text-blue-500 hover:underline truncate max-w-[150px] block">
                                        {t.url}
                                    </a>
                                </div>
                            </div>

                            <div className="text-right">
                                {result ? (
                                    <>
                                        <p className="text-xs font-mono font-bold">{result.latency_ms} ms</p>
                                        <p className={`text-[10px] ${result.status_code >= 400 ? 'text-red-500' : 'text-gray-500'}`}>
                                            HTTP {result.status_code}
                                        </p>
                                    </>
                                ) : (
                                    <span className="text-xs text-gray-400">Waiting...</span>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>

            <div className="mt-4 pt-3 border-t border-gray-100 text-xs text-gray-500 flex gap-4">
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500"></span> UP</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500"></span> DOWN</span>
            </div>
        </div>
    );
}
