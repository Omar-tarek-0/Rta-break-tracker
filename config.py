"""
RTA Break Tracker Web - Configuration
Supports both development and production environments
"""
import os
from pathlib import Path
import pytz

# Base directory
BASE_DIR = Path(__file__).parent

# Environment
ENV = os.environ.get('FLASK_ENV', 'development')
DEBUG = ENV == 'development'

# Timezone Configuration (Change this to your timezone!)
# Egypt: 'Africa/Cairo'
# Saudi Arabia: 'Asia/Riyadh'
# UAE: 'Asia/Dubai'
TIMEZONE = pytz.timezone(os.environ.get('TIMEZONE', 'Africa/Cairo'))

# Secret key (CHANGE IN PRODUCTION via environment variable!)
SECRET_KEY = os.environ.get('SECRET_KEY', 'rta-break-tracker-dev-key-change-in-production')

# Database Configuration
# Use PostgreSQL in production, SQLite in development
# Prefer private endpoint to avoid egress fees on Railway

def get_database_uri():
    """Get database URI, preferring private endpoint to avoid egress fees"""
    # Option 1: Explicit private URL (best - no fees)
    private_url = os.environ.get('DATABASE_PRIVATE_URL')
    if private_url:
        return private_url
    
    # Option 2: Construct URL from PG* variables (Railway provides these)
    # This is the PRIMARY method for Railway PostgreSQL
    pghost = os.environ.get('PGHOST')
    pgport = os.environ.get('PGPORT', '5432')
    pgdatabase = os.environ.get('PGDATABASE')
    pguser = os.environ.get('PGUSER')
    pgpassword = os.environ.get('PGPASSWORD')
    
    # If all PG* variables exist, construct connection string (Railway provides these)
    # ALWAYS use PG* variables if available, regardless of public/private
    # (Better to use public PostgreSQL than SQLite which doesn't persist!)
    if pghost and pgdatabase and pguser and pgpassword:
        # Construct PostgreSQL connection string
        return f'postgresql://{pguser}:{pgpassword}@{pghost}:{pgport}/{pgdatabase}'
    
    # Option 3: Use DATABASE_URL (Railway's standard variable)
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Fix postgres:// to postgresql:// if needed
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        return database_url
    
    # Option 4: Fall back to DATABASE_PUBLIC_URL only if nothing else available
    # (This will show the warning, but at least the app will work)
    public_url = os.environ.get('DATABASE_PUBLIC_URL')
    if public_url:
        if public_url.startswith('postgres://'):
            public_url = public_url.replace('postgres://', 'postgresql://', 1)
        return public_url
    
    return None

database_uri = get_database_uri()

# IMPORTANT: Log database connection for debugging (without password)
print("=" * 60)
print("[DATABASE CONFIG] Checking database connection...")

# Check what environment variables are available
pghost = os.environ.get('PGHOST')
pgdatabase = os.environ.get('PGDATABASE')
database_url = os.environ.get('DATABASE_URL')
public_url = os.environ.get('DATABASE_PUBLIC_URL')

print(f"[DATABASE CONFIG] Environment variables found:")
print(f"  - PGHOST: {'✅ Set' if pghost else '❌ Not set'}")
print(f"  - PGDATABASE: {'✅ Set' if pgdatabase else '❌ Not set'}")
print(f"  - DATABASE_URL: {'✅ Set' if database_url else '❌ Not set'}")
print(f"  - DATABASE_PUBLIC_URL: {'✅ Set' if public_url else '❌ Not set'}")

