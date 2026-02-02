/**
 * Incidents Panel Component.
 * Displays and manages network incidents with timeline view.
 */

import { useState, useEffect } from 'react';
import * as api from '../services/api';

const STATUS_COLORS = {
    OPEN: { bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-300' },
    INVESTIGATING: { bg: 'bg-orange-100', text: 'text-orange-700', border: 'border-orange-300' },
    IDENTIFIED: { bg: 'bg-yellow-100', text: 'text-yellow-700', border: 'border-yellow-300' },
    MONITORING: { bg: 'bg-blue-100', text: 'text-blue-700', border: 'border-blue-300' },
    RESOLVED: { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-300' }
};

const PRIORITY_COLORS = {
    P1: { bg: 'bg-red-600', text: 'text-white' },
    P2: { bg: 'bg-orange-500', text: 'text-white' },
    P3: { bg: 'bg-yellow-500', text: 'text-black' },
    P4: { bg: 'bg-gray-400', text: 'text-white' }
};

export function IncidentsPanel() {
    const [incidents, setIncidents] = useState([]);
    const [selectedIncident, setSelectedIncident] = useState(null);
    const [timeline, setTimeline] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [statusFilter, setStatusFilter] = useState('');
    const [newIncident, setNewIncident] = useState({
        title: '',
        description: '',
        priority: 'P3',
        impact_summary: ''
    });
    const [newUpdate, setNewUpdate] = useState('');

    useEffect(() => {
        loadIncidents();
    }, [statusFilter]);

    const loadIncidents = async () => {
        setLoading(true);
        try {
            const url = statusFilter
                ? `/api/incidents?status=${statusFilter}`
                : '/api/incidents';
            const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}${url}`);
            const data = await response.json();
            setIncidents(data);
        } catch (err) {
            console.error('Failed to load incidents:', err);
        } finally {
            setLoading(false);
        }
    };

    const loadTimeline = async (incidentId) => {
        try {
            const response = await fetch(
                `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/incidents/${incidentId}/timeline`
            );
            const data = await response.json();
            setTimeline(data);
        } catch (err) {
            console.error('Failed to load timeline:', err);
        }
    };

    const selectIncident = async (incident) => {
        setSelectedIncident(incident);
        await loadTimeline(incident.id);
    };

    const createIncident = async () => {
        try {
            const response = await fetch(
                `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/incidents`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(newIncident)
                }
            );
            if (response.ok) {
                setShowCreateModal(false);
                setNewIncident({ title: '', description: '', priority: 'P3', impact_summary: '' });
                loadIncidents();
            }
        } catch (err) {
            console.error('Failed to create incident:', err);
        }
    };

    const updateIncidentStatus = async (incidentId, newStatus) => {
        try {
            const response = await fetch(
                `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/incidents/${incidentId}`,
                {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status: newStatus })
                }
            );
            if (response.ok) {
                loadIncidents();
                if (selectedIncident?.id === incidentId) {
                    const updated = await response.json();
                    setSelectedIncident(updated);
                    loadTimeline(incidentId);
                }
            }
        } catch (err) {
            console.error('Failed to update status:', err);
        }
    };

    const addTimelineUpdate = async () => {
        if (!newUpdate.trim() || !selectedIncident) return;

        try {
            const response = await fetch(
                `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/incidents/${selectedIncident.id}/timeline`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: newUpdate, update_type: 'update' })
                }
            );
            if (response.ok) {
                setNewUpdate('');
                loadTimeline(selectedIncident.id);
            }
        } catch (err) {
            console.error('Failed to add update:', err);
        }
    };

    const formatDate = (dateStr) => {
        const date = new Date(dateStr);
        return date.toLocaleString([], {
            month: 'short', day: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col md:flex-row justify-between items-center gap-4"
                style={{ backgroundColor: 'var(--bg-secondary)', padding: '1rem', borderRadius: '12px', border: '1px solid var(--border-light)' }}>
                <div>
                    <h2 className="text-xl font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                        <span>🚨</span> Incident Management
                    </h2>
                    <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
                        Track and manage network incidents
                    </p>
                </div>

                <div className="flex gap-3">
                    <select
                        value={statusFilter}
                        onChange={(e) => setStatusFilter(e.target.value)}
                        className="px-3 py-2 rounded-lg text-sm"
                        style={{
                            backgroundColor: 'var(--bg-tertiary)',
                            color: 'var(--text-primary)',
                            border: '1px solid var(--border-light)'
                        }}
                    >
                        <option value="">All Statuses</option>
                        <option value="OPEN">Open</option>
                        <option value="INVESTIGATING">Investigating</option>
                        <option value="IDENTIFIED">Identified</option>
                        <option value="MONITORING">Monitoring</option>
                        <option value="RESOLVED">Resolved</option>
                    </select>

                    <button
                        onClick={() => setShowCreateModal(true)}
                        className="btn btn-primary"
                    >
                        + New Incident
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Incidents List */}
                <div className="lg:col-span-1 space-y-3">
                    <h3 className="text-sm font-semibold uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>
                        Active Incidents ({incidents.length})
                    </h3>

                    {loading ? (
                        <div className="text-center py-8" style={{ color: 'var(--text-muted)' }}>Loading...</div>
                    ) : incidents.length === 0 ? (
                        <div className="text-center py-8 rounded-lg" style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--text-muted)' }}>
                            <p className="text-4xl mb-2">✨</p>
                            <p>No incidents found</p>
                        </div>
                    ) : (
                        incidents.map(incident => (
                            <div
                                key={incident.id}
                                onClick={() => selectIncident(incident)}
                                className={`p-4 rounded-lg cursor-pointer transition-all ${selectedIncident?.id === incident.id ? 'ring-2 ring-blue-500' : ''
                                    }`}
                                style={{
                                    backgroundColor: 'var(--bg-secondary)',
                                    border: '1px solid var(--border-light)'
                                }}
                            >
                                <div className="flex items-start justify-between gap-2 mb-2">
                                    <span className={`px-2 py-0.5 rounded text-xs font-bold ${PRIORITY_COLORS[incident.priority]?.bg} ${PRIORITY_COLORS[incident.priority]?.text}`}>
                                        {incident.priority}
                                    </span>
                                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[incident.status]?.bg} ${STATUS_COLORS[incident.status]?.text}`}>
                                        {incident.status}
                                    </span>
                                </div>
                                <h4 className="font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>
                                    {incident.title}
                                </h4>
                                <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                                    Created {formatDate(incident.created_at)}
                                </p>
                            </div>
                        ))
                    )}
                </div>

                {/* Selected Incident Details */}
                <div className="lg:col-span-2">
                    {selectedIncident ? (
                        <div className="space-y-4">
                            {/* Incident Header */}
                            <div className="p-6 rounded-lg" style={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-light)' }}>
                                <div className="flex items-start justify-between mb-4">
                                    <div>
                                        <div className="flex items-center gap-2 mb-2">
                                            <span className={`px-3 py-1 rounded font-bold ${PRIORITY_COLORS[selectedIncident.priority]?.bg} ${PRIORITY_COLORS[selectedIncident.priority]?.text}`}>
                                                {selectedIncident.priority}
                                            </span>
                                            <span className={`px-3 py-1 rounded font-medium ${STATUS_COLORS[selectedIncident.status]?.bg} ${STATUS_COLORS[selectedIncident.status]?.text}`}>
                                                {selectedIncident.status}
                                            </span>
                                        </div>
                                        <h2 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                                            {selectedIncident.title}
                                        </h2>
                                    </div>
                                </div>

                                {selectedIncident.description && (
                                    <p className="mb-4" style={{ color: 'var(--text-secondary)' }}>
                                        {selectedIncident.description}
                                    </p>
                                )}

                                {/* Status Buttons */}
                                <div className="flex flex-wrap gap-2">
                                    {['INVESTIGATING', 'IDENTIFIED', 'MONITORING', 'RESOLVED'].map(status => (
                                        <button
                                            key={status}
                                            onClick={() => updateIncidentStatus(selectedIncident.id, status)}
                                            disabled={selectedIncident.status === status}
                                            className={`px-3 py-1.5 rounded text-sm font-medium transition-all ${selectedIncident.status === status
                                                    ? 'opacity-50 cursor-not-allowed'
                                                    : 'hover:opacity-80'
                                                } ${STATUS_COLORS[status]?.bg} ${STATUS_COLORS[status]?.text}`}
                                        >
                                            → {status}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Timeline */}
                            <div className="p-6 rounded-lg" style={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-light)' }}>
                                <h3 className="text-lg font-bold mb-4" style={{ color: 'var(--text-primary)' }}>
                                    📋 Timeline
                                </h3>

                                {/* Add Update */}
                                <div className="flex gap-2 mb-6">
                                    <input
                                        type="text"
                                        value={newUpdate}
                                        onChange={(e) => setNewUpdate(e.target.value)}
                                        placeholder="Add an update..."
                                        className="flex-1 px-4 py-2 rounded-lg"
                                        style={{
                                            backgroundColor: 'var(--bg-tertiary)',
                                            color: 'var(--text-primary)',
                                            border: '1px solid var(--border-light)'
                                        }}
                                        onKeyPress={(e) => e.key === 'Enter' && addTimelineUpdate()}
                                    />
                                    <button onClick={addTimelineUpdate} className="btn btn-primary">
                                        Add
                                    </button>
                                </div>

                                {/* Timeline Entries */}
                                <div className="space-y-4">
                                    {timeline.map((entry, idx) => (
                                        <div key={entry.id} className="flex gap-4">
                                            <div className="flex flex-col items-center">
                                                <div
                                                    className="w-3 h-3 rounded-full"
                                                    style={{ backgroundColor: entry.update_type === 'status_change' ? 'var(--accent-primary)' : 'var(--border-medium)' }}
                                                ></div>
                                                {idx < timeline.length - 1 && (
                                                    <div className="w-0.5 flex-1" style={{ backgroundColor: 'var(--border-light)' }}></div>
                                                )}
                                            </div>
                                            <div className="flex-1 pb-4">
                                                <p className="font-medium" style={{ color: 'var(--text-primary)' }}>
                                                    {entry.message}
                                                </p>
                                                <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                                                    {formatDate(entry.created_at)}
                                                    {entry.created_by && ` • ${entry.created_by}`}
                                                </p>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="h-full flex items-center justify-center rounded-lg p-12"
                            style={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-light)' }}>
                            <div className="text-center">
                                <p className="text-4xl mb-4">📋</p>
                                <p style={{ color: 'var(--text-muted)' }}>Select an incident to view details</p>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Create Modal */}
            {showCreateModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="w-full max-w-lg p-6 rounded-xl" style={{ backgroundColor: 'var(--bg-secondary)' }}>
                        <h2 className="text-xl font-bold mb-4" style={{ color: 'var(--text-primary)' }}>
                            Create New Incident
                        </h2>

                        <div className="space-y-4">
                            <div>
                                <label className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>Title</label>
                                <input
                                    type="text"
                                    value={newIncident.title}
                                    onChange={(e) => setNewIncident({ ...newIncident, title: e.target.value })}
                                    className="w-full mt-1 px-4 py-2 rounded-lg"
                                    style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-primary)', border: '1px solid var(--border-light)' }}
                                    placeholder="e.g., Database connectivity issues"
                                />
                            </div>

                            <div>
                                <label className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>Priority</label>
                                <select
                                    value={newIncident.priority}
                                    onChange={(e) => setNewIncident({ ...newIncident, priority: e.target.value })}
                                    className="w-full mt-1 px-4 py-2 rounded-lg"
                                    style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-primary)', border: '1px solid var(--border-light)' }}
                                >
                                    <option value="P1">P1 - Critical (Full Outage)</option>
                                    <option value="P2">P2 - High (Major Degradation)</option>
                                    <option value="P3">P3 - Medium (Partial Issues)</option>
                                    <option value="P4">P4 - Low (Minor Issues)</option>
                                </select>
                            </div>

                            <div>
                                <label className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>Description</label>
                                <textarea
                                    value={newIncident.description}
                                    onChange={(e) => setNewIncident({ ...newIncident, description: e.target.value })}
                                    className="w-full mt-1 px-4 py-2 rounded-lg h-24"
                                    style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-primary)', border: '1px solid var(--border-light)' }}
                                    placeholder="Describe the issue..."
                                />
                            </div>

                            <div>
                                <label className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>Impact Summary</label>
                                <input
                                    type="text"
                                    value={newIncident.impact_summary}
                                    onChange={(e) => setNewIncident({ ...newIncident, impact_summary: e.target.value })}
                                    className="w-full mt-1 px-4 py-2 rounded-lg"
                                    style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-primary)', border: '1px solid var(--border-light)' }}
                                    placeholder="e.g., 50% of users affected"
                                />
                            </div>
                        </div>

                        <div className="flex justify-end gap-3 mt-6">
                            <button
                                onClick={() => setShowCreateModal(false)}
                                className="px-4 py-2 rounded-lg"
                                style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-primary)' }}
                            >
                                Cancel
                            </button>
                            <button
                                onClick={createIncident}
                                disabled={!newIncident.title}
                                className="btn btn-primary disabled:opacity-50"
                            >
                                Create Incident
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default IncidentsPanel;
