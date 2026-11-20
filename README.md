# BuildSmart 360 — Standalone Render Deployment Application

A standalone deployment manager application designed to guide and automate the end-to-end deployment of **BuildSmart 360** to **Render**.

---

## Features

- **Step 1: Pre-Flight Verification**: Validates your Google Sheets connection, OAuth tokens, Brevo transactional email delivery, and runs the 20 isolated test cases.
- **Step 2: Git Repository & Sensitive Data Check**: Verifies that your code is committed on branch `main` and that secrets (`.env`, `data/`) are properly ignored.
- **Step 3: GitHub Remote Sync & Approval**: Inspect the latest commits from your GitHub repository and approve a commit for deployment.
- **Step 4: Render Deployment**:
  - **Automated Mode**: Connect your Render API Key, select your workspace, and deploy in 1-click. All 15 environment variables are auto-injected.
  - **Manual Mode**: One-click copy for all Render environment variables with pre-filled build and start commands.
- **Step 5: Google Cloud OAuth Registration & Health Check**: Computes the exact redirect URI and verifies live deployment health.

---

## Quick Start (Local)

### 1. Launch the Deployment Application
Double-click `Start-Deployment-App.cmd`, or run:
```powershell
python run_deployer.py
```

### 2. Follow the 5 Linear Steps
The application will automatically open in your default browser at:
`http://127.0.0.1:5500`

---

## Deploying the Deployment Application to Render

This deployment tool can run as its own hosted cloud web service on Render:

- **Repository**: `https://github.com/vtabsquare/Buildsmart-deployment-.git`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn deployer.app:app`
- **Environment**: Python 3.11+
- **Free Tier Compatible**: Yes, runs on Render Free tier
