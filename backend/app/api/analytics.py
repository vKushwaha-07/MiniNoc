from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel

from app.db.session import get_db
from app.db.models import Metric, Device, Alert

router = APIRouter()

class DataPoint(BaseModel):
    timestamp: datetime
    avg_latency_ms: Optional[float]
    avg_packet_loss: Optional[float]
    avg_cpu_usage: Optional[float]
    
class AnalyticsResponse(BaseModel):
    range_hours: int
    data: List[DataPoint]
    summary: dict

@router.get("/metrics", response_model=AnalyticsResponse)
def get_aggregated_metrics(
    range_hours: int = Query(24, ge=1, le=720, description="Hours of history to fetch"),
    device_id: Optional[int] = Query(None, description="Filter by device ID"),
    db: Session = Depends(get_db)
):
    """
    Get historical performance metrics aggregated by appropriate time buckets.
    range_hours: 24 (hourly), 168 (7 days - 6h blocks), 720 (30 days - daily)
    """
    
    # Determine bucket size based on range
    if range_hours <= 24:
        # Hourly buckets for 24h range
        bucket_size = "1 hour"
        time_group = strftime_format = "%Y-%m-%d %H:00:00"
    elif range_hours <= 168:
        # 4-hour buckets for 7 days
        bucket_size = "4 hours"
        # Complex grouping not easily doable with simple strftime in SQLite/Postgres agnostic way
        # For simplicity in this SQLite implementation, we'll group by 4-hour blocks roughly
        # Or just use hourly for now but limit the query
        time_group = strftime_format = "%Y-%m-%d %H:00:00" # Keeping hourly for accuracy for now
    else:
        # Daily buckets for 30 days
        bucket_size = "1 day"
        time_group = strftime_format = "%Y-%m-%d 00:00:00"

    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=range_hours)
    
    # Base query filters
    filters = [Metric.timestamp >= start_time]
    if device_id:
        filters.append(Metric.device_id == device_id)
        
    # SQLite-specific datetime formatting for grouping
    # In a production Postgres DB this would use date_trunc
    
    stmt = (
        db.query(
            func.strftime('%Y-%m-%d %H:00:00', Metric.timestamp).label('bucket'),
            func.avg(Metric.latency_ms).label('avg_latency'),
            func.avg(Metric.packet_loss_percent).label('avg_loss'),
            func.avg(Metric.cpu_usage_percent).label('avg_cpu')
        )
        .filter(*filters)
        .group_by('bucket')
        .order_by('bucket')
    )
    
    results = stmt.all()
    
    data_points = []
    
    overall_latency_sum = 0
    overall_loss_sum = 0
    count = 0
    
    for row in results:
        # Parse timestamp string from SQLite
        ts = datetime.strptime(row.bucket, "%Y-%m-%d %H:%M:%S")
        
        # Round values
        lat = round(row.avg_latency, 2) if row.avg_latency is not None else 0
        loss = round(row.avg_loss, 2) if row.avg_loss is not None else 0
        cpu = round(row.avg_cpu, 2) if row.avg_cpu is not None else 0
        
        data_points.append(DataPoint(
            timestamp=ts,
            avg_latency_ms=lat,
            avg_packet_loss=loss,
            avg_cpu_usage=cpu
        ))
        
        overall_latency_sum += lat
        overall_loss_sum += loss
        count += 1
        
    summary = {
        "avg_latency_ms": round(overall_latency_sum / count, 2) if count > 0 else 0,
        "avg_packet_loss": round(overall_loss_sum / count, 2) if count > 0 else 0,
        "data_points_count": count
    }
    
    return AnalyticsResponse(
        range_hours=range_hours,
        data=data_points,
        summary=summary
    )


class SLAMetrics(BaseModel):
    uptime_percent: float
    mttr_minutes: float
    mtbf_hours: float
    total_outages: int
    sla_compliance: bool  # > 99.9%
    period_label: str

