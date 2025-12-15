# 🚀 RTA Break Tracker - Deployment Guide

## Option 1: Railway.app (Recommended - Easiest)

Railway offers free tier and easy deployment.

### Steps:

1. **Create GitHub Repository**
   ```bash
   cd "D:\RTA screenshot\web"
   git init
   git add .
   git commit -m "Initial commit"
   ```

2. **Push to GitHub**
   - Create a new repository on https://github.com/new
   - Follow GitHub instructions to push your code

3. **Deploy on Railway**
   - Go to https://railway.app
   - Sign up with GitHub
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository
   - Railway will auto-detect Python and deploy!

4. **Add PostgreSQL Database**
   - In Railway dashboard, click "+ New" → "Database" → "PostgreSQL"
   - Railway automatically sets `DATABASE_URL`

5. **Set Environment Variables**
   - Go to your app → Variables tab
   - Add:
     - `SECRET_KEY` = (generate random string)
     - `FLASK_ENV` = production
     - `ADMIN_PASSWORD` = your-secure-password

6. **Get Your URL**
   - Railway gives you a URL like: `https://rta-tracker-xxx.up.railway.app`
   - Share this with your agents!

---

## Option 2: Render.com (Free Tier Available)

### Steps:

1. Push code to GitHub (same as above)

2. **Deploy on Render**
   - Go to https://render.com
   - Sign up with GitHub
   - Click "New" → "Web Service"
   - Connect your repository
   - Settings:
     - Environment: Python
     - Build Command: `pip install -r requirements.txt`
     - Start Command: `gunicorn app:app`

3. **Add PostgreSQL**
   - Create new PostgreSQL database on Render
   - Copy the Internal Database URL
   - Add as `DATABASE_URL` environment variable

4. **Environment Variables**
   - Add `SECRET_KEY`, `FLASK_ENV=production`

---

## Option 3: PythonAnywhere (Simple & Reliable)

### Steps:

1. Go to https://www.pythonanywhere.com
2. Sign up (free tier available)
3. Go to "Web" tab → "Add a new web app"
4. Choose Flask and Python 3.11
5. Upload your files via "Files" tab
6. Set up virtualenv and install requirements
7. Configure WSGI file to point to your app

---

## Option 4: Your Own Server (VPS)

If you have a Windows/Linux server:

### On Ubuntu/Debian:

```bash
# Install Python
sudo apt update
sudo apt install python3 python3-pip python3-venv nginx

# Clone your app
git clone https://github.com/YOUR_USERNAME/rta-tracker.git
cd rta-tracker

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run with gunicorn
gunicorn app:app --bind 0.0.0.0:5000 --daemon

# Or use systemd service for auto-start
```

---

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Random secret for sessions | `abc123xyz789...` |
| `FLASK_ENV` | Environment mode | `production` |
| `DATABASE_URL` | PostgreSQL connection | `postgresql://user:pass@host/db` |
| `ADMIN_USERNAME` | Admin login username | `admin` |
| `ADMIN_PASSWORD` | Admin login password | `SecurePass123!` |
| `PORT` | Server port (auto-set by host) | `5000` |

---

## After Deployment

1. ✅ Access your app URL
2. ✅ Login with admin credentials
3. ✅ Change admin password (via database or add password change feature)
4. ✅ Add your agents using the "Add Agent" button
5. ✅ Share the URL with your 20 agents!

---

## Quick Deploy Commands (Railway)

```bash
# One-time setup
cd "D:\RTA screenshot\web"
git init
git add .
git commit -m "RTA Break Tracker"

# Install Railway CLI (optional)
npm install -g @railway/cli
railway login
railway init
railway up
```

Your app will be live at a URL like: `https://your-app.up.railway.app` 🎉

