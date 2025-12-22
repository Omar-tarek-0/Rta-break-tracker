# 🔧 RTA Break Tracker - Technical Guide

## For Developers and System Administrators

---

## 📐 Architecture Overview

### Application Flow

```
User Request
    ↓
Flask App (app.py)
    ↓
Authentication Check (Flask-Login)
    ↓
Route Handler
    ↓
Database Query (SQLAlchemy)
    ↓
Template Rendering / JSON Response
    ↓
Client (Browser)
```

### Request Lifecycle

1. **User accesses URL** → Flask receives request
2. **Authentication check** → `@login_required` decorator
3. **Route handler** → Processes request
4. **Database operations** → SQLAlchemy queries
5. **Response** → HTML template or JSON API response

---

## 🗄️ Database Models

### User Model

```python
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='agent')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    breaks = db.relationship('BreakRecord', backref='agent', lazy=True)
```

**Relationships:**
- One-to-Many with `BreakRecord` (agent → breaks)
- One-to-Many with `Shift` (agent → shifts)

**Methods:**
- `is_rtm()` - Check if user is RTM
- `is_agent()` - Check if user is agent
- `set_password(password)` - Hash and store password
- `check_password(password)` - Verify password

### BreakRecord Model

```python
class BreakRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    break_type = db.Column(db.String(50), nullable=False)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    start_screenshot = db.Column(db.String(255))
    end_screenshot = db.Column(db.String(255))
    duration_minutes = db.Column(db.Integer)
    is_overdue = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

**Key Methods:**
- `is_active()` - Check if break is ongoing
- `get_elapsed_minutes()` - Calculate elapsed time
- `get_allowed_duration()` - Get allowed duration from config
- `get_break_info()` - Get break type info (name, emoji, color)
- `to_dict()` - Serialize to dictionary

### Shift Model

```python
class Shift(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    shift_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
```

**Methods:**
- `get_duration_hours()` - Calculate shift duration
- `to_dict()` - Serialize to dictionary

---

## 🔐 Authentication System

### Login Flow

1. User submits credentials → `POST /login`
2. Find user by username
3. Verify password with `bcrypt.checkpw()`
4. Create session with `login_user(user)`
5. Redirect to appropriate dashboard

### Session Management

- Uses Flask-Login for session handling
- Sessions stored in encrypted cookies
- `@login_required` decorator protects routes
- Automatic redirect to login if not authenticated

### Password Security

- Passwords hashed with `bcrypt`
- Salt automatically generated
- Never stored in plain text
- Default password for restored users: `changeme123`

---

## 📊 Metrics Calculation Details

### Utilization Calculation

```python
def calculate_utilization(scheduled_hours, break_minutes):
    if scheduled_hours == 0:
        return 0
    worked_minutes = (scheduled_hours * 60) - break_minutes
    return (worked_minutes / (scheduled_hours * 60)) * 100
```

**Formula:**
```
Utilization = (Scheduled Time - Break Time) / Scheduled Time × 100
```

### Adherence Calculation

**Per Break:**
```python
adherence_score = (allowed_duration - actual_duration) / allowed_duration
if adherence_score < 0:
    adherence_score = 0  # Can't exceed 100%
```

**Punch In/Out Adherence:**
```python
# Compare punch time to shift start/end
punch_in_diff = abs((punch_in_time - shift_start_time).total_seconds() / 60)
punch_out_diff = abs((punch_out_time - shift_end_time).total_seconds() / 60)

# Allow 5-minute grace period
if punch_in_diff <= 5:
    punch_in_score = 1.0
else:
    punch_in_score = max(0, 1 - (punch_in_diff - 5) / 15)
```

**Final Adherence:**
- Average of all break adherence scores
- Includes punch in/out scores
- Weighted average

### Conformance Calculation

```python
conformance = (total_breaks - exceeding_breaks - incidents) / total_breaks * 100
```

**Components:**
- `total_breaks` - All breaks (excluding punch in/out)
- `exceeding_breaks` - Breaks that exceeded allowed duration
- `incidents` - Overdue breaks + emergency breaks beyond limit

### Exceeding Breaks

A break is "exceeding" if:
- `actual_duration > allowed_duration`
- Not including punch in/out

### Incidents

Counted as incidents:
- Breaks marked as `is_overdue = True`
- Emergency breaks beyond daily limit (if applicable)

---

## 🖼️ Screenshot Handling

### Upload Process

1. **Client uploads file** → `POST /api/break/start` or `/api/break/end`
2. **File validation** → Check extension, size
3. **Save to disk** → `uploads/{date}/{uuid}.jpg`
4. **Optimize image** → Resize if needed, convert to JPEG
5. **Store path in database** → Save relative path

### File Storage Structure

```
uploads/
├── 2025-12-15/
│   ├── abc123def456.jpg
│   └── xyz789ghi012.jpg
├── 2025-12-16/
│   └── ...
```

### Image Processing

- **Format**: Converted to JPEG
- **Max Size**: 16MB upload limit
- **Optimization**: Resized if too large
- **Naming**: UUID-based for uniqueness

---

## 🔄 API Endpoints Reference

### Authentication

#### `POST /login`
**Request:**
```json
{
  "username": "agent1",
  "password": "password123"
}
```

**Response:**
- Success: Redirect to dashboard
- Error: Flash message, redirect to login

#### `GET /logout`
- Logs out user
- Clears session
- Redirects to login

---

### Agent Endpoints

#### `GET /agent`
- Renders agent dashboard
- Requires: Agent role
- Returns: HTML template

#### `POST /api/break/start`
**Request:**
- `screenshot` (file)
- `break_type` (string)

**Response:**
```json
{
  "success": true,
  "message": "Break started successfully",
  "break": { ... }
}
```

**Logic:**
- Validates punch in status (must be punched in)
- Saves screenshot
- Creates BreakRecord
- Auto-completes punch in/out (single screenshot)

#### `POST /api/break/end`
**Request:**
- `screenshot` (file)

**Response:**
```json
{
  "success": true,
  "message": "Break ended successfully"
}
```

**Logic:**
- Finds active break
- Saves end screenshot
- Calculates duration
- Marks as overdue if exceeded

---

### RTM Endpoints

#### `GET /dashboard`
- Renders RTM dashboard
- Requires: RTM role
- Returns: HTML template with stats

#### `GET /api/breaks`
**Query Parameters:**
- `start_date` (YYYY-MM-DD)
- `end_date` (YYYY-MM-DD)
- `agent_id` (optional)

**Response:**
```json
{
  "breaks": [
    {
      "id": 1,
      "agent_name": "John Doe",
      "break_type": "short",
      "start_time": "2025-12-15T10:00:00",
      ...
    }
  ]
}
```

#### `POST /api/break/<id>/notes`
**Request:**
```json
{
  "notes": "Agent was late returning"
}
```

**Response:**
```json
{
  "success": true
}
```

---

### Shift Management

#### `GET /api/shifts`
**Query Parameters:**
- `agent_id` (optional)
- `start_date` (optional)
- `end_date` (optional)

**Response:**
```json
{
  "shifts": [
    {
      "id": 1,
      "agent_id": 2,
      "shift_date": "2025-12-15",
      "start_time": "08:00:00",
      "end_time": "17:00:00"
    }
  ]
}
```

#### `POST /api/shift/create`
**Request:**
```json
{
  "agent_id": 2,
  "shift_date": "2025-12-15",
  "start_time": "08:00:00",
  "end_time": "17:00:00"
}
```

#### `POST /api/shift/bulk`
**Request:**
```json
{
  "agent_ids": [2, 3, 4],
  "start_date": "2025-12-15",
  "end_date": "2025-12-29",
  "start_time": "08:00:00",
  "end_time": "17:00:00"
}
```

---

### Reports

#### `GET /api/report/metrics`
**Query Parameters:**
- `start_date` (required)
- `end_date` (required)

**Response:**
```json
{
  "summary": {
    "avg_utilization": 85.5,
    "avg_adherence": 92.3,
    "avg_conformance": 88.7,
    "total_incidents": 5,
    "total_exceeding": 12,
    "total_emergency": 3,
    "total_lunch": 45,
    "total_coaching": 8
  },
  "agents": [
    {
      "agent_id": 2,
      "agent_name": "John Doe",
      "scheduled_hours": 40,
      "total_breaks": 8,
      "break_minutes": 120,
      "exceeding_minutes": 15,
      "incidents": 1,
      "emergency_count": 0,
      "lunch_count": 5,
      "coaching_count": 1,
      "utilization": 87.5,
      "adherence": 90.2,
      "conformance": 87.5
    }
  ]
}
```

#### `GET /api/report/export`
**Query Parameters:**
- `start_date` (required)
- `end_date` (required)

**Response:**
- Excel file download
- Content-Type: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

---

### Backup & Restore

#### `GET /api/backup/export`
**Response:**
- JSON file download
- Contains all users, breaks, shifts

**Backup Format:**
```json
{
  "version": "1.0",
  "exported_at": "2025-12-15T10:00:00",
  "exported_by": "RTM Admin",
  "data": {
    "users": [...],
    "breaks": [...],
    "shifts": [...]
  }
}
```

#### `POST /api/backup/import`
**Request:**
- `file` (multipart/form-data, JSON file)

**Response:**
```json
{
  "success": true,
  "message": "Backup restored: 20 users, 150 breaks, 40 shifts"
}
```

**Logic:**
- Parses JSON backup file
- Skips existing users (by username)
- Restores breaks and shifts
- Sets default password for restored users

---

## 🎨 Frontend Architecture

### JavaScript Structure

**Agent View (`app.js`):**
- `initAgentView()` - Initialize agent interface
- `handleFileSelect()` - Process uploaded file
- `startBreak()` - Submit break start
- `endBreak()` - Submit break end
- `updateElapsedTime()` - Update break timer
- `updateSubmitButton()` - Dynamic button text

**Dashboard View:**
- `initDashboard()` - Initialize dashboard
- `loadBreaks()` - Fetch and display breaks
- `switchTab()` - Tab navigation
- `loadShifts()` - Load shift management
- `loadMetrics()` - Generate reports
- `exportToExcel()` - Trigger Excel download
- `exportBackup()` - Export data backup
- `importBackup()` - Restore from backup

### CSS Architecture

**Theme Variables:**
```css
:root {
  --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  --background: #f5f7fa;
  --surface: #ffffff;
  --text: #1a1a2e;
  --success: #10b981;
  --warning: #f59e0b;
  --danger: #ef4444;
}
```

**Component Classes:**
- `.btn` - Button styles
- `.panel` - Content panels
- `.break-type-btn` - Break selection buttons
- `.history-card` - Break history items
- `.metrics-table` - Reports table
- `.backup-card` - Backup section cards

---

## 🔒 Security Considerations

### Password Security
- ✅ Bcrypt hashing with salt
- ✅ Never stored in plain text
- ✅ Not included in backups

### Authentication
- ✅ Session-based with Flask-Login
- ✅ Role-based access control
- ✅ Protected routes with `@login_required`

### File Upload Security
- ✅ File type validation
- ✅ File size limits (16MB)
- ✅ Secure filename handling
- ✅ UUID-based naming

### SQL Injection Prevention
- ✅ SQLAlchemy ORM (parameterized queries)
- ✅ No raw SQL queries

### XSS Prevention
- ✅ Jinja2 auto-escaping
- ✅ Input validation

---

## 🧪 Testing Recommendations

### Manual Testing Checklist

**Agent Functions:**
- [ ] Login as agent
- [ ] Punch in
- [ ] Take break (all types)
- [ ] End break
- [ ] View schedule
- [ ] View break history
- [ ] Punch out

**RTM Functions:**
- [ ] Login as RTM
- [ ] View all breaks
- [ ] Add notes
- [ ] Add new agent
- [ ] Assign shifts
- [ ] Generate reports
- [ ] Export Excel
- [ ] Export backup
- [ ] Import backup

### Database Testing

```python
# Example test queries
from app import db, User, BreakRecord

# Get all agents
agents = User.query.filter_by(role='agent').all()

# Get today's breaks
today = datetime.now().date()
breaks = BreakRecord.query.filter(
    db.func.date(BreakRecord.start_time) == today
).all()

# Get overdue breaks
overdue = BreakRecord.query.filter_by(is_overdue=True).all()
```

---

## 📈 Performance Optimization

### Database Indexing

Recommended indexes:
```sql
CREATE INDEX idx_break_agent_date ON break_records(agent_id, start_time);
CREATE INDEX idx_shift_agent_date ON shifts(agent_id, shift_date);
CREATE INDEX idx_user_username ON users(username);
```

### Query Optimization

- Use `filter()` instead of loading all records
- Limit results with `.limit()`
- Use joins efficiently
- Cache frequently accessed data

### Image Optimization

- Convert to JPEG (smaller than PNG)
- Resize large images
- Store in date-based folders
- Consider CDN for production

---

## 🐛 Debugging

### Enable Debug Mode

**Development:**
```python
# config.py
DEBUG = True
FLASK_ENV = 'development'
```

**Logging:**
```python
import logging
app.logger.setLevel(logging.DEBUG)
```

### Common Debug Points

1. **Check database connection**
   ```python
   from app import db
   db.session.execute('SELECT 1')
   ```

2. **Check user authentication**
   ```python
   from flask_login import current_user
   print(current_user.is_authenticated)
   ```

3. **Check file uploads**
   ```python
   print(request.files)
   print(request.form)
   ```

---

## 📚 Additional Resources

- **Flask Documentation**: https://flask.palletsprojects.com/
- **SQLAlchemy Documentation**: https://docs.sqlalchemy.org/
- **Flask-Login Documentation**: https://flask-login.readthedocs.io/
- **PostgreSQL Documentation**: https://www.postgresql.org/docs/

---

**Last Updated:** December 2024

