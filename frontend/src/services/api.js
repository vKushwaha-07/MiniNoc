/**
 * API Service for Mini NOC Dashboard.
 * Handles all communication with the FastAPI backend.
 */

const API_BASE_URL = 'http://localhost:8000/api';

/**
 * Generic fetch wrapper with error handling.
 */
async function fetchApi(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;

    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };

    const response = await fetch(url, { ...defaultOptions, ...options });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
    }

    // Handle 204 No Content
    if (response.status === 204) {
        return null;
    }

    return response.json();
}

// ============== Dashboard ==============

export async function getDashboardSummary() {
    return fetchApi('/dashboard/summary');
}

// ============== Devices ==============

export async function getDevices(params = {}) {
    const query = new URLSearchParams(params).toString();
    return fetchApi(`/devices${query ? `?${query}` : ''}`);
}

export async function getDevice(deviceId) {
    return fetchApi(`/devices/${deviceId}`);
}

export async function createDevice(deviceData) {
    return fetchApi('/devices', {
        method: 'POST',
        body: JSON.stringify(deviceData),
    });
}

export async function updateDevice(deviceId, deviceData) {
    return fetchApi(`/devices/${deviceId}`, {
        method: 'PUT',
        body: JSON.stringify(deviceData),
    });
}

export async function deleteDevice(deviceId) {
    return fetchApi(`/devices/${deviceId}`, {
        method: 'DELETE',
    });
}

export async function getDeviceStats() {
    return fetchApi('/devices/summary/stats');
}

// ============== Metrics ==============

export async function getDeviceMetrics(deviceId, hours = 24) {
    return fetchApi(`/metrics/${deviceId}?hours=${hours}`);
}

export async function getLatestMetric(deviceId) {
    return fetchApi(`/metrics/${deviceId}/latest`);
}

export async function getMetricsSummary(deviceId, hours = 24) {
    return fetchApi(`/metrics/${deviceId}/summary?hours=${hours}`);
}

// ============== Alerts ==============

export async function getAlerts(params = {}) {
    const query = new URLSearchParams(params).toString();
    return fetchApi(`/alerts${query ? `?${query}` : ''}`);
}

export async function getActiveAlerts() {
    return fetchApi('/alerts/active');
}

export async function getAlertSummary() {
    return fetchApi('/alerts/summary');
}

export async function resolveAlert(alertId) {
    return fetchApi(`/alerts/${alertId}/resolve`, {
        method: 'PATCH',
        body: JSON.stringify({ is_resolved: true }),
    });
}

export async function resolveAllAlerts(params = {}) {
    const query = new URLSearchParams(params).toString();
    return fetchApi(`/alerts/resolve-all${query ? `?${query}` : ''}`, {
        method: 'POST',
    });
}

// ============== Scanning ==============

// ============== Scanning ==============

export async function getLocalNetwork() {
    return fetchApi('/discovery/local-network');
}

export async function discoverSubnet(subnet, addDiscovered = true) {
    return fetchApi('/scan/discover', {
        method: 'POST',
        body: JSON.stringify({ subnet, add_discovered: addDiscovered }),
    });
}

export async function triggerHealthCheck() {
    return fetchApi('/scan/health-check', {
        method: 'POST',
    });
}

export async function getScanLogs(limit = 50) {
    return fetchApi(`/scan/logs?limit=${limit}`);
}

export async function getLatestScan() {
    return fetchApi('/scan/logs/latest');
}

// ============== Health ==============

export async function checkHealth() {
    const response = await fetch('http://localhost:8000/health');
    return response.json();
}

// ============== Device Discovery ==============

export async function discoverDevice(ipAddress, fullScan = true) {
    return fetchApi('/discovery/device', {
        method: 'POST',
        body: JSON.stringify({ ip_address: ipAddress, full_scan: fullScan }),
    });
}

export async function enrichDevice(deviceId, fullScan = true) {
    return fetchApi(`/control/enrich/${deviceId}?full_scan=${fullScan}`, {
        method: 'POST',
    });
}

export async function enrichAllDevices(fullScan = false) {
    return fetchApi(`/discovery/enrich-all?full_scan=${fullScan}`, {
        method: 'POST',
    });
}

// ============== Notifications ==============

export async function getNotificationConfig() {
    return fetchApi('/notifications/config');
}

export async function updateNotificationConfig(config) {
    return fetchApi('/notifications/config', {
        method: 'POST',
        body: JSON.stringify(config),
    });
}

export async function testNotification(channel, message = 'Test notification') {
    return fetchApi('/notifications/test', {
        method: 'POST',
        body: JSON.stringify({ channel, message }),
    });
}

export async function sendNotification(title, message, severity = 'INFO', deviceIp = null) {
    const params = new URLSearchParams({ title, message, severity });
    if (deviceIp) params.append('device_ip', deviceIp);
    return fetchApi(`/notifications/send?${params.toString()}`, {
        method: 'POST',
    });
}

// ============== Delete All (for testing) ==============

export async function deleteAllDevices() {
    return fetchApi('/devices/all?confirm=true', {
        method: 'DELETE',
    });
}

// ============== Analytics & Tools ==============

export async function getAnalyticsMetrics(rangeHours = 24, deviceId = null) {
    const params = new URLSearchParams({ range_hours: rangeHours });
    if (deviceId) params.append('device_id', deviceId);
    return fetchApi(`/analytics/metrics?${params.toString()}`);
}

export async function getSLAMetrics(rangeDays = 30) {
    return fetchApi(`/analytics/sla?range_days=${rangeDays}`);
}

export async function getTopology() {
    return fetchApi('/analytics/topology');
}

export async function getIpam(subnet) {
    return fetchApi(`/analytics/ipam/${subnet}`);
}

export async function runSpeedtest() {
    return fetchApi('/analytics/internet/speedtest', {
        method: 'POST'
    });
}

// ============== Web Monitor & Controls ==============

export async function getWebTargets() {
    return fetchApi('/web/targets');
}

export async function checkAllWebsites() {
    return fetchApi('/web/check-all', { method: 'POST' });
}

export async function wakeDevice(macAddress) {
    return fetchApi('/control/wol', {
        method: 'POST',
        body: JSON.stringify({ mac_address: macAddress })
    });
}

export async function testSsh(ip, username, password, port = 22) {
    return fetchApi('/control/ssh/test', {
        method: 'POST',
        body: JSON.stringify({ ip, username, password, port })
    });
}
