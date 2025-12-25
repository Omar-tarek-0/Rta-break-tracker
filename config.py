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
# Priority: DATABASE_PRIVATE_URL > PG* variables > DATABASE_URL > DATABASE_PUBLIC_URL > SQLite

print("=" * 60)
print("[DATABASE CONFIG] Checking database connection...")

# Get all possible database variables
DATABASE_PRIVATE_URL = os.environ.get('DATABASE_PRIVATE_URL')
DATABASE_URL = os.environ.get('DATABASE_URL')
DATABASE_PUBLIC_URL = os.environ.get('DATABASE_PUBLIC_URL')
PGHOST = os.environ.get('PGHOST')
PGDATABASE = os.environ.get('PGDATABASE')
PGUSER = os.environ.get('PGUSER')
PGPASSWORD = os.environ.get('PGPASSWORD')
PGPORT = os.environ.get('PGPORT', '5432')

print("[DATABASE CONFIG] Environment variables found:")
print(f"  - PGHOST: {'✅ Set' if PGHOST else '❌ Not set'}")
print(f"  - PGDATABASE: {'✅ Set' if PGDATABASE else '❌ Not set'}")
print(f"  - DATABASE_URL: {'✅ Set' if DATABASE_URL else '❌ Not set'}")
print(f"  - DATABASE_PUBLIC_URL: {'✅ Set' if DATABASE_PUBLIC_URL else '❌ Not set'}")

# Priority 1: DATABASE_PRIVATE_URL (private endpoint, no egress fees)
if DATABASE_PRIVATE_URL:
    SQLALCHEMY_DATABASE_URI = DATABASE_PRIVATE_URL
    if SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)
    print("[DATABASE CONFIG] ✅ Using: DATABASE_PRIVATE_URL (Private endpoint)")
# Priority 2: Construct from PG* variables (if PGHOST is internal)
elif PGHOST and PGDATABASE and PGUSER and PGPASSWORD:
    if 'railway.internal' in PGHOST or PGHOST == 'postgres.railway.internal':
        # Private endpoint - construct URI
        SQLALCHEMY_DATABASE_URI = f'postgresql://{PGUSER}:{PGPASSWORD}@{PGHOST}:{PGPORT}/{PGDATABASE}'
        print("[DATABASE CONFIG] ✅ Using: PostgreSQL (Private - from PG* variables)")
    else:
        # Public endpoint - use if no other option
        SQLALCHEMY_DATABASE_URI = f'postgresql://{PGUSER}:{PGPASSWORD}@{PGHOST}:{PGPORT}/{PGDATABASE}'
        print("[DATABASE CONFIG] ⚠️  Using: PostgreSQL (Public - from PG* variables)")
# Priority 3: DATABASE_URL
elif DATABASE_URL:
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    if SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)
    print("[DATABASE CONFIG] ✅ Using: DATABASE_URL")
# Priority 4: DATABASE_PUBLIC_URL (last resort - incurs egress fees)
elif DATABASE_PUBLIC_URL:
    SQLALCHEMY_DATABASE_URI = DATABASE_PUBLIC_URL
    if SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)
    print("[DATABASE CONFIG] ⚠️  Using: DATABASE_PUBLIC_URL (Public endpoint - may incur egress fees)")
# Fallback: SQLite (development only)
else:
    DATABASE_PATH = BASE_DIR / 'data' / 'database.db'
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
    (BASE_DIR / 'data').mkdir(exist_ok=True)
    print("[DATABASE CONFIG] ❌ CRITICAL ERROR: No database URI found!")
    print("[DATABASE CONFIG] ❌ This will use SQLite, which DOES NOT PERSIST on Railway!")
    print("[DATABASE CONFIG] ❌ Your data will be LOST on each deployment!")
    print("[DATABASE CONFIG] ❌ Please check Railway database connection!")

print("=" * 60)

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
    "emergency": 10
}

# Break display info
BREAK_INFO = {
    "short": {"name": "Short Break", "emoji": "☕", "color": "#2196f3"},
    "lunch": {"name": "Lunch Break", "emoji": "🍽️", "color": "#4caf50"},
    "meeting": {"name": "Meeting", "emoji": "📅", "color": "#9c27b0"},
    "huddle": {"name": "Huddle", "emoji": "👥", "color": "#ff9800"},
    "emergency": {"name": "Emergency", "emoji": "🚨", "color": "#f44336"}
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
