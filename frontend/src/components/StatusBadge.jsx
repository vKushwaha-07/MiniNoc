/**
 * Status Badge Component.
 * Displays device status with appropriate styling.
 */

export function StatusBadge({ status }) {
    const statusConfig = {
        UP: { class: 'status-up', label: 'UP' },
        DOWN: { class: 'status-down', label: 'DOWN' },
        DEGRADED: { class: 'status-warning', label: 'DEGRADED' },
        UNKNOWN: { class: 'status-unknown', label: 'UNKNOWN' },
    };

    const config = statusConfig[status] || statusConfig.UNKNOWN;

    return (
        <span className={`status-badge ${config.class}`}>
            <span className="status-dot"></span>
            {config.label}
        </span>
    );
}

/**
 * Severity Badge for Alerts.
 */
export function SeverityBadge({ severity }) {
    const severityConfig = {
        CRITICAL: { class: 'status-down', label: 'CRITICAL' },
        WARNING: { class: 'status-warning', label: 'WARNING' },
        INFO: { class: 'status-up', label: 'INFO' },
    };

    const config = severityConfig[severity] || severityConfig.INFO;

    return (
        <span className={`status-badge ${config.class}`}>
            {config.label}
        </span>
    );
}

export default StatusBadge;
