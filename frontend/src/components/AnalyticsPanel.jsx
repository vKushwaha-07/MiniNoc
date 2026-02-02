import { useState, useEffect, useRef } from 'react';
import {
    LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import * as api from '../services/api';

export function AnalyticsPanel() {
    const [range, setRange] = useState(24);
    const [data, setData] = useState(null);
    const [slaData, setSlaData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);


    const loadData = async (hours) => {
        setLoading(true);
        try {
            const [metricsResult, slaResult] = await Promise.all([
                api.getAnalyticsMetrics(hours),
                api.getSLAMetrics(Math.ceil(hours / 24)) // Convert hours to days for SLA
            ]);

            // Format timestamps for display
            const formattedData = metricsResult.data.map(d => ({
                ...d,
                timeStr: new Date(d.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                dateStr: new Date(d.timestamp).toLocaleDateString()
            }));

            setData({ ...metricsResult, data: formattedData });
            setSlaData(slaResult);
            setError(null);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadData(range);
    }, [range]);

    const handleExportPDF = () => {
        // Use browser native print which supports all CSS (including oklch)
        // Checks App.css @media print for styling
        window.print();
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col md:flex-row justify-between items-center gap-4 bg-white p-4 rounded-xl shadow-sm border border-gray-200">
                <div>
                    <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
                        <span>📊</span> Network Analytics & SLA
                    </h2>
                    <p className="text-sm text-gray-500 mt-1">Historical performance and service level compliance</p>
                </div>

                <div className="flex gap-3 no-print">
                    <select
                        value={range}
                        onChange={(e) => setRange(Number(e.target.value))}
                        className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-gray-50 focus:ring-2 focus:ring-blue-500 outline-none"
                    >
                        <option value={24}>Last 24 Hours</option>
                        <option value={168}>Last 7 Days</option>
                        <option value={720}>Last 30 Days</option>
                    </select>

                    <button
                        id="export-btn"
                        onClick={handleExportPDF}
                        className="btn bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 flex items-center gap-2 shadow-sm"
                    >
                        <span>🖨️</span> Print Report
                    </button>

                    {/* CSV Download */}
                    <a
                        href={`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/analytics/export/csv?range_days=${Math.ceil(range / 24)}`}
                        download
                        className="btn bg-emerald-600 text-white hover:bg-emerald-700 shadow-md flex items-center gap-2"
                    >
                        <span>📊</span> CSV
                    </a>

                    {/* Text Report Download */}
                    <a
                        href={`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/analytics/export/pdf?range_days=${Math.ceil(range / 24)}`}
                        download
                        className="btn bg-indigo-600 text-white hover:bg-indigo-700 shadow-md flex items-center gap-2"
                    >
                        <span>📄</span> Report
                    </a>

                    <button
                        onClick={() => loadData(range)}
                        className="btn bg-blue-600 text-white hover:bg-blue-700 shadow-md flex items-center gap-2"
                    >
                        <span>↻</span>
                    </button>
                </div>
            </div>

            {loading ? (
                <div className="h-96 flex items-center justify-center bg-white rounded-xl shadow-sm border border-gray-100">
                    <div className="flex flex-col items-center">
                        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mb-4"></div>
                        <p className="text-gray-500">Aggregating monitoring data...</p>
                    </div>
                </div>
            ) : error ? (
                <div className="p-6 bg-red-50 text-red-700 rounded-xl border border-red-200 flex items-center gap-3">
                    <span className="text-2xl">⚠️</span>
                    <div>
                        <p className="font-bold">Error loading analytics</p>
                        <p className="text-sm">{error}</p>
                    </div>
                </div>
            ) : (
                <div className="space-y-6">

                    {/* SLA Section - 4 Columns */}
                    {slaData && (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                            {/* Uptime Card */}
                            <div className="bg-white p-5 rounded-xl shadow-sm border border-gray-100 relative overflow-hidden group hover:shadow-md transition-shadow">
                                <div className={`absolute top-0 left-0 w-1 h-full ${slaData.sla_compliance ? 'bg-emerald-500' : 'bg-red-500'}`}></div>
                                <div className="flex justify-between items-start mb-2">
                                    <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Uptime (SLA)</h3>
                                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${slaData.sla_compliance ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>
                                        Target: 99.9%
                                    </span>
                                </div>
                                <div className="flex items-baseline gap-2">
                                    <span className={`text-3xl font-bold tabular-nums ${slaData.sla_compliance ? 'text-gray-800' : 'text-red-600'}`}>
                                        {slaData.uptime_percent}%
                                    </span>
                                </div>
                                <p className="text-xs text-xs text-gray-400 mt-2">
                                    {slaData.sla_compliance ? '✅ SLA Compliant' : '❌ SLA Breached'}
                                </p>
                            </div>

                            {/* MTTR Card */}
                            <div className="bg-white p-5 rounded-xl shadow-sm border border-gray-100 relative overflow-hidden group hover:shadow-md transition-shadow">
                                <div className="absolute top-0 left-0 w-1 h-full bg-blue-500"></div>
                                <div className="flex justify-between items-start mb-2">
                                    <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">MTTR</h3>
                                    <span className="text-lg">🔧</span>
                                </div>
                                <div className="flex items-baseline gap-1">
                                    <span className="text-3xl font-bold text-gray-800 tabular-nums">{slaData.mttr_minutes}</span>
                                    <span className="text-sm text-gray-500">min</span>
                                </div>
                                <p className="text-xs text-gray-400 mt-2">Mean Time To Repair</p>
                            </div>

                            {/* MTBF Card */}
                            <div className="bg-white p-5 rounded-xl shadow-sm border border-gray-100 relative overflow-hidden group hover:shadow-md transition-shadow">
                                <div className="absolute top-0 left-0 w-1 h-full bg-indigo-500"></div>
                                <div className="flex justify-between items-start mb-2">
                                    <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">MTBF</h3>
                                    <span className="text-lg">🛡️</span>
                                </div>
                                <div className="flex items-baseline gap-1">
                                    <span className="text-3xl font-bold text-gray-800 tabular-nums">{slaData.mtbf_hours}</span>
                                    <span className="text-sm text-gray-500">hours</span>
                                </div>
                                <p className="text-xs text-gray-400 mt-2">Mean Time Between Failures</p>
                            </div>

                            {/* Outages Card */}
                            <div className="bg-white p-5 rounded-xl shadow-sm border border-gray-100 relative overflow-hidden group hover:shadow-md transition-shadow">
                                <div className="absolute top-0 left-0 w-1 h-full bg-orange-500"></div>
                                <div className="flex justify-between items-start mb-2">
                                    <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Total Outages</h3>
                                    <span className="text-lg">⚡</span>
                                </div>
                                <div className="flex items-baseline gap-1">
                                    <span className="text-3xl font-bold text-gray-800 tabular-nums">{slaData.total_outages}</span>
                                </div>
                                <p className="text-xs text-gray-400 mt-2">Recorded downtime events</p>
                            </div>
                        </div>
                    )}

                    {/* Performance Summary - 3 Columns */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between">
                            <div>
                                <p className="text-xs text-gray-500 uppercase font-semibold">Avg Latency</p>
                                <p className="text-2xl font-bold text-gray-800 mt-1">{data?.summary?.avg_latency_ms} <span className="text-sm font-normal text-gray-400">ms</span></p>
                            </div>
                            <div className="p-3 bg-blue-50 text-blue-600 rounded-lg">
                                📶
                            </div>
                        </div>
                        <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between">
                            <div>
                                <p className="text-xs text-gray-500 uppercase font-semibold">Avg Packet Loss</p>
                                <p className={`text-2xl font-bold mt-1 ${data?.summary?.avg_packet_loss > 0 ? 'text-red-600' : 'text-gray-800'}`}>
                                    {data?.summary?.avg_packet_loss}%
                                </p>
                            </div>
                            <div className={`p-3 rounded-lg ${data?.summary?.avg_packet_loss > 0 ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-600'}`}>
                                📉
                            </div>
                        </div>
                        <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between">
                            <div>
                                <p className="text-xs text-gray-500 uppercase font-semibold">Samples Collected</p>
                                <p className="text-2xl font-bold text-gray-800 mt-1">{data?.summary?.data_points_count}</p>
                            </div>
                            <div className="p-3 bg-gray-50 text-gray-600 rounded-lg">
                                📝
                            </div>
                        </div>
                    </div>

                    {/* Charts Grid */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* Latency Chart */}
                        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
                            <h3 className="text-sm font-bold text-gray-700 mb-6 flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                                Latency Performance (ms)
                            </h3>
                            <div className="h-64">
                                <ResponsiveContainer width="100%" height="100%">
                                    <AreaChart data={data?.data}>
                                        <defs>
                                            <linearGradient id="colorLatency" x1="0" y1="0" x2="0" y2="1">
                                                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.1} />
                                                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                                            </linearGradient>
                                        </defs>
                                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                                        <XAxis
                                            dataKey={range > 24 ? "dateStr" : "timeStr"}
                                            tick={{ fontSize: 10, fill: '#64748b' }}
                                            axisLine={false}
                                            tickLine={false}
                                            minTickGap={30}
                                        />
                                        <YAxis
                                            tick={{ fontSize: 10, fill: '#64748b' }}
                                            axisLine={false}
                                            tickLine={false}
                                        />
                                        <Tooltip
                                            contentStyle={{
                                                borderRadius: '8px',
                                                border: '1px solid #e2e8f0',
                                                boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'
                                            }}
                                            itemStyle={{ fontSize: '12px' }}
                                            labelStyle={{ fontSize: '12px', color: '#64748b', marginBottom: '4px' }}
                                        />
                                        <Area
                                            type="monotone"
                                            dataKey="avg_latency_ms"
                                            stroke="#3b82f6"
                                            strokeWidth={2}
                                            fillOpacity={1}
                                            fill="url(#colorLatency)"
                                            name="Latency"
                                        />
                                    </AreaChart>
                                </ResponsiveContainer>
                            </div>
                        </div>

                        {/* Packet Loss Chart */}
                        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
                            <h3 className="text-sm font-bold text-gray-700 mb-6 flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-red-500"></span>
                                Packet Loss Events (%)
                            </h3>
                            <div className="h-64">
                                <ResponsiveContainer width="100%" height="100%">
                                    <LineChart data={data?.data}>
                                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                                        <XAxis
                                            dataKey={range > 24 ? "dateStr" : "timeStr"}
                                            tick={{ fontSize: 10, fill: '#64748b' }}
                                            axisLine={false}
                                            tickLine={false}
                                            minTickGap={30}
                                        />
                                        <YAxis
                                            tick={{ fontSize: 10, fill: '#64748b' }}
                                            axisLine={false}
                                            tickLine={false}
                                        />
                                        <Tooltip
                                            contentStyle={{
                                                borderRadius: '8px',
                                                border: '1px solid #e2e8f0',
                                                boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'
                                            }}
                                            itemStyle={{ fontSize: '12px' }}
                                            labelStyle={{ fontSize: '12px', color: '#64748b', marginBottom: '4px' }}
                                        />
                                        <Line
                                            type="step"
                                            dataKey="avg_packet_loss"
                                            stroke="#ef4444"
                                            strokeWidth={2}
                                            dot={false}
                                            activeDot={{ r: 4 }}
                                            name="Loss %"
                                        />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default AnalyticsPanel;
