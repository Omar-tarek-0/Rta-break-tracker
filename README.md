# 🖥️ RTA Break Tracker - Complete Documentation

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Features](#features)
3. [System Architecture](#system-architecture)
4. [Installation & Setup](#installation--setup)
5. [User Guide](#user-guide)
6. [Technical Documentation](#technical-documentation)
7. [Deployment](#deployment)
8. [Configuration](#configuration)
9. [Troubleshooting](#troubleshooting)

---

## 🎯 Project Overview

**RTA Break Tracker** is a web-based application designed for Real-Time Management (RTM) of call center agents. It enables agents to submit break requests with screenshots for validation, and allows RTM administrators to monitor, validate, and generate reports on agent break activities.

### Purpose
- **For Agents**: Easy break submission with screenshot validation
- **For RTM**: Centralized monitoring, validation, and reporting of agent breaks
- **For Management**: Comprehensive metrics and Excel exports for analysis

### Key Benefits
- ✅ Real-time break tracking and validation
- ✅ Screenshot-based verification system
- ✅ Automated metrics calculation (Utilization, Adherence, Conformance)
- ✅ Shift management for 2-week schedules
- ✅ Comprehensive reporting with Excel export
- ✅ Cloud-based, accessible from anywhere
- ✅ Data backup and restore functionality

---

## ✨ Features

### 👤 Agent Features

1. **Break Management**
   - Multiple break types: Short Break, Lunch, Meeting, Huddle, Emergency, Coaching, Overtime, Compensation, etc.
   - Punch In/Out system for daily attendance
   - Screenshot upload (browse or paste from clipboard)
   - Real-time break status display
   - Break history for current day

2. **Shift Schedule**
   - View assigned shifts for next 2 weeks
   - Clear display of shift times
   - Today's shift highlighted

3. **Status Indicators**
   - Current break status with elapsed time
   - Overdue break warnings
   - Punch status (Not Punched, Punched In, Punched Out)

### 👨‍💼 RTM Features

1. **Break Monitoring**
   - Real-time view of all agent breaks
   - Grouped by agent for easy viewing
   - Date range filtering
   - Search functionality
   - Screenshot viewing
   - Notes and comments

2. **Shift Management**
   - Assign shifts to agents for 2-week periods
   - Quick templates (8-5, 11-8, 1-10, 4-1 AM, 12M-9 AM)
   - Bulk assignment for multiple agents
   - Individual shift editing

3. **Reports & Analytics**
   - **Metrics Calculated:**
     - Utilization %
     - Adherence %
     - Conformance %
     - Exceeding Breaks
     - Incidents Count
     - Emergency Breaks
     - Lunch Breaks
     - Coaching Breaks
   - Date range selection
   - Summary cards with averages
   - Detailed agent metrics table
   - Excel export functionality

4. **Data Management**
   - Export all data as JSON backup
   - Restore from backup file
   - Safe update procedures

5. **User Management**
   - Add new agents
   - View all agents
   - Agent statistics

---

## 🏗️ System Architecture

### Technology Stack

**Backend:**
- **Flask** - Python web framework
- **Flask-SQLAlchemy** - ORM for database operations
- **Flask-Login** - User authentication and session management
- **PostgreSQL** (Production) / **SQLite** (Development) - Database
- **bcrypt** - Password hashing
- **Pillow** - Image processing
- **openpyxl** - Excel file generation
- **pytz** - Timezone handling

**Frontend:**
- **HTML5** - Structure
- **CSS3** - Styling (with purple gradient theme)
- **JavaScript (Vanilla)** - Interactivity and API calls

**Deployment:**
- **Gunicorn** - WSGI HTTP server
- **Railway.app** / **Render.com** - Cloud hosting
- **PostgreSQL** - Production database

### Application Structure

```
web/
├── app.py                 # Main Flask application
├── config.py             # Configuration settings
├── requirements.txt       # Python dependencies
├── Procfile              # Railway deployment config
├── templates/            # HTML templates
│   ├── base.html
│   ├── login.html
│   ├── agent.html
│   └── dashboard.html
├── static/
│   ├── css/
│   │   └── style.css     # Styling
│   └── js/
│       └── app.js        # Frontend JavaScript
└── uploads/              # Screenshot storage
```

### Database Schema

**Users Table:**
- `id` - Primary key
- `username` - Unique username
- `password_hash` - Hashed password
- `full_name` - Display name
- `role` - 'agent' or 'rtm'
- `created_at` - Account creation timestamp

**Break Records Table:**
- `id` - Primary key
- `agent_id` - Foreign key to Users
- `break_type` - Type of break (short, lunch, etc.)
- `start_time` - Break start timestamp
- `end_time` - Break end timestamp
- `start_screenshot` - Path to start screenshot
- `end_screenshot` - Path to end screenshot
- `duration_minutes` - Calculated duration
- `is_overdue` - Boolean flag
- `notes` - RTM comments
- `created_at` - Record creation timestamp

**Shifts Table:**
- `id` - Primary key
- `agent_id` - Foreign key to Users
- `shift_date` - Date of shift
- `start_time` - Shift start time
- `end_time` - Shift end time
- `created_by` - RTM user who created it
- `created_at` - Creation timestamp

---

## 🚀 Installation & Setup

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- PostgreSQL (for production) or SQLite (for development)
- Git (for version control)

### Local Development Setup

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd "RTA screenshot/web"
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Linux/Mac:
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment**
   - Create `.env` file (optional):
     ```
     FLASK_ENV=development
     SECRET_KEY=your-secret-key-here
     TIMEZONE=Africa/Cairo
     ```

5. **Initialize Database**
   - The database will be created automatically on first run
   - Default admin account: `admin` / `admin123`

6. **Run the Application**
   ```bash
   python app.py
   ```
   - Open browser: `http://localhost:5000`

### Production Deployment

See [DEPLOY.md](DEPLOY.md) for detailed deployment instructions.

**Quick Deploy to Railway:**
1. Push code to GitHub
2. Connect Railway to GitHub repo
3. Add PostgreSQL database
4. Set environment variables
5. Deploy!

---

## 📖 User Guide

### For Agents

#### First Time Login
1. Go to the application URL
2. Enter your username and password (provided by RTM)
3. Click "Login"

#### Taking a Break

1. **Select Break Type**
   - Click on the break type button (e.g., "☕ Short Break")
   - Available types: Short Break, Lunch, Meeting, Huddle, Emergency, Coaching, etc.

2. **Upload Screenshot**
   - **Option 1**: Click "📁 Browse" and select image file
   - **Option 2**: Press "📋 Paste" and paste from clipboard (Ctrl+V)
   - Supported formats: PNG, JPG, JPEG, GIF, BMP

3. **Submit Break Start**
   - Button text changes based on break type (e.g., "Submit Short Break")
   - Click the submit button
   - Wait for confirmation

4. **End Break**
   - When returning, select the same break type
   - Upload end screenshot
   - Click "Submit Break End"

#### Punch In/Out

1. **Punch In** (Start of day)
   - Select "🟢 Punch In"
   - Upload one screenshot
   - Click "Submit Punch In"
   - Status changes to "Punched In"

2. **Punch Out** (End of day)
   - Select "🔴 Punch Out"
   - Upload one screenshot
   - Click "Submit Punch Out"
   - Status changes to "Punched Out"
   - No more breaks can be taken after punch out

#### Viewing Schedule

- Your assigned shifts for the next 2 weeks are displayed in the right panel
- Today's shift is highlighted
- Shows shift times (e.g., "08:00 AM - 05:00 PM")

#### Break Status

- **Status Box** shows:
  - Current break name and elapsed time
  - Start time and allowed duration
  - Overdue warning (red border) if exceeded

### For RTM Administrators

#### Dashboard Overview

1. **Break Records Tab**
   - View all agent breaks grouped by agent
   - Filter by date range
   - Search by agent name
   - Click screenshots to view full size
   - Add notes/comments to breaks

2. **Shift Management Tab**
   - Assign shifts to agents
   - Use quick templates or custom times
   - Set shifts for 2-week periods
   - Bulk assign to multiple agents

3. **Reports & Export Tab**
   - Select date range
   - Generate metrics report
   - View summary cards and detailed table
   - Export to Excel

4. **Data Backup Tab**
   - Export all data as JSON
   - Restore from backup file
   - Safe update procedures

#### Adding New Agents

1. Click "➕ Add Agent" button
2. Enter:
   - Full Name
   - Username (must be unique)
   - Password
3. Click "✅ Add Agent"
4. Agent can now login with these credentials

#### Managing Shifts

1. Click "🕐 Shift Management" button
2. Select date range (up to 2 weeks)
3. Choose agents (checkboxes)
4. Set start and end times
   - Or use quick templates
5. Click "💾 Save Shifts"
6. Agents will see their schedules

#### Generating Reports

1. Go to "📊 Reports & Export" tab
2. Select date range
3. Click "📊 Generate Report"
4. Review metrics:
   - Summary cards (averages)
   - Detailed agent table
5. Click "📥 Export to Excel" to download

#### Adding Notes to Breaks

1. Find the break in the Break Records tab
2. Click "📝 Add Note" button
3. Enter comment
4. Click "Save"
5. Note appears on the break card

---

## 🔧 Technical Documentation

### API Endpoints

#### Authentication
- `POST /login` - User login
- `GET /logout` - User logout

#### Agent Endpoints
- `GET /agent` - Agent dashboard view
- `POST /api/break/start` - Start a break
- `POST /api/break/end` - End a break
- `GET /api/breaks` - Get agent's breaks

#### RTM Endpoints
- `GET /dashboard` - RTM dashboard view
- `GET /api/breaks` - Get all breaks (with filters)
- `POST /api/break/<id>/notes` - Add notes to break
- `GET /api/agents` - Get all agents
- `POST /api/agents` - Create new agent

#### Shift Management
- `GET /api/shifts` - Get shifts
- `POST /api/shift/create` - Create shift
- `PUT /api/shift/<id>` - Update shift
- `DELETE /api/shift/<id>` - Delete shift
- `POST /api/shift/bulk` - Bulk create shifts

#### Reports
- `GET /api/report/metrics` - Get metrics for date range
- `GET /api/report/export` - Export Excel report

#### Backup
- `GET /api/backup/export` - Export all data as JSON
- `POST /api/backup/import` - Import data from JSON

### Break Types Configuration

Break types are defined in `config.py`:

```python
BREAK_DURATIONS = {
    "short": 15,              # 15 minutes
    "lunch": 30,              # 30 minutes
    "meeting": 60,             # 60 minutes
    "huddle": 15,              # 15 minutes
    "emergency": 15,           # 15 minutes
    "coaching_aya": 30,       # 30 minutes
    "coaching_mostafa": 30,   # 30 minutes
    "punch_in": 0,            # Instant (single screenshot)
    "punch_out": 0,           # Instant (single screenshot)
    "overtime": 0,
    "compensation": 0,
    "meeting_team_leader": 60  # 60 minutes
}
```

### Metrics Calculation

**Utilization:**
```
Utilization = (Scheduled Hours - Break Time) / Scheduled Hours × 100
```

**Adherence:**
- Calculated per break: `(Allowed Duration - Actual Duration) / Allowed Duration × 100`
- Includes punch in/out timing vs. shift times
- Average of all adherence scores

**Conformance:**
```
Conformance = (Total Breaks - Exceeding Breaks - Incidents) / Total Breaks × 100
```

**Exceeding Breaks:**
- Breaks that exceeded their allowed duration

**Incidents:**
- Breaks marked as overdue
- Emergency breaks beyond limit

### Timezone Handling

- All times stored in configured timezone (default: Africa/Cairo)
- Set via `TIMEZONE` environment variable
- Consistent across all operations

---

## 🌐 Deployment

### Railway.app (Recommended)

1. **Create GitHub Repository**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin <your-repo-url>
   git push -u origin main
   ```

2. **Deploy on Railway**
   - Go to https://railway.app
   - Sign up with GitHub
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository
   - Railway auto-detects Python

3. **Add PostgreSQL Database**
   - Click "+ New" → "Database" → "PostgreSQL"
   - Railway sets `DATABASE_URL` automatically

4. **Set Environment Variables**
   - Go to Variables tab
   - Add:
     - `SECRET_KEY` = (generate random string)
     - `FLASK_ENV` = production
     - `ADMIN_PASSWORD` = your-secure-password
     - `TIMEZONE` = Africa/Cairo (or your timezone)

5. **Get Your URL**
   - Railway provides URL like: `https://your-app.up.railway.app`

### Render.com

Similar process:
1. Connect GitHub repo
2. Create PostgreSQL database
3. Set environment variables
4. Deploy

See [DEPLOY.md](DEPLOY.md) for detailed instructions.

---

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_ENV` | Environment (development/production) | development |
| `SECRET_KEY` | Flask secret key | (dev key) |
| `DATABASE_URL` | PostgreSQL connection string | (SQLite local) |
| `TIMEZONE` | Timezone (e.g., Africa/Cairo) | Africa/Cairo |
| `ADMIN_USERNAME` | Default admin username | admin |
| `ADMIN_PASSWORD` | Default admin password | admin123 |
| `UPLOAD_FOLDER` | Screenshot storage path | ./uploads |

### Timezone Options

Common timezones:
- Egypt: `Africa/Cairo`
- Saudi Arabia: `Asia/Riyadh`
- UAE: `Asia/Dubai`
- India: `Asia/Kolkata`
- UK: `Europe/London`
- US Eastern: `America/New_York`

### Break Duration Customization

Edit `config.py` to modify break durations:

```python
BREAK_DURATIONS = {
    "short": 15,  # Change to desired minutes
    "lunch": 30,
    # ... etc
}
```

---

## 🔍 Troubleshooting

### Common Issues

**1. Login Not Working**
- Check username/password
- Verify user exists in database
- Check browser console for errors

**2. Screenshots Not Uploading**
- Check file size (max 16MB)
- Verify file format (PNG, JPG, etc.)
- Check upload folder permissions

**3. Times Displaying Incorrectly**
- Verify `TIMEZONE` environment variable
- Check timezone in `config.py`
- Clear browser cache

**4. Database Connection Errors**
- Verify `DATABASE_URL` is set correctly
- Check PostgreSQL is running
- Verify connection string format

**5. Deployment Issues**
- Check Railway/Render logs
- Verify environment variables
- Check `requirements.txt` is complete
- Verify `Procfile` exists

### Getting Help

1. Check application logs
2. Review browser console (F12)
3. Check server logs (Railway/Render dashboard)
4. Verify configuration settings
5. Review [SAFE_UPDATES.md](SAFE_UPDATES.md) for data backup procedures

---

## 📝 Additional Documentation

- **[DEPLOY.md](DEPLOY.md)** - Detailed deployment guide
- **[SAFE_UPDATES.md](SAFE_UPDATES.md)** - Safe update procedures and data backup

---

## 📄 License

This project is proprietary software for internal use.

---

## 👥 Support

For issues or questions:
1. Check this documentation
2. Review troubleshooting section
3. Check application logs
4. Contact system administrator

---

**Last Updated:** December 2024
**Version:** 1.0

