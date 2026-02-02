# Mini NOC - Getting Started Guide

Welcome to **Mini NOC**, an enterprise-grade Network Operations Center for monitoring network devices, tracking incidents, and maintaining uptime.

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.10+** (backend)
- **Node.js 18+** (frontend)
- **Redis** (for Celery background tasks)

### 1. Clone and Install

```bash
# Backend
cd mini-noc/backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

### 2. Start Services

```bash
# Terminal 1: Backend API
cd backend
python -m uvicorn main:app --reload --port 8000

# Terminal 2: Celery Worker (for background scans)
cd backend
celery -A app.core.celery_app worker --loglevel=info

# Terminal 3: Frontend
cd frontend
npm run dev
```

### 3. Access Dashboard
- **Frontend**: http://localhost:5173
- **API Docs**: http://localhost:8000/docs
- **Metrics**: http://localhost:8000/metrics

---

## 🖥️ Core Features

### Dashboard
- Real-time device status (UP/DOWN/DEGRADED)
- Summary cards with key metrics
- Auto-refresh every 30 seconds

### Device Management
- Add devices manually or via subnet discovery
- View latency, packet loss, and uptime
- Enhanced discovery captures: MAC, vendor, OS, open ports

### 🚨 Incident Management
- Create and track incidents (P1-P4 priority)
- Timeline with status updates
- Link alerts to incidents

### 📊 Analytics
- SLA compliance metrics
- Trend charts for latency/availability
- Export to CSV or PDF reports

### 🔔 Alerts
- Automatic alerts for device failures
- Severity levels: INFO, WARNING, CRITICAL
- Email notifications (configure in settings)

---

## 📚 API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/devices` | GET | List all devices |
| `/api/devices` | POST | Add new device |
| `/api/scan/discover` | POST | Scan subnet |
| `/api/alerts` | GET | List alerts |
| `/api/incidents` | GET/POST | Manage incidents |
| `/api/analytics/summary` | GET | Get analytics |

Full Swagger docs at: `http://localhost:8000/docs`

---

## ⚙️ Configuration

### Environment Variables

```env
# Backend (.env)
DATABASE_URL=sqlite:///./mini_noc.db
CELERY_BROKER_URL=redis://localhost:6379/0
CRON_SECRET=your-secret-for-vercel-cron

# Email Notifications
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@email.com
SMTP_PASSWORD=app-password

# Frontend (frontend/.env)
VITE_API_URL=http://localhost:8000
```

---

## 🌐 Vercel Deployment

1. Push code to GitHub
2. Import project in Vercel
3. Set build settings:
   - **Backend**: `cd backend && pip install -r requirements.txt`
   - **Frontend**: `cd frontend && npm run build`
4. Add environment variables in Vercel dashboard
5. Configure CRON_SECRET for scheduled health checks

---

## 🎨 Dark Mode

Click the 🌙/☀️ icon in the top bar to toggle dark mode. Theme preference is saved automatically.

---

## 🔒 Security Features

- Rate limiting: 100 requests/minute per IP
- Security headers: CSP, X-Frame-Options, XSS Protection
- Cron endpoint secured with secret token

---

## 📞 Support

For issues or feature requests, open an issue on GitHub.

**Mini NOC v1.0.0** - Enterprise Network Monitoring