if database_uri:
    # Mask password in log
    safe_uri = database_uri
    if '@' in safe_uri and ':' in safe_uri.split('@')[0]:
        parts = safe_uri.split('@')
        user_pass = parts[0].split('://')[1] if '://' in parts[0] else parts[0]
        if ':' in user_pass:
            user = user_pass.split(':')[0]
            safe_uri = safe_uri.replace(user_pass, f'{user}:***', 1)
    
    # Extract database name for logging
    db_name = "unknown"
    if '/' in safe_uri:
        db_name = safe_uri.split('/')[-1].split('?')[0]
    
    print(f"[DATABASE CONFIG] ✅ Connection string: {safe_uri.split('@')[0]}@***")
    print(f"[DATABASE CONFIG] ✅ Database name: {db_name}")
    print(f"[DATABASE CONFIG] ✅ Using: {'PostgreSQL (Production)' if 'postgresql' in database_uri else 'SQLite (Development)'}")
else:
    print("[DATABASE CONFIG] ❌ CRITICAL ERROR: No database URI found!")
    print("[DATABASE CONFIG] ❌ This will use SQLite, which DOES NOT PERSIST on Railway!")
    print("[DATABASE CONFIG] ❌ Your data will be LOST on each deployment!")
    print("[DATABASE CONFIG] ❌ Please check Railway database connection!")
print("=" * 60)

if database_uri:
    # Production: Use PostgreSQL
    # Fix Heroku/Railway postgres:// to postgresql://
    if database_uri.startswith('postgres://'):
        database_uri = database_uri.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = database_uri
else:
    # Development: Use SQLite
    DATABASE_PATH = BASE_DIR / 'data' / 'database.db'
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
    (BASE_DIR / 'data').mkdir(exist_ok=True)

SQLALCHEMY_TRACK_MODIFICATIONS = False

# Uploads Configuration
# Use cloud storage URL if provided, otherwise local
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', str(BASE_DIR / 'uploads'))
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}

# Ensure upload directory exists (for local storage)
Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)

# Break Configuration (in minutes)
BREAK_DURATIONS = {
    "short": 15,
    "lunch": 30,
    "meeting": 60,
    "huddle": 15,
    "emergency": 15,  # Increased to 15 minutes
    "coaching_aya": 30,
    "coaching_mostafa": 30,
    "punch_in": 0,  # Single screenshot, auto-completed
    "punch_out": 0,  # Single screenshot, auto-completed
    "overtime": 0,
    "compensation": 0,
    "meeting_team_leader": 60
}

# Break display info
BREAK_INFO = {
    "short": {"name": "Short Break", "emoji": "☕", "color": "#2196f3"},
    "lunch": {"name": "Lunch Break", "emoji": "🍽️", "color": "#4caf50"},
    "meeting": {"name": "Meeting", "emoji": "📅", "color": "#9c27b0"},
    "huddle": {"name": "Huddle", "emoji": "👥", "color": "#ff9800"},
    "emergency": {"name": "Emergency", "emoji": "🚨", "color": "#f44336"},
    "coaching_aya": {"name": "Coaching with Aya", "emoji": "👩‍🏫", "color": "#e91e63"},
    "coaching_mostafa": {"name": "Coaching with ₘₒₛₜₐfₐ", "emoji": "👨‍🏫", "color": "#00bcd4"},
    "punch_in": {"name": "Punch In", "emoji": "🟢", "color": "#4caf50"},
    "punch_out": {"name": "Punch Out", "emoji": "🔴", "color": "#f44336"},
    "overtime": {"name": "Overtime", "emoji": "⏰", "color": "#ff9800"},
    "compensation": {"name": "Compensation", "emoji": "💰", "color": "#9c27b0"},
    "meeting_team_leader": {"name": "Meeting with Team Leader", "emoji": "👔", "color": "#607d8b"}
}

# User Roles
ROLE_AGENT = "agent"
ROLE_RTM = "rtm"

# Default admin account (created on first run)
# In production, change password immediately after first login!
DEFAULT_USERS = [
    {
        "username": os.environ.get('ADMIN_USERNAME', 'admin'),
        "password": os.environ.get('ADMIN_PASSWORD', 'admin123'),
        "full_name": "RTM Admin",
        "role": ROLE_RTM
    },
]
