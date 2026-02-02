# Mini NOC - Network Operations Center

**Mini NOC** is an enterprise-grade Network Monitoring System (NMS) designed to provide real-time visibility into network infrastructure. It combines a high-performance Python backend with a modern React dashboard to track device health, manage incidents, and visualize network performance.

![Dashboard Preview](https://via.placeholder.com/800x400?text=Mini+NOC+Dashboard)

## ✨ Features

### 🔍 Enhanced Discovery & Monitoring
- **Subnet Scanning:** Automatically discover devices (IP, MAC, Vendor, OS, Open Ports).
- **Real-Time Health Checks:** ICMP ping monitoring (Latency, Packet Loss, Status).
- **SNMP Polling:** Retrieve CPU, Memory, and Interface stats from network devices.
- **Service Detection:** Banner grabbing to identify running services.

### 🚨 Incident Management
- **Incident Tracking:** Create incidents, assign severity levels (P1-P4), and track resolution.
- **Automated Alerts:** System generates alerts for device failures or threshold breaches.
- **Timeline View:** Audit trail of all actions and status changes.

### 🛠️ Enterprise Control
- **Wake-on-LAN (WoL):** Wake up remote devices directly from the dashboard.
- **SSH Testing:** Verify SSH connectivity to remote hosts.
- **Enrichment:** On-demand deep scanning of specific devices.

### 📊 Analytics & Reporting
- **SLA Dashboard:** Track specific uptime commitments and MTTR/MTBF.
- **Visualizations:** Interactive charts for latency, loss, and CPU usage.
- **Export:** Download reports as CSV or PDF.

### 🎨 Modern UI/UX
- **Dark Mode:** Fully supported dark/light themes.
- **Responsive:** Optimized for desktop and tablet screens.
- **Sound Alerts:** Audible notifications for critical events.

---

## 💻 Software Requirements

To run this project locally, you need:

- **Python 3.10+** (for the backend API)
- **Node.js 18+** (for the frontend dashboard)
- **Git** (for version control)

---

## 🚀 How to Run Locally

Follow these steps to set up the project on your machine.

### 1. Backend Setup

Open a terminal and navigate to the `backend` folder:

```bash
cd backend

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the API server
python main.py
```

The backend API will start at `http://localhost:8000`.

### 2. Frontend Setup

Open a **new terminal** and navigate to the `frontend` folder:

```bash
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

The dashboard will be available at `http://localhost:5173`.

---

## 📦 Distribution / Sharing

If you want to share this project with others:

1.  **Cleanup:** Delete the `node_modules` (frontend), `venv` (backend), and `__pycache__` folders to reduce size.
2.  **Zip:** Compress the `mini-noc` folder.
3.  **Run:** The recipient just needs to follow the **Backend Setup** and **Frontend Setup** steps above.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Copyright (c) 2026 **Vaishnavi Kushwaha**
