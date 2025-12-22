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
    
    # Option 2: Construct private URL from PG* variables (no fees if PGHOST is internal)
    pghost = os.environ.get('PGHOST')
    pgport = os.environ.get('PGPORT', '5432')
    pgdatabase = os.environ.get('PGDATABASE')
    pguser = os.environ.get('PGUSER')
    pgpassword = os.environ.get('PGPASSWORD')
    
    # If PGHOST exists and looks like a private/internal hostname, use it
    if pghost and pgdatabase and pguser and pgpassword:
        # Private hostnames typically contain: .internal, .local, or are private IPs
        if '.internal' in pghost or '.local' in pghost or pghost.startswith('10.') or pghost.startswith('172.') or pghost.startswith('192.168.'):
            return f'postgresql://{pguser}:{pgpassword}@{pghost}:{pgport}/{pgdatabase}'
    
    # Option 3: Use DATABASE_URL (check if it's private)
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # If DATABASE_URL uses a private host, it's fine
        # If it uses DATABASE_PUBLIC_URL, we'll avoid it below
        return database_url
    
    # Option 4: Fall back to DATABASE_PUBLIC_URL only if nothing else available
    # (This will show the warning, but at least the app will work)
    public_url = os.environ.get('DATABASE_PUBLIC_URL')
    if public_url:
        return public_url
    
    return None

database_uri = get_database_uri()

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
