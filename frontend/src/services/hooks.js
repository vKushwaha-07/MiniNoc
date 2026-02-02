import { useState, useEffect, useCallback } from 'react';
import * as api from './api';

/**
 * Custom hook for fetching data with loading and error states.
 */
export function useApiData(fetchFn, dependencies = []) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const refetch = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const result = await fetchFn();
            setData(result);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, [fetchFn]);

    useEffect(() => {
        refetch();
    }, dependencies);

    return { data, loading, error, refetch };
}

/**
 * Hook for dashboard summary data.
 */
export function useDashboardSummary() {
    return useApiData(api.getDashboardSummary);
}

/**
 * Hook for devices list.
 */
export function useDevices(params = {}) {
    const fetchFn = useCallback(() => api.getDevices(params), [JSON.stringify(params)]);
    return useApiData(fetchFn, [JSON.stringify(params)]);
}

/**
 * Hook for active alerts.
 */
export function useActiveAlerts() {
    return useApiData(api.getActiveAlerts);
}

/**
 * Hook for alert summary.
 */
export function useAlertSummary() {
    return useApiData(api.getAlertSummary);
}

/**
 * Hook for device metrics.
 */
export function useDeviceMetrics(deviceId, hours = 24) {
    const fetchFn = useCallback(
        () => api.getDeviceMetrics(deviceId, hours),
        [deviceId, hours]
    );
    return useApiData(fetchFn, [deviceId, hours]);
}

/**
 * Hook for auto-refresh functionality.
 */
export function useAutoRefresh(refetchFn, intervalMs = 30000, enabled = true) {
    useEffect(() => {
        if (!enabled) return;

        const interval = setInterval(() => {
            refetchFn();
        }, intervalMs);

        return () => clearInterval(interval);
    }, [refetchFn, intervalMs, enabled]);
}

/**
 * Hook for managing multiple refetch functions.
 */
export function useDashboardState() {
    const summary = useDashboardSummary();
    const devices = useDevices();
    const alerts = useActiveAlerts();

    const refetchAll = useCallback(() => {
        summary.refetch();
        devices.refetch();
        alerts.refetch();
    }, [summary.refetch, devices.refetch, alerts.refetch]);

    return {
        summary,
        devices,
        alerts,
        refetchAll,
        isLoading: summary.loading || devices.loading || alerts.loading,
        hasError: summary.error || devices.error || alerts.error,
    };
}
