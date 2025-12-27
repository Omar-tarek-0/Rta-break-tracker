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
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    # Production: Use PostgreSQL
    # Fix Heroku/Railway postgres:// to postgresql://
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
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
    "emergency": 15
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
