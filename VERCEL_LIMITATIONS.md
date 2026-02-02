# Vercel Deployment Limitations & Future Roadmap

> **Deployment Mode**: Vercel Serverless (Free Tier)
> **Status**: Pure Cloud Deployment

This document tracks features that are **disabled or limited** because we are deploying to Vercel's Serverless environment instead of a traditional VPS/Server.

Vercel functions are ephemeral (they die after ~10 seconds) and read-only.

## 🚫 Disabled Features (By Design)

### 1. Active Network Scanning (`nmap`, `ping`)
-   **Limitation**: Vercel does not allow "Raw Socket" access required for ICMP pings.
-   **Impact**: The "Scan Network" button will not be able to physically ping devices from the cloud server.
-   **Future Fix**: Deploy a "Remote Agent" (Python script) on a local Raspberry Pi/PC that talks to this Vercel API.

### 2. Background Workers (Celery/Redis)
-   **Limitation**: Vercel does not support persistent processes.
-   **Impact**: We cannot run the `celery_app` or `start_worker.bat`. Long-running tasks must be handled differently (e.g., GitHub Actions, Cron Jobs, or external trigger).
-   **Workaround**: API endpoints will need to be synchronous or delegate to an external service.

### 3. Local SQLite Database
-   **Limitation**: The filesystem on Vercel is read-only (except `/tmp`) and impermanent.
-   **Impact**: `sql_app.db` will be wiped on every deployment.
-   **Required Change**: Must connect to a Cloud Database (Neon, Supabase, or AWS RDS) using `DATABASE_URL`.

### 4. Local File Logging
-   **Limitation**: Cannot write to `debug.log`.
-   **Impact**: Logs must be sent to `stdout` (Vercel Logs) or a service like papertrail.

---

## 🔮 Future "Pro" Features (To Re-Enable)
When moving to a **VPS (DigitalOcean/Render/AWS)**, we can re-enable:

-   [ ] **Real-time Monitoring**: reactivating the `monitoring_orchestrator` loop.
-   [ ] **Auto-Discovery**: Enabling the `nmap`/`ping` sweep.
-   [ ] **Persistent Async Tasks**: Re-enabling the Redis/Celery Architecture.
