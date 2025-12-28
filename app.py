"""
RTA Break Tracker - Web Application
Flask-based web app for tracking agent breaks
"""
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, Response
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from pathlib import Path
import bcrypt
import os
import uuid
import io

from config import (
    SECRET_KEY, SQLALCHEMY_DATABASE_URI, UPLOAD_FOLDER, 
    ALLOWED_EXTENSIONS, BREAK_DURATIONS, BREAK_INFO,
    ROLE_AGENT, ROLE_RTM, DEFAULT_USERS, DEBUG, ENV, TIMEZONE
)
import pytz
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

def get_local_time():
    """Get current time in configured timezone"""
    return datetime.now(TIMEZONE)

def to_local_time(dt):
    """Return datetime as-is (already stored in local time)"""
    if dt is None:
        return None
    # Times are stored in local timezone already, just return as-is
    return dt

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# ==================== MODELS ====================

class User(UserMixin, db.Model):
    """User model for agents and RTM"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=ROLE_AGENT)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    breaks = db.relationship('BreakRecord', backref='agent', lazy=True)
    
    def is_rtm(self):
        return self.role == ROLE_RTM
    
    def is_agent(self):
        return self.role == ROLE_AGENT
    
    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))


class Shift(db.Model):
    """Shift model for tracking agent work schedules"""
    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    shift_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    agent = db.relationship('User', foreign_keys=[agent_id], backref='shifts')
    
    def get_duration_hours(self):
        """Calculate shift duration in hours"""
        start = datetime.combine(self.shift_date, self.start_time)
        end = datetime.combine(self.shift_date, self.end_time)
        if end < start:  # Overnight shift
            end += timedelta(days=1)
        return (end - start).total_seconds() / 3600
    
    def to_dict(self):
        return {
            'id': self.id,
            'agent_id': self.agent_id,
            'agent_name': self.agent.full_name if self.agent else 'Unknown',
            'shift_date': self.shift_date.isoformat(),
            'start_time': self.start_time.strftime('%H:%M'),
            'end_time': self.end_time.strftime('%H:%M'),
            'duration_hours': round(self.get_duration_hours(), 2)
        }


class BreakRecord(db.Model):
    """Break record model"""
    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    break_type = db.Column(db.String(20), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    start_screenshot = db.Column(db.String(255))
    end_time = db.Column(db.DateTime)
    end_screenshot = db.Column(db.String(255))
    duration_minutes = db.Column(db.Integer)
    is_overdue = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def is_active(self):
        return self.end_time is None
    
    def get_elapsed_minutes(self):
        if self.start_time:
            # Both times are in local timezone
            now = get_local_time().replace(tzinfo=None)
            elapsed = now - self.start_time
            return max(0, int(elapsed.total_seconds() / 60))
        return 0
    
    def get_break_info(self):
        return BREAK_INFO.get(self.break_type, {"name": self.break_type, "emoji": "⏱️", "color": "#666"})
    
    def get_allowed_duration(self):
        return BREAK_DURATIONS.get(self.break_type, 15)
    
    def get_local_start_time(self):
        """Get start time in local timezone"""
        if self.start_time:
            return to_local_time(self.start_time)
        return None
    
    def get_local_end_time(self):
        """Get end time in local timezone"""
        if self.end_time:
            return to_local_time(self.end_time)
        return None
    
    def to_dict(self):
        info = self.get_break_info()
        local_start = self.get_local_start_time()
        local_end = self.get_local_end_time()
        return {
            'id': self.id,
            'agent_id': self.agent_id,
            'agent_name': self.agent.full_name if self.agent else 'Unknown',
            'break_type': self.break_type,
            'break_name': info['name'],
            'break_emoji': info['emoji'],
            'break_color': info['color'],
            'start_time': local_start.isoformat() if local_start else None,
            'end_time': local_end.isoformat() if local_end else None,
            'start_screenshot': self.start_screenshot,
            'end_screenshot': self.end_screenshot,
            'duration_minutes': self.duration_minutes,
            'elapsed_minutes': self.get_elapsed_minutes() if self.is_active() else self.duration_minutes,
            'is_active': self.is_active(),
            'is_overdue': self.is_overdue,
            'notes': self.notes or '',
            'allowed_duration': self.get_allowed_duration()
        }


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ==================== HELPERS ====================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_screenshot(file):
    """Save uploaded screenshot and return filename"""
    if file and allowed_file(file.filename):
        # Generate unique filename
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        
        # Create date-based folder
        today = get_local_time().strftime("%Y-%m-%d")
        folder = Path(app.config['UPLOAD_FOLDER']) / today
        folder.mkdir(parents=True, exist_ok=True)
        
        # Save file
        filepath = folder / filename
        file.save(str(filepath))
        
        return f"{today}/{filename}"
    return None


def init_db():
    """Initialize database and create default users"""
    db.create_all()
    
    # Create default users if they don't exist
    for user_data in DEFAULT_USERS:
        if not User.query.filter_by(username=user_data['username']).first():
            user = User(
                username=user_data['username'],
                full_name=user_data['full_name'],
                role=user_data['role']
            )
            user.set_password(user_data['password'])
            db.session.add(user)
    
    db.session.commit()


# ==================== ROUTES ====================

@app.route('/')
def index():
    """Home page - redirect to appropriate view"""
    if current_user.is_authenticated:
        if current_user.is_rtm():
            return redirect(url_for('dashboard'))
        return redirect(url_for('agent_view'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """Logout"""
    logout_user()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))


@app.route('/agent')
@login_required
def agent_view():
    """Agent view for submitting breaks"""
    if current_user.is_rtm():
        return redirect(url_for('dashboard'))
    
    # Get active break for this agent
    active_break = BreakRecord.query.filter_by(
        agent_id=current_user.id,
        end_time=None
    ).first()
    
    # Get today's breaks
    today = get_local_time().date()
    today_breaks = BreakRecord.query.filter(
        BreakRecord.agent_id == current_user.id,
        db.func.date(BreakRecord.start_time) == today
    ).order_by(BreakRecord.start_time.desc()).all()
    
    # Get today's shift for this agent
    today_shift = Shift.query.filter_by(
        agent_id=current_user.id,
        shift_date=today
    ).first()
    
    # Check punch in/out status for today
    punch_in = BreakRecord.query.filter(
        BreakRecord.agent_id == current_user.id,
        BreakRecord.break_type == 'punch_in',
        db.func.date(BreakRecord.start_time) == today
    ).first()
    
    punch_out = BreakRecord.query.filter(
        BreakRecord.agent_id == current_user.id,
        BreakRecord.break_type == 'punch_out',
        db.func.date(BreakRecord.start_time) == today
    ).first()
    
    # Determine agent status
    # not_punched_in: hasn't punched in yet today
    # punched_in: punched in but not out
    # punched_out: already punched out for the day
    if not punch_in:
        punch_status = 'not_punched_in'
    elif punch_out:
        punch_status = 'punched_out'
    else:
        punch_status = 'punched_in'
    
    return render_template('agent.html',
        user=current_user,
        active_break=active_break,
        today_breaks=today_breaks,
        today_shift=today_shift,
        punch_status=punch_status,
        punch_in_time=punch_in.start_time if punch_in else None,
        punch_out_time=punch_out.start_time if punch_out else None,
        break_types=BREAK_INFO,
        break_durations=BREAK_DURATIONS
    )


@app.route('/dashboard')
@login_required
def dashboard():
    """RTM Dashboard"""
    if not current_user.is_rtm():
        return redirect(url_for('agent_view'))
    
    # Get filter parameters
    date_filter = request.args.get('date', get_local_time().strftime('%Y-%m-%d'))
    agent_filter = request.args.get('agent', '')
    type_filter = request.args.get('type', '')
    
    # Get all agents
    agents = User.query.filter_by(role=ROLE_AGENT).order_by(User.full_name).all()
    
    # Get stats
    today = get_local_time().date()
    total_breaks_today = BreakRecord.query.filter(
        db.func.date(BreakRecord.start_time) == today
    ).count()
    active_breaks = BreakRecord.query.filter_by(end_time=None).count()
    overdue_breaks = BreakRecord.query.filter(
        db.func.date(BreakRecord.start_time) == today,
        BreakRecord.is_overdue == True
    ).count()
    
    return render_template('dashboard.html',
        user=current_user,
        agents=agents,
        total_agents=len(agents),
        total_breaks_today=total_breaks_today,
        active_breaks=active_breaks,
        overdue_breaks=overdue_breaks,
        break_types=BREAK_INFO,
        break_durations=BREAK_DURATIONS,
        date_filter=date_filter,
        agent_filter=agent_filter,
        type_filter=type_filter
    )


# ==================== API ROUTES ====================

@app.route('/api/breaks', methods=['GET'])
@login_required
def get_breaks():
    """Get breaks for dashboard"""
    if not current_user.is_rtm():
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get filter parameters
    start_date = request.args.get('start_date', get_local_time().strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', start_date)
    agent_id = request.args.get('agent_id', '')
    break_type = request.args.get('break_type', '')
    
    # Build query
    query = BreakRecord.query.filter(
        db.func.date(BreakRecord.start_time) >= start_date,
        db.func.date(BreakRecord.start_time) <= end_date
    )
    
    if agent_id:
        query = query.filter_by(agent_id=int(agent_id))
    
    if break_type:
        query = query.filter_by(break_type=break_type)
    
    breaks = query.order_by(BreakRecord.start_time.desc()).all()
    
    # Group by agent and determine status
    agents_data = {}
    for br in breaks:
        if br.agent_id not in agents_data:
            # Check if agent has an active break (exclude punch_in/punch_out - these are attendance, not breaks)
            active_break = BreakRecord.query.filter(
                BreakRecord.agent_id == br.agent_id,
                BreakRecord.end_time == None,
                BreakRecord.break_type.notin_(['punch_in', 'punch_out'])
            ).first()
            
            agents_data[br.agent_id] = {
                'agent_name': br.agent.full_name,
                'agent_status': 'on_break' if active_break else 'available',
                'active_break_type': active_break.break_type if active_break else None,
                'breaks': []
            }
        agents_data[br.agent_id]['breaks'].append(br.to_dict())
    
    # Count only regular breaks (exclude punch_in/punch_out)
    regular_breaks_count = len([b for b in breaks if b.break_type not in ['punch_in', 'punch_out']])
    
    return jsonify({
        'agents': list(agents_data.values()),
        'total_breaks': regular_breaks_count
    })


@app.route('/api/break/start', methods=['POST'])
@login_required
def start_break():
    """Start a new break"""
    if current_user.is_rtm():
        return jsonify({'error': 'RTM cannot take breaks'}), 403
    
    # Check for active break
    active = BreakRecord.query.filter_by(agent_id=current_user.id, end_time=None).first()
    if active:
        return jsonify({'error': 'You already have an active break'}), 400
    
    break_type = request.form.get('break_type')
    screenshot = request.files.get('screenshot')
    
    if not break_type or break_type not in BREAK_DURATIONS:
        return jsonify({'error': 'Invalid break type'}), 400
    
    if not screenshot:
        return jsonify({'error': 'Screenshot is required'}), 400
    
    # Save screenshot
    screenshot_path = save_screenshot(screenshot)
    if not screenshot_path:
        return jsonify({'error': 'Invalid screenshot file'}), 400
    
    # Create break record
    break_record = BreakRecord(
        agent_id=current_user.id,
        break_type=break_type,
        start_time=get_local_time().replace(tzinfo=None),
        start_screenshot=screenshot_path
    )
    db.session.add(break_record)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Break started! Return within {BREAK_DURATIONS[break_type]} minutes',
        'break': break_record.to_dict()
    })


@app.route('/api/break/end', methods=['POST'])
@login_required
def end_break():
    """End current break"""
    if current_user.is_rtm():
        return jsonify({'error': 'RTM cannot take breaks'}), 403
    
    # Get active break
    active = BreakRecord.query.filter_by(agent_id=current_user.id, end_time=None).first()
    if not active:
        return jsonify({'error': 'No active break to end'}), 400
    
    screenshot = request.files.get('screenshot')
    if not screenshot:
        return jsonify({'error': 'Screenshot is required'}), 400
    
    # Save screenshot
    screenshot_path = save_screenshot(screenshot)
    if not screenshot_path:
        return jsonify({'error': 'Invalid screenshot file'}), 400
    
    # Update break record
    active.end_time = get_local_time().replace(tzinfo=None)
    active.end_screenshot = screenshot_path
    active.duration_minutes = int((active.end_time - active.start_time).total_seconds() / 60)
    active.is_overdue = active.duration_minutes > active.get_allowed_duration()
    
    db.session.commit()
    
    status = "on time" if not active.is_overdue else "OVERDUE"
    return jsonify({
        'success': True,
        'message': f'Break ended! Duration: {active.duration_minutes} minutes ({status})',
        'break': active.to_dict()
    })


@app.route('/api/break/<int:break_id>/notes', methods=['POST'])
@login_required
def update_notes(break_id):
    """Update break notes"""
    if not current_user.is_rtm():
        return jsonify({'error': 'Unauthorized'}), 403
    
    break_record = BreakRecord.query.get_or_404(break_id)
    notes = request.json.get('notes', '')
    
    break_record.notes = notes
    db.session.commit()
    
    return jsonify({'success': True, 'notes': notes})


@app.route('/api/break/manual', methods=['POST'])
@login_required
def create_manual_break():
    """RTM can manually create break records for agents"""
    if not current_user.is_rtm():
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get form data
    agent_id = request.form.get('agent_id', type=int)
    break_type = request.form.get('break_type')
    start_date = request.form.get('start_date')
    start_time = request.form.get('start_time')
    end_date = request.form.get('end_date', '')
    end_time = request.form.get('end_time', '')
    notes = request.form.get('notes', '')
    
    # Files
    start_screenshot = request.files.get('start_screenshot')
    end_screenshot = request.files.get('end_screenshot')
    
    # Validation
    if not agent_id:
        return jsonify({'error': 'Agent ID is required'}), 400
    if not break_type or break_type not in BREAK_DURATIONS:
        return jsonify({'error': 'Invalid break type'}), 400
    if not start_date or not start_time:
        return jsonify({'error': 'Start date and time are required'}), 400
    
    # Check if agent exists
    agent = User.query.get(agent_id)
    if not agent or not agent.is_agent():
        return jsonify({'error': 'Invalid agent'}), 400
    
    # Parse start datetime
    try:
        start_datetime_str = f"{start_date} {start_time}"
        start_datetime = datetime.strptime(start_datetime_str, '%Y-%m-%d %H:%M')
        # Localize to configured timezone
        start_datetime = TIMEZONE.localize(start_datetime).replace(tzinfo=None)
    except ValueError:
        return jsonify({'error': 'Invalid start date/time format'}), 400
    
    # Parse end datetime (if provided)
    end_datetime = None
    if end_date and end_time:
        try:
            end_datetime_str = f"{end_date} {end_time}"
            end_datetime = datetime.strptime(end_datetime_str, '%Y-%m-%d %H:%M')
            end_datetime = TIMEZONE.localize(end_datetime).replace(tzinfo=None)
            
            if end_datetime < start_datetime:
                return jsonify({'error': 'End time must be after start time'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid end date/time format'}), 400
    
    # Save screenshots
    start_screenshot_path = None
    if start_screenshot:
        start_screenshot_path = save_screenshot(start_screenshot)
        if not start_screenshot_path:
            return jsonify({'error': 'Invalid start screenshot file'}), 400
    
    end_screenshot_path = None
    if end_screenshot:
        end_screenshot_path = save_screenshot(end_screenshot)
        if not end_screenshot_path:
            return jsonify({'error': 'Invalid end screenshot file'}), 400
    
    # Calculate duration if end time is provided
    duration_minutes = None
    is_overdue = False
    if end_datetime:
        duration_minutes = int((end_datetime - start_datetime).total_seconds() / 60)
        allowed_duration = BREAK_DURATIONS.get(break_type, 15)
        is_overdue = duration_minutes > allowed_duration
    
    # Create break record
    break_record = BreakRecord(
        agent_id=agent_id,
        break_type=break_type,
        start_time=start_datetime,
        start_screenshot=start_screenshot_path,
        end_time=end_datetime,
        end_screenshot=end_screenshot_path,
        duration_minutes=duration_minutes,
        is_overdue=is_overdue,
        notes=notes
    )
    
    db.session.add(break_record)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Break record created successfully',
        'break': break_record.to_dict()
    })


@app.route('/api/agents', methods=['GET'])
@login_required
def get_agents():
    """Get all agents"""
    if not current_user.is_rtm():
        return jsonify({'error': 'Unauthorized'}), 403
    
    agents = User.query.filter_by(role=ROLE_AGENT).order_by(User.full_name).all()
    return jsonify({
        'agents': [{'id': a.id, 'username': a.username, 'full_name': a.full_name} for a in agents]
    })


@app.route('/api/agent/create', methods=['POST'])
@login_required
def create_agent():
    """Create a new agent"""
    if not current_user.is_rtm():
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    full_name = data.get('full_name', '').strip()
    
    if not username or not password or not full_name:
        return jsonify({'error': 'All fields are required'}), 400
    
    if len(password) < 4:
        return jsonify({'error': 'Password must be at least 4 characters'}), 400
    
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 400
    
    user = User(username=username, full_name=full_name, role=ROLE_AGENT)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'agent': {'id': user.id, 'username': user.username, 'full_name': user.full_name}
    })


@app.route('/uploads/<path:filename>')
@login_required
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ==================== SHIFT MANAGEMENT API ====================

@app.route('/api/shifts', methods=['GET'])
@login_required
def get_shifts():
    """Get shifts for a date range"""
    if not current_user.is_rtm():
        return jsonify({'error': 'Unauthorized'}), 403
    
    start_date_str = request.args.get('start_date', get_local_time().strftime('%Y-%m-%d'))
    end_date_str = request.args.get('end_date', start_date_str)
    agent_id = request.args.get('agent_id', '')
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    
    query = Shift.query.filter(
        Shift.shift_date >= start_date,
        Shift.shift_date <= end_date
    )
    
    if agent_id:
        query = query.filter_by(agent_id=int(agent_id))
    
    shifts = query.order_by(Shift.shift_date, Shift.start_time).all()
    
    return jsonify({
        'shifts': [s.to_dict() for s in shifts],
        'total': len(shifts)
    })


@app.route('/api/shift/bulk', methods=['POST'])
@login_required
def create_bulk_shifts():
    """Create shifts for multiple agents over a date range (e.g., 2 weeks)"""
    if not current_user.is_rtm():
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    agent_ids = data.get('agent_ids', [])
    start_date_str = data.get('start_date')
    end_date_str = data.get('end_date')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    
    if not all([agent_ids, start_date_str, end_date_str, start_time, end_time]):
        return jsonify({'error': 'All fields are required'}), 400
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        start_time_obj = datetime.strptime(start_time, '%H:%M').time()
        end_time_obj = datetime.strptime(end_time, '%H:%M').time()
    except ValueError:
        return jsonify({'error': 'Invalid date or time format'}), 400
    
    # Validate date range (max 14 days for 2 weeks)
    days_diff = (end_date - start_date).days + 1
    if days_diff > 14:
        return jsonify({'error': 'Date range cannot exceed 14 days (2 weeks)'}), 400
    
    if days_diff < 1:
        return jsonify({'error': 'End date must be after start date'}), 400
    
    created = 0
    updated = 0
    
    # Generate all dates in range
    current_date = start_date
    dates_to_create = []
    while current_date <= end_date:
        dates_to_create.append(current_date)
        current_date += timedelta(days=1)
    
    # Create/update shifts for each agent and each date
    for agent_id in agent_ids:
        agent = User.query.filter_by(id=agent_id, role=ROLE_AGENT).first()
        if not agent:
            continue
        
        for shift_date in dates_to_create:
            existing = Shift.query.filter_by(agent_id=agent_id, shift_date=shift_date).first()
            if existing:
                existing.start_time = start_time_obj
                existing.end_time = end_time_obj
                updated += 1
            else:
                shift = Shift(
                    agent_id=agent_id,
                    shift_date=shift_date,
                    start_time=start_time_obj,
                    end_time=end_time_obj,
                    created_by=current_user.id
                )
                db.session.add(shift)
                created += 1
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Created {created} shifts, updated {updated} shifts for {len(dates_to_create)} days',
        'days_created': len(dates_to_create),
        'created': created,
        'updated': updated
    })


@app.route('/api/shift/<int:shift_id>', methods=['DELETE'])
@login_required
def delete_shift(shift_id):
    """Delete a shift"""
    if not current_user.is_rtm():
        return jsonify({'error': 'Unauthorized'}), 403
    
    shift = Shift.query.get_or_404(shift_id)
    db.session.delete(shift)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Shift deleted'})


# ==================== REPORTING & EXPORT ====================

def calculate_agent_metrics(agent_id, start_date, end_date):
    """Calculate all metrics for an agent within a date range"""
    
    # Get all breaks for this agent in date range
    breaks = BreakRecord.query.filter(
        BreakRecord.agent_id == agent_id,
        db.func.date(BreakRecord.start_time) >= start_date,
        db.func.date(BreakRecord.start_time) <= end_date
    ).all()
    
    # Get all shifts for this agent in date range
    shifts = Shift.query.filter(
        Shift.agent_id == agent_id,
        Shift.shift_date >= datetime.strptime(start_date, '%Y-%m-%d').date(),
        Shift.shift_date <= datetime.strptime(end_date, '%Y-%m-%d').date()
    ).all()
    
    # Calculate metrics
    total_scheduled_minutes = sum(s.get_duration_hours() * 60 for s in shifts)
    
    # Exclude punch_in and punch_out from break calculations
    regular_breaks = [b for b in breaks if b.break_type not in ['punch_in', 'punch_out']]
    
    total_break_minutes = sum(b.duration_minutes or 0 for b in regular_breaks if b.end_time)
    total_allowed_break_minutes = sum(b.get_allowed_duration() for b in regular_breaks if b.end_time)
    exceeding_break_minutes = max(0, total_break_minutes - total_allowed_break_minutes)
    
    # Count incidents (overdue breaks) - exclude punch_in/punch_out
    incidents = sum(1 for b in regular_breaks if b.is_overdue)
    
    # Count emergency breaks
    emergency_count = sum(1 for b in breaks if b.break_type == 'emergency')
    
    # Count breaks by type
    break_counts = {}
    for b in breaks:
        break_counts[b.break_type] = break_counts.get(b.break_type, 0) + 1
    
    # Extract specific counts for reporting
    lunch_count = break_counts.get('lunch', 0)
    coaching_count = break_counts.get('coaching_aya', 0) + break_counts.get('coaching_mostafa', 0)
    overtime_count = break_counts.get('overtime', 0)
    compensation_count = break_counts.get('compensation', 0)
    
    # ==================== UTILIZATION CALCULATION ====================
    # Utilization: Working hours = 8 hours, Break = 1 hour allocated
    # If agent worked 8 hours and took 1 hour break = 100% utilization
    # If agent took emergency (or any break) that exceeds the 1 hour allocated break, 
    # that reduces the utilization because working time decreases
    
    # Calculate all break time (excluding overtime and compensation - these are work, not breaks)
    # Include: short, lunch, emergency, meeting, huddle, coaching, etc.
    utilization_break_minutes = 0
    for b in regular_breaks:
        if b.end_time and b.break_type not in ['overtime', 'compensation']:
            utilization_break_minutes += b.duration_minutes or 0
    
    # Expected working time: 8 hours per shift (480 minutes)
    # Expected break time: 1 hour per shift (60 minutes) - allocated for breaks
    expected_working_minutes = len(shifts) * 8 * 60  # 8 hours per shift = 480 minutes
    expected_break_minutes = len(shifts) * 60  # 60 minutes per shift (allocated break time)
    
    # Calculate actual working time
    # Formula: actual_working_time = expected_working_time - (actual_break_time - expected_break_time)
    #         = expected_working_time - excess_break_time
    # If breaks <= 1 hour: actual_working_time = 8 hours (100% utilization)
    # If breaks > 1 hour: actual_working_time = 8 hours - (excess break time) (< 100% utilization)
    if expected_working_minutes > 0:
        # Calculate excess break time (breaks beyond the allocated 1 hour)
        excess_break_minutes = max(0, utilization_break_minutes - expected_break_minutes)
        
        # Actual working time = expected working time - excess break time
        actual_working_time = expected_working_minutes - excess_break_minutes
        
        # Utilization = (actual working time / expected working time) * 100
        utilization = (actual_working_time / expected_working_minutes) * 100
    else:
        utilization = 0
    
    # ==================== ADHERENCE CALCULATION ====================
    # Adherence: Based on break durations and shift timing
    # 1. Break duration adherence: If agent took break 1 for 16 mins (allowed 15 mins), adherence is reduced
    # 2. Shift timing adherence: If agent came/punched in on assigned shift time, they're adhering
    
    adherence_scores = []
    
    # 1. Break duration adherence
    # For each break, check if actual duration <= allowed duration
    # If exceeded, calculate penalty: (allowed_duration / actual_duration) * 100
    total_completed_breaks = len([b for b in breaks if b.end_time and b.break_type not in ['punch_in', 'punch_out', 'overtime', 'compensation']])
    
    if total_completed_breaks > 0:
        for b in breaks:
            if b.end_time and b.duration_minutes is not None and b.break_type not in ['punch_in', 'punch_out', 'overtime', 'compensation']:
                allowed_duration = b.get_allowed_duration()
                if allowed_duration > 0:
                    actual_duration = b.duration_minutes
                    if actual_duration <= allowed_duration:
                        # Within allowed time = 100% adherence
                        break_adherence = 100.0
                    else:
                        # Exceeded allowed time = penalty
                        # Example: 15 mins allowed, 16 mins taken = (15/16) * 100 = 93.75%
                        break_adherence = (allowed_duration / actual_duration) * 100
                    adherence_scores.append(break_adherence)
    
    # 2. Shift timing adherence (punch in/out vs assigned shift times)
    # If agent came/punched in on assigned shift time, they're adhering
    shifts_by_date = {s.shift_date: s for s in shifts}
    
    # Group punch in/out by date
    punch_records_by_date = {}
    for b in breaks:
        if b.break_type in ['punch_in', 'punch_out'] and b.start_time:
            punch_date = b.start_time.date()
            if punch_date not in punch_records_by_date:
                punch_records_by_date[punch_date] = {}
            punch_records_by_date[punch_date][b.break_type] = b
    
    # Calculate punch in/out adherence for each day with a shift
    for shift_date, shift in shifts_by_date.items():
        punch_records = punch_records_by_date.get(shift_date, {})
        
        # Punch in adherence: Did agent punch in on assigned shift time?
        if 'punch_in' in punch_records:
            punch_in = punch_records['punch_in']
            punch_in_time = punch_in.start_time.time()
            shift_start_time = shift.start_time
            
            # Calculate difference in minutes
            punch_in_datetime = datetime.combine(shift_date, punch_in_time)
            shift_start_datetime = datetime.combine(shift_date, shift_start_time)
            
            # Allow 5 minutes grace period (early or late)
            time_diff_minutes = abs((punch_in_datetime - shift_start_datetime).total_seconds() / 60)
            
            if time_diff_minutes <= 5:
                punch_in_adherence = 100.0
            else:
                # Penalty: decrease adherence for being late/early
                # Max penalty at 30 minutes = 0% adherence
                punch_in_adherence = max(0, (30 - time_diff_minutes) / 30 * 100)
            adherence_scores.append(punch_in_adherence)
        else:
            # No punch in = 0% adherence for that day
            adherence_scores.append(0.0)
        
        # Punch out adherence: Did agent punch out on assigned shift time?
        if 'punch_out' in punch_records:
            punch_out = punch_records['punch_out']
            punch_out_time = punch_out.start_time.time()
            shift_end_time = shift.end_time
            
            # Calculate difference in minutes
            punch_out_datetime = datetime.combine(shift_date, punch_out_time)
            shift_end_datetime = datetime.combine(shift_date, shift_end_time)
            
            # Handle overnight shifts
            if shift_end_time < shift.start_time:
                shift_end_datetime += timedelta(days=1)
            
            # Allow 5 minutes grace period (early or late)
            time_diff_minutes = abs((punch_out_datetime - shift_end_datetime).total_seconds() / 60)
            
            if time_diff_minutes <= 5:
                punch_out_adherence = 100.0
            else:
                # Penalty: decrease adherence for being late/early
                punch_out_adherence = max(0, (30 - time_diff_minutes) / 30 * 100)
            adherence_scores.append(punch_out_adherence)
        else:
            # No punch out = 0% adherence for that day
            adherence_scores.append(0.0)
    
    # Calculate overall adherence as average of all scores
    if adherence_scores:
        adherence = sum(adherence_scores) / len(adherence_scores)
    else:
        adherence = 100  # No data = 100% adherence (default)
    
    # ==================== CONFORMANCE CALCULATION ====================
    # Conformance: Agent should work 8 hours per day
    # If they worked exactly 8 hours = 100% conformance
    # If they worked 7.59 hours = reduced conformance
    # If they worked more than 8 hours but didn't come on shift, but used compensation aux 
    # to make up missing minutes to reach 8 hours, it should count for conformance
    # Formula: Conformance = (actual working hours / 8 hours) × 100
    # Compensation aux counts toward the 8 hours
    
    if len(shifts) > 0:
        # Calculate actual working hours
        # Working time = shift duration - break time + compensation time
        # Compensation aux counts as working time (to compensate for missing minutes)
        
        # Get compensation time (compensation aux counts toward working hours)
        compensation_minutes = sum(
            b.duration_minutes or 0 
            for b in breaks 
            if b.break_type == 'compensation' and b.end_time
        )
        
        # Calculate actual working time
        # Formula: actual_working_hours = (shift_duration - break_time) + compensation_time
        # But we need to account for the fact that shift duration includes allocated break time
        # So: actual_working_hours = expected_working_hours - excess_break_time + compensation_time
        
        # Calculate excess break time (breaks beyond allocated 1 hour)
        excess_break_minutes = max(0, utilization_break_minutes - expected_break_minutes)
        
        # Actual working hours = expected working hours - excess breaks + compensation
        actual_working_minutes = expected_working_minutes - excess_break_minutes + compensation_minutes
        
        # Conformance = (actual working hours / 8 hours) × 100
        # Cap at 100% (can't exceed 100% conformance)
        conformance = min(100.0, (actual_working_minutes / expected_working_minutes) * 100)
    else:
        conformance = 0  # No shifts assigned = 0% conformance
    
    return {
        'total_scheduled_hours': round(total_scheduled_minutes / 60, 2),
        'total_break_minutes': total_break_minutes,
        'total_allowed_break_minutes': total_allowed_break_minutes,
        'exceeding_break_minutes': exceeding_break_minutes,
        'incidents': incidents,
        'emergency_count': emergency_count,
        'total_breaks': len(regular_breaks),  # Exclude punch_in/punch_out from total
        'completed_breaks': total_completed_breaks,
        'utilization': round(utilization, 1),
        'adherence': round(adherence, 1),
        'conformance': round(conformance, 1),
        'break_counts': break_counts,
        'lunch_count': lunch_count,
        'coaching_count': coaching_count,
        'overtime_count': overtime_count,
        'compensation_count': compensation_count,
        'shifts_count': len(shifts)
    }


@app.route('/api/report/metrics', methods=['GET'])
@login_required
def get_metrics():
    """Get metrics for all agents"""
    if not current_user.is_rtm():
        return jsonify({'error': 'Unauthorized'}), 403
    
    start_date = request.args.get('start_date', get_local_time().strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', start_date)
    
    agents = User.query.filter_by(role=ROLE_AGENT).order_by(User.full_name).all()
    
    results = []
    totals = {
        'total_scheduled_hours': 0,
        'total_break_minutes': 0,
        'exceeding_break_minutes': 0,
        'incidents': 0,
        'emergency_count': 0,
        'total_breaks': 0,
        'utilization_sum': 0,
        'adherence_sum': 0,
        'conformance_sum': 0,
        'agent_count': 0
    }
    
    for agent in agents:
        metrics = calculate_agent_metrics(agent.id, start_date, end_date)
        results.append({
            'agent_id': agent.id,
            'agent_name': agent.full_name,
            'username': agent.username,
            **metrics
        })
        
        # Accumulate totals
        totals['total_scheduled_hours'] += metrics['total_scheduled_hours']
        totals['total_break_minutes'] += metrics['total_break_minutes']
        totals['exceeding_break_minutes'] += metrics['exceeding_break_minutes']
        totals['incidents'] += metrics['incidents']
        totals['emergency_count'] += metrics['emergency_count']
        totals['total_breaks'] += metrics['total_breaks']
        if metrics['shifts_count'] > 0:
            totals['utilization_sum'] += metrics['utilization']
            totals['adherence_sum'] += metrics['adherence']
            totals['conformance_sum'] += metrics['conformance']
            totals['agent_count'] += 1
    
    # Calculate averages
    if totals['agent_count'] > 0:
        totals['avg_utilization'] = round(totals['utilization_sum'] / totals['agent_count'], 1)
        totals['avg_adherence'] = round(totals['adherence_sum'] / totals['agent_count'], 1)
        totals['avg_conformance'] = round(totals['conformance_sum'] / totals['agent_count'], 1)
    else:
        totals['avg_utilization'] = 0
        totals['avg_adherence'] = 0
        totals['avg_conformance'] = 0
    
    return jsonify({
        'agents': results,
        'totals': totals,
        'date_range': {'start': start_date, 'end': end_date}
    })


@app.route('/api/report/export', methods=['GET'])
@login_required
def export_report():
    """Export metrics to Excel"""
    if not current_user.is_rtm():
        return jsonify({'error': 'Unauthorized'}), 403
    
    start_date = request.args.get('start_date', get_local_time().strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', start_date)
    
    agents = User.query.filter_by(role=ROLE_AGENT).order_by(User.full_name).all()
    
    # Create workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Agent Metrics"
    
    # Styles
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="1a73e8", end_color="1a73e8", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    
    cell_alignment = Alignment(horizontal="center", vertical="center")
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    good_fill = PatternFill(start_color="c6efce", end_color="c6efce", fill_type="solid")
    warning_fill = PatternFill(start_color="ffeb9c", end_color="ffeb9c", fill_type="solid")
    bad_fill = PatternFill(start_color="ffc7ce", end_color="ffc7ce", fill_type="solid")
    
    # Title
    ws.merge_cells('A1:M1')
    ws['A1'] = f"RTA Agent Metrics Report ({start_date} to {end_date})"
    ws['A1'].font = Font(bold=True, size=14)
    ws['A1'].alignment = Alignment(horizontal="center")
    
    # Headers (row 3)
    headers = [
        "Agent Name",
        "Username", 
        "Scheduled Hours",
        "Total Breaks",
        "Break Time (min)",
        "Allowed Break (min)",
        "Exceeding (min)",
        "Incidents",
        "Emergency",
        "Utilization %",
        "Adherence %",
        "Conformance %",
        "Status"
    ]
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = border
    
    # Data rows
    row = 4
    total_metrics = {
        'scheduled_hours': 0,
        'break_minutes': 0,
        'allowed_minutes': 0,
        'exceeding': 0,
        'incidents': 0,
        'emergency': 0,
        'breaks': 0,
        'util_sum': 0,
        'adh_sum': 0,
        'conf_sum': 0,
        'count': 0
    }
    
    for agent in agents:
        metrics = calculate_agent_metrics(agent.id, start_date, end_date)
        
        # Determine status
        if metrics['incidents'] == 0 and metrics['exceeding_break_minutes'] == 0:
            status = "✅ Good"
            status_fill = good_fill
        elif metrics['incidents'] <= 2 or metrics['exceeding_break_minutes'] <= 15:
            status = "⚠️ Warning"
            status_fill = warning_fill
        else:
            status = "❌ Needs Review"
            status_fill = bad_fill
        
        row_data = [
            agent.full_name,
            agent.username,
            metrics['total_scheduled_hours'],
            metrics['total_breaks'],
            metrics['total_break_minutes'],
            metrics['total_allowed_break_minutes'],
            metrics['exceeding_break_minutes'],
            metrics['incidents'],
            metrics['emergency_count'],
            metrics['utilization'],
            metrics['adherence'],
            metrics['conformance'],
            status
        ]
        
        for col, value in enumerate(row_data, 1):
            cell = ws.cell(row=row, column=col, value=value)
            cell.alignment = cell_alignment
            cell.border = border
            if col == 13:  # Status column
                cell.fill = status_fill
        
        # Accumulate totals
        total_metrics['scheduled_hours'] += metrics['total_scheduled_hours']
        total_metrics['break_minutes'] += metrics['total_break_minutes']
        total_metrics['allowed_minutes'] += metrics['total_allowed_break_minutes']
        total_metrics['exceeding'] += metrics['exceeding_break_minutes']
        total_metrics['incidents'] += metrics['incidents']
        total_metrics['emergency'] += metrics['emergency_count']
        total_metrics['breaks'] += metrics['total_breaks']
        if metrics['shifts_count'] > 0:
            total_metrics['util_sum'] += metrics['utilization']
            total_metrics['adh_sum'] += metrics['adherence']
            total_metrics['conf_sum'] += metrics['conformance']
            total_metrics['count'] += 1
        
        row += 1
    
    # Totals/Average row
    row += 1
    total_fill = PatternFill(start_color="e0e0e0", end_color="e0e0e0", fill_type="solid")
    
    avg_util = round(total_metrics['util_sum'] / total_metrics['count'], 1) if total_metrics['count'] > 0 else 0
    avg_adh = round(total_metrics['adh_sum'] / total_metrics['count'], 1) if total_metrics['count'] > 0 else 0
    avg_conf = round(total_metrics['conf_sum'] / total_metrics['count'], 1) if total_metrics['count'] > 0 else 0
    
    totals_row = [
        "TOTAL / AVERAGE",
        f"{len(agents)} agents",
        total_metrics['scheduled_hours'],
        total_metrics['breaks'],
        total_metrics['break_minutes'],
        total_metrics['allowed_minutes'],
        total_metrics['exceeding'],
        total_metrics['incidents'],
        total_metrics['emergency'],
        avg_util,
        avg_adh,
        avg_conf,
        ""
    ]
    
    for col, value in enumerate(totals_row, 1):
        cell = ws.cell(row=row, column=col, value=value)
        cell.font = Font(bold=True)
        cell.alignment = cell_alignment
        cell.border = border
        cell.fill = total_fill
    
    # Adjust column widths
    column_widths = [20, 15, 15, 12, 15, 15, 12, 10, 10, 12, 12, 12, 15]
    for i, width in enumerate(column_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = width
    
    # Add a summary section
    row += 3
    ws.cell(row=row, column=1, value="Summary").font = Font(bold=True, size=12)
    row += 1
    ws.cell(row=row, column=1, value=f"Report Period: {start_date} to {end_date}")
    row += 1
    ws.cell(row=row, column=1, value=f"Total Agents: {len(agents)}")
    row += 1
    ws.cell(row=row, column=1, value=f"Total Incidents: {total_metrics['incidents']}")
    row += 1
    ws.cell(row=row, column=1, value=f"Total Emergency Breaks: {total_metrics['emergency']}")
    row += 1
    ws.cell(row=row, column=1, value=f"Total Exceeding Break Time: {total_metrics['exceeding']} minutes")
    row += 1
    ws.cell(row=row, column=1, value=f"Average Utilization: {avg_util}%")
    row += 1
    ws.cell(row=row, column=1, value=f"Average Adherence: {avg_adh}%")
    row += 1
    ws.cell(row=row, column=1, value=f"Average Conformance: {avg_conf}%")
    
    # Save to bytes
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    # Generate filename
    filename = f"RTA_Metrics_{start_date}_to_{end_date}.xlsx"
    
    return Response(
        output.getvalue(),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


# ==================== STARTUP ====================

def create_app():
    """Initialize database - called on startup"""
    try:
        with app.app_context():
            init_db()
    except Exception as e:
        print(f"⚠️ Warning: Database initialization failed: {e}")
        print("⚠️ App will continue, but database features may not work.")
    return app

# Initialize on import (for gunicorn)
try:
    create_app()
except Exception as e:
    print(f"⚠️ Warning: App initialization error: {e}")
    print("⚠️ App will continue, but some features may not work.")

# ==================== MAIN ====================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    print("=" * 50)
    print("RTA Break Tracker - Web Application")
    print(f"Environment: {ENV}")
    print("=" * 50)
    print(f"Open in browser: http://localhost:{port}")
    print("-" * 50)
    print("Default admin: admin / admin123")
    print("(Change password after first login!)")
    print("=" * 50)
    
    app.run(debug=DEBUG, host='0.0.0.0', port=port)

