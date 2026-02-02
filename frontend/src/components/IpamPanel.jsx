import { useState, useEffect } from 'react';
import * as api from '../services/api';

export function IpamPanel() {
    const [subnet, setSubnet] = useState("192.168.1");
    const [ips, setIps] = useState([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        loadIpam();
    }, [subnet]);

    const loadIpam = async () => {
        setLoading(true);
        try {
            const data = await api.getIpam(subnet);
            setIps(data);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const getStatusColor = (status) => {
        switch (status) {
            case 'active': return 'bg-emerald-500 hover:bg-emerald-600';
            case 'down': return 'bg-red-500 hover:bg-red-600';
            case 'reserved': return 'bg-blue-500 hover:bg-blue-600';
            default: return 'bg-gray-200 hover:bg-gray-300';
        }
    };

    return (
        <div className="card p-6">
            <div className="flex justify-between items-center mb-6">
                <h2 className="text-lg font-semibold text-gray-800">IPAM Visualizer</h2>
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={subnet}
                        onChange={(e) => setSubnet(e.target.value)}
                        className="input max-w-[150px] text-sm"
                        placeholder="192.168.1"
                    />
                    <button onClick={loadIpam} className="btn btn-sm btn-outline">
                        ↻
                    </button>
                </div>
            </div>

            {loading ? (
                <div className="h-64 flex items-center justify-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
            ) : (
                <div className="grid grid-cols-16 gap-1">
                    {ips.map((ip) => (
                        <div
                            key={ip.ip}
                            className={`aspect-square rounded-sm ${getStatusColor(ip.status)} transition-colors cursor-help tooltip-container relative group`}
                        >
                            {/* Tooltip */}
                            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-10 w-48 bg-gray-900 text-white text-xs rounded p-2 shadow-lg">
                                <p className="font-bold">{ip.ip}</p>
                                <p>Status: {ip.status}</p>
                                {ip.hostname && <p>Host: {ip.hostname}</p>}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            <div className="flex gap-4 mt-6 text-xs text-gray-500">
                <div className="flex items-center gap-1"><div className="w-3 h-3 bg-emerald-500 rounded-sm"></div> Active</div>
                <div className="flex items-center gap-1"><div className="w-3 h-3 bg-red-500 rounded-sm"></div> Down</div>
                <div className="flex items-center gap-1"><div className="w-3 h-3 bg-blue-500 rounded-sm"></div> Reserved</div>
                <div className="flex items-center gap-1"><div className="w-3 h-3 bg-gray-200 rounded-sm"></div> Free</div>
            </div>
        </div>
    );
}
