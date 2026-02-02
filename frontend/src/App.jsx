/**
 * Mini NOC Dashboard - Main Application Component.
 * Professional Network Operations Center monitoring interface.
 */

import { useState, useEffect, useCallback } from 'react';
import { TopBar } from './components/TopBar';
import { SummaryCard } from './components/SummaryCard';
import { DeviceTable } from './components/DeviceTable';
import { AlertPanel } from './components/AlertPanel';
import { ScanPanel } from './components/ScanPanel';
import { NotificationPanel } from './components/NotificationPanel';
import { AnalyticsPanel } from './components/AnalyticsPanel';
import { TopologyPanel } from './components/TopologyPanel';
import { IpamPanel } from './components/IpamPanel';
import { InternetHealthWidget } from './components/InternetHealthWidget';
import { WebMonitorWidget } from './components/WebMonitorWidget';
import { IncidentsPanel } from './components/IncidentsPanel';
import * as api from './services/api';
import './App.css';

function App() {
  // State
  const [activeTab, setActiveTab] = useState('dashboard');
  const [summary, setSummary] = useState(null);
  const [devices, setDevices] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [lastScan, setLastScan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'light');

  // Apply theme to document
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => setTheme(t => t === 'light' ? 'dark' : 'light');

  // Fetch all dashboard data
  const fetchData = useCallback(async () => {
    try {
      const [summaryData, devicesData, alertsData] = await Promise.all([
        api.getDashboardSummary(),
        api.getDevices(),
        api.getActiveAlerts(),
      ]);

      setSummary(summaryData);
      setDevices(devicesData);
      setAlerts(alertsData);
      setLastScan(summaryData.last_scan);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchData]);

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error && !summary) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="card p-8 text-center max-w-md">
          <div className="text-5xl mb-4">⚠️</div>
          <h2 className="text-xl font-semibold text-gray-800 mb-2">Connection Error</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <p className="text-sm text-gray-500 mb-4">
            Make sure the backend server is running on port 8000.
          </p>
          <button onClick={fetchData} className="btn btn-primary">
            Retry
          </button>
        </div>
      </div>
    );
  }

  const renderTabButton = (id, label, icon) => (
    <button
      onClick={() => setActiveTab(id)}
      className={`${activeTab === id
        ? 'text-white shadow-md'
        : 'hover:opacity-80 border'
        } px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2`}
      style={{
        backgroundColor: activeTab === id ? 'var(--accent-primary)' : 'var(--bg-secondary)',
        color: activeTab === id ? 'white' : 'var(--text-secondary)',
        borderColor: activeTab === id ? 'transparent' : 'var(--border-light)'
      }}
    >
      <span>{icon}</span>
      {label}
    </button>
  );

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--bg-primary)', color: 'var(--text-primary)' }}>
      {/* Top Bar */}
      <div className="no-print sticky top-0 z-50">
        <TopBar
          lastScan={lastScan}
          onRefresh={fetchData}
          autoRefresh={autoRefresh}
          onAutoRefreshChange={setAutoRefresh}
          theme={theme}
          onToggleTheme={toggleTheme}
        />
      </div>

      {/* Main Content */}
      <main className="p-6 max-w-[1600px] mx-auto">
        {/* Navigation Tabs */}
        <div className="mb-6">
          <div className="flex gap-2">
            {renderTabButton('dashboard', 'Dashboard', '📊')}
            {renderTabButton('incidents', 'Incidents', '🚨')}
            {renderTabButton('analytics', 'Analytics', '📈')}
            {renderTabButton('topology', 'Network Map', '🕸️')}
            {renderTabButton('tools', 'Tools', '🛠️')}
          </div>
        </div>

        {activeTab === 'dashboard' && (
          <div className="animate-fadeIn">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-10">
              <SummaryCard
                title="Total Devices"
                value={summary?.total_devices || 0}
                icon="🖥️"
                variant="info"
              />
              <SummaryCard
                title="Devices Up"
                value={summary?.devices_up || 0}
                icon="✓"
                variant="success"
              />
              <SummaryCard
                title="Devices Down"
                value={summary?.devices_down || 0}
                icon="✕"
                variant={summary?.devices_down > 0 ? 'danger' : 'default'}
              />
              <SummaryCard
                title="Critical Alerts"
                value={summary?.critical_alerts || 0}
                icon="🔴"
                variant={summary?.critical_alerts > 0 ? 'danger' : 'default'}
              />
              <SummaryCard
                title="Warnings"
                value={summary?.warning_alerts || 0}
                icon="⚠️"
                variant={summary?.warning_alerts > 0 ? 'warning' : 'default'}
              />
            </div>

            {/* Main Grid - Device Table and Sidebar */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              {/* Device Table - 2 columns */}
              <div className="lg:col-span-2">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="font-outfit text-lg font-bold flex items-center gap-3" style={{ color: 'var(--text-primary)' }}>
                    <span className="w-1 h-6 rounded-full" style={{ background: 'var(--color-primary)' }}></span>
                    Monitored Devices
                  </h2>
                  <span className="text-sm font-medium" style={{ color: 'var(--text-muted)' }}>
                    {devices.length} nodes
                  </span>
                </div>
                <div className="card">
                  <DeviceTable
                    devices={devices}
                    onDeviceClick={(device) => console.log('Device clicked:', device)}
                    onRefresh={fetchData}
                  />
                </div>
              </div>

              {/* Sidebar - 1 column */}
              <div className="space-y-6">
                <ScanPanel onScanComplete={fetchData} />
                <AlertPanel alerts={alerts} onRefresh={fetchData} />
                <NotificationPanel />
              </div>
            </div>
          </div>
        )}

        {activeTab === 'incidents' && (
          <div className="max-w-6xl mx-auto animate-fadeIn">
            <IncidentsPanel />
          </div>
        )}

        {activeTab === 'analytics' && (
          <div className="max-w-6xl mx-auto animate-fadeIn">
            <AnalyticsPanel />
          </div>
        )}

        {activeTab === 'topology' && (
          <div className="max-w-6xl mx-auto animate-fadeIn">
            <TopologyPanel />
          </div>
        )}

        {activeTab === 'tools' && (
          <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 animate-fadeIn">
            <IpamPanel />
            <InternetHealthWidget />
            <WebMonitorWidget />
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="py-8 text-center text-sm font-medium text-gray-400 mt-12 mb-4">
        <p>Mini NOC v1.0.0 • Enterprise Network Monitoring</p>
      </footer>
    </div>
  );
}

export default App;