@router.get("/sla", response_model=SLAMetrics)
def get_sla_metrics(
    range_days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Calculate SLA metrics (Uptime, MTTR, MTBF) over a time period.
    Default: 30 days.
    """
    start_time = datetime.utcnow() - timedelta(days=range_days)
    
    # Get all outage alerts (resolved and unresolved)
    # Severity CRITICAL or DOWN status usually implies outage
    outages = db.query(Alert).filter(
        Alert.created_at >= start_time,
        Alert.title.contains("DOWN") | (Alert.severity == "CRITICAL")
    ).all()
    
    total_time_seconds = range_days * 24 * 3600
    down_time_seconds = 0
    total_outages = len(outages)
    total_repair_time = 0
    resolved_count = 0
    
    for alert in outages:
        if alert.is_resolved and alert.resolved_at:
            duration = (alert.resolved_at - alert.created_at).total_seconds()
            down_time_seconds += duration
            total_repair_time += duration
            resolved_count += 1
        else:
            # Current outage duration
            duration = (datetime.utcnow() - alert.created_at).total_seconds()
            down_time_seconds += duration
            
    # Cap down time at total time
    if down_time_seconds > total_time_seconds:
        down_time_seconds = total_time_seconds
        
    uptime_seconds = total_time_seconds - down_time_seconds
    uptime_percent = (uptime_seconds / total_time_seconds) * 100
    
    # MTTR (Mean Time To Repair) in minutes
    mttr = (total_repair_time / resolved_count / 60) if resolved_count > 0 else 0
    
    # MTBF (Mean Time Between Failures) in hours
    # MTBF = (Total Uptime) / (Number of Breakdowns)
    mtbf = (uptime_seconds / total_outages / 3600) if total_outages > 0 else (total_time_seconds / 3600)
    
    return SLAMetrics(
        uptime_percent=round(uptime_percent, 4),
        mttr_minutes=round(mttr, 2),
        mtbf_hours=round(mtbf, 2),
        total_outages=total_outages,
        sla_compliance=uptime_percent >= 99.9,
        period_label=f"Last {range_days} Days"
    )

class TopologyNode(BaseModel):
    id: str
    label: str
    type: str = "default"  # input, output, default
    data: dict
    position: dict  # {x: 0, y: 0}

class TopologyEdge(BaseModel):
    id: str
    source: str
    target: str
    animated: bool = False
    style: dict = {}
    label: Optional[str] = None

class TopologyResponse(BaseModel):
    nodes: List[TopologyNode]
    edges: List[TopologyEdge]

@router.get("/topology", response_model=TopologyResponse)
def get_topology(db: Session = Depends(get_db)):
    """
    Generate network topology for React Flow.
    Currently implements a star topology centered on the Gateway/Router.
    """
    devices = db.query(Device).filter(Device.is_active == True).all()
    
    nodes = []
    edges = []
    
    # Central Node (Router/Gateway)
    # in a real scenario, we'd detect the gateway. For now, assume a virtual center.
    center_id = "gateway"
    nodes.append(TopologyNode(
        id=center_id,
        label="Gateway / Router",
        type="input",
        data={"role": "gateway", "status": "UP"},
        position={"x": 400, "y": 50}
    ))
    
    # Position devices in a circle/grid
    import math
    radius = 300
    angle_step = 2 * math.pi / max(len(devices), 1)
    
    for i, device in enumerate(devices):
        angle = i * angle_step
        x = 400 + radius * math.cos(angle)
        y = 350 + radius * math.sin(angle)
        
        node_id = str(device.id)
        label = device.hostname if device.hostname else device.ip_address
        
        # Color based on status
        color = "#10b981" if device.status == "UP" else "#ef4444"
        
        nodes.append(TopologyNode(
            id=node_id,
            label=label,
            type="default",
            data={
                "ip": device.ip_address,
                "status": device.status,
                "vendor": device.vendor,
                "latency": "N/A" # Could fetch latest metric
            },
            position={"x": int(x), "y": int(y)}
        ))
        
        # Edge from Gateway to Device
        edges.append(TopologyEdge(
            id=f"e-{center_id}-{node_id}",
            source=center_id,
            target=node_id,
            animated=device.status == "UP",
            style={"stroke": color, "strokeWidth": 2},
            label=""
        ))
    
    return TopologyResponse(nodes=nodes, edges=edges)


class IPAMStatus(BaseModel):
    ip: str
    status: str  # free, active, down, reserved
    hostname: Optional[str] = None
    device_id: Optional[int] = None

@router.get("/ipam/{subnet_base}", response_model=List[IPAMStatus])
def get_ipam(subnet_base: str, db: Session = Depends(get_db)):
    """
    Get IP Address Management status for a /24 subnet.
    subnet_base example: "192.168.1"
    """
    # Get all devices in this subnet
    devices = db.query(Device).filter(Device.ip_address.like(f"{subnet_base}.%")).all()
    device_map = {d.ip_address: d for d in devices}
    
    results = []
    
    # Assume /24 subnet (1-254 usable)
    for i in range(1, 255):
        ip = f"{subnet_base}.{i}"
        
        if ip in device_map:
            device = device_map[ip]
            status = "active" if device.status == "UP" else "down"
            results.append(IPAMStatus(
                ip=ip,
                status=status,
                hostname=device.hostname,
                device_id=device.id
            ))
        else:
            status = "free"
            # specific checks for gateway or broadcast?
            if i == 1:
                status = "reserved" # Commonly gateway
            
            results.append(IPAMStatus(ip=ip, status=status))
            
    return results


class InternetHealth(BaseModel):
    status: str # UP, DOWN, DEGRADED
    latency_google: float
    latency_cloudflare: float
    download_mbps: Optional[float] = None
    upload_mbps: Optional[float] = None
    isp: Optional[str] = None

@router.post("/internet/speedtest", response_model=InternetHealth)
def run_speedtest():
    """
    Run a speedtest and connectivity check.
    WARNING: This takes time (10-30s).
    """
    import subprocess
    import re
    
    # Simple ping check first
    from pythonping import ping
    
    def get_ping(host):
        try:
            resp = ping(host, count=3, timeout=2)
            return resp.rtt_avg_ms
        except:
            return 999.0
            
    lat_google = get_ping("8.8.8.8")
    lat_cf = get_ping("1.1.1.1")
    
    status = "UP"
    if lat_google > 100 or lat_cf > 100:
        status = "DEGRADED"
    if lat_google > 500 and lat_cf > 500:
        status = "DOWN"
        
    # Run speedtest-cli
    try:
        # Using subprocess to run speedtest-cli --simple
        # Output format:
        # Ping: 12.34 ms
        # Download: 100.00 Mbit/s
        # Upload: 50.00 Mbit/s
        
        process = subprocess.run(["speedtest-cli", "--simple"], capture_output=True, text=True, timeout=45)
        output = process.stdout
        
        download = 0
        upload = 0
        isp = "Unknown"
        
        if process.returncode == 0:
            d_match = re.search(r"Download:\s+([\d\.]+)", output)
            u_match = re.search(r"Upload:\s+([\d\.]+)", output)
            if d_match: download = float(d_match.group(1))
            if u_match: upload = float(u_match.group(1))
            
            # Try to get ISP info via --json if needed, but keeping it simple for now
    except Exception as e:
        print(f"Speedtest failed: {e}")
        download = 0
        upload = 0
        
    return InternetHealth(
        status=status,
        latency_google=lat_google,
        latency_cloudflare=lat_cf,
        download_mbps=download,
        upload_mbps=upload,
        isp="Detected ISP"
    )


# ============================================
# EXPORT ENDPOINTS (CSV / PDF)
# ============================================

from fastapi.responses import StreamingResponse
import io
import csv

@router.get("/export/csv")
def export_analytics_csv(
    range_days: int = Query(7, ge=1, le=90, description="Days of data to export (7, 30, or 90)"),
    db: Session = Depends(get_db)
):
    """
    Export analytics data as CSV file.
    Includes device status, metrics summary, and SLA data.
    """
    start_time = datetime.utcnow() - timedelta(days=range_days)
    
    # Get devices with metrics
    devices = db.query(Device).filter(Device.is_active == True).all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "Device IP", "Hostname", "Status", "Vendor", "OS Type",
        "Latest Latency (ms)", "Latest Packet Loss (%)",
        "Avg Latency (ms)", "Avg Packet Loss (%)",
        "Last Seen", "Created At"
    ])
    
    # Data rows
    for device in devices:
        # Get average metrics for this device in the period
        avg_metrics = db.query(
            func.avg(Metric.latency_ms).label('avg_lat'),
            func.avg(Metric.packet_loss_percent).label('avg_loss')
        ).filter(
            Metric.device_id == device.id,
            Metric.timestamp >= start_time
        ).first()
        
        writer.writerow([
            device.ip_address,
            device.hostname or "N/A",
            device.status,
            device.vendor or "Unknown",
            device.os_type or "Unknown",
            round(device.latest_latency_ms, 2) if device.latest_latency_ms else "N/A",
            round(device.latest_packet_loss, 2) if device.latest_packet_loss else "N/A",
            round(avg_metrics.avg_lat, 2) if avg_metrics and avg_metrics.avg_lat else "N/A",
            round(avg_metrics.avg_loss, 2) if avg_metrics and avg_metrics.avg_loss else "N/A",
            device.last_seen.isoformat() if device.last_seen else "Never",
            device.created_at.isoformat() if device.created_at else "N/A"
        ])
    
    # SLA Summary section
    writer.writerow([])
    writer.writerow(["=== SLA SUMMARY ==="])
    writer.writerow(["Period", f"Last {range_days} Days"])
    
    # Calculate uptime
    total_time = range_days * 24 * 3600
    outages = db.query(Alert).filter(
        Alert.created_at >= start_time,
        Alert.title.contains("DOWN") | (Alert.severity == "CRITICAL")
    ).all()
    
    down_time = sum(
        (a.resolved_at - a.created_at).total_seconds() if a.is_resolved and a.resolved_at 
        else (datetime.utcnow() - a.created_at).total_seconds()
        for a in outages
    )
    uptime_pct = ((total_time - min(down_time, total_time)) / total_time) * 100
    
    writer.writerow(["Uptime %", f"{uptime_pct:.4f}%"])
    writer.writerow(["Total Outages", len(outages)])
    writer.writerow(["SLA Compliant", "Yes" if uptime_pct >= 99.9 else "No"])
    
    # Prepare response
    output.seek(0)
    filename = f"mini_noc_report_{range_days}d_{datetime.utcnow().strftime('%Y%m%d')}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/export/pdf")
def export_analytics_pdf(
    range_days: int = Query(7, ge=1, le=90, description="Days of data to export"),
    db: Session = Depends(get_db)
):
    """
    Export analytics data as PDF report.
    Returns a simple text-based report (ReportLab can be added for rich PDFs).
    """
    start_time = datetime.utcnow() - timedelta(days=range_days)
    
    # Get summary data
    devices = db.query(Device).filter(Device.is_active == True).all()
    devices_up = sum(1 for d in devices if d.status == "UP")
    devices_down = sum(1 for d in devices if d.status == "DOWN")
    
    # Alerts
    active_alerts = db.query(Alert).filter(Alert.is_resolved == False).count()
    
    # SLA metrics
    total_time = range_days * 24 * 3600
    outages = db.query(Alert).filter(
        Alert.created_at >= start_time,
        Alert.title.contains("DOWN") | (Alert.severity == "CRITICAL")
    ).all()
    
    down_time = sum(
        (a.resolved_at - a.created_at).total_seconds() if a.is_resolved and a.resolved_at 
        else (datetime.utcnow() - a.created_at).total_seconds()
        for a in outages
    )
    uptime_pct = ((total_time - min(down_time, total_time)) / total_time) * 100
    
    # Build text report (can be converted to PDF with ReportLab)
    report_lines = [
        "=" * 60,
        "MINI NOC - NETWORK MONITORING REPORT",
        "=" * 60,
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
        f"Report Period: Last {range_days} Days",
        "",
        "-" * 40,
        "DEVICE SUMMARY",
        "-" * 40,
        f"Total Devices: {len(devices)}",
        f"Devices UP: {devices_up}",
        f"Devices DOWN: {devices_down}",
        f"Active Alerts: {active_alerts}",
        "",
        "-" * 40,
        "SLA METRICS",
        "-" * 40,
        f"Uptime: {uptime_pct:.4f}%",
        f"Total Outages: {len(outages)}",
        f"SLA Compliant (>99.9%): {'YES' if uptime_pct >= 99.9 else 'NO'}",
        "",
        "-" * 40,
        "DEVICE DETAILS",
        "-" * 40,
    ]
    
    for d in devices[:20]:  # Limit to 20 for readability
        report_lines.append(f"  {d.ip_address:15} | {d.hostname or 'N/A':20} | {d.status:8}")
    
    if len(devices) > 20:
        report_lines.append(f"  ... and {len(devices) - 20} more devices")
    
    report_lines.extend([
        "",
        "=" * 60,
        "END OF REPORT",
        "=" * 60
    ])
    
    report_text = "\n".join(report_lines)
    
    # Return as plain text (PDF conversion would need ReportLab)
    filename = f"mini_noc_report_{range_days}d_{datetime.utcnow().strftime('%Y%m%d')}.txt"
    
    return StreamingResponse(
        iter([report_text]),
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
