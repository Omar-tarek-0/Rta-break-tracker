"""
RTA Break Tracker - Web Application
Flask-based web app for tracking agent breaks
"""
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, Response
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import not_
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

# Break types that count as working time (meetings/coaching)
WORKING_TIME_BREAKS = ['coaching_aya', 'coaching_mostafa', 'meeting_team_leader']
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
    
    def is_working_time_break(self):
        """Check if this break counts as working time (coaching/meetings)"""
        return self.break_type in WORKING_TIME_BREAKS
    
    def get_effective_overdue_status(self):
        """Get overdue status, but always False for working time breaks"""
        if self.is_working_time_break():
            return False
        return self.is_overdue
    
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
            'is_overdue': self.get_effective_overdue_status(),  # Use effective status (excludes working time breaks)
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
    
    # Get active break for this agent (exclude punch_in/punch_out as they're auto-completed)
    active_break = BreakRecord.query.filter(
        BreakRecord.agent_id == current_user.id,
        BreakRecord.end_time == None,
        not_(BreakRecord.break_type.in_(['punch_in', 'punch_out']))
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
    
    # Group by agent
    agents_data = {}
    for br in breaks:
        if br.agent_id not in agents_data:
            agents_data[br.agent_id] = {
                'agent_name': br.agent.full_name,
                'breaks': []
            }
        agents_data[br.agent_id]['breaks'].append(br.to_dict())
    
    return jsonify({
        'agents': list(agents_data.values()),
        'total_breaks': len(breaks)
    })


@app.route('/api/break/start', methods=['POST'])
@login_required
def start_break():
    """Start a new break"""
    if current_user.is_rtm():
        return jsonify({'error': 'RTM cannot take breaks'}), 403
    
    # Check for active break (exclude punch_in/punch_out as they're auto-completed instantly)
    active = BreakRecord.query.filter(
        BreakRecord.agent_id == current_user.id,
        BreakRecord.end_time == None,
        not_(BreakRecord.break_type.in_(['punch_in', 'punch_out']))
    ).first()
    if active:
        return jsonify({'error': 'You already have an active break'}), 400
    
    break_type = request.form.get('break_type')
    screenshot = request.files.get('screenshot')
    
    if not break_type or break_type not in BREAK_DURATIONS:
        return jsonify({'error': 'Invalid break type'}), 400
    
    # Require punch_in before other breaks (except punch_in itself)
    if break_type != 'punch_in':
        today = get_local_time().date()
        punch_in = BreakRecord.query.filter(
            BreakRecord.agent_id == current_user.id,
            BreakRecord.break_type == 'punch_in',
            db.func.date(BreakRecord.start_time) == today
        ).first()
        
        if not punch_in:
            return jsonify({
                'error': 'You must punch in first before taking any breaks. Please punch in to continue.'
            }), 400
    
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
    
    # Auto-complete punch_in and punch_out instantly
    if break_type in ['punch_in', 'punch_out']:
        break_record.end_time = break_record.start_time
        break_record.end_screenshot = screenshot_path
        break_record.duration_minutes = 0
        break_record.is_overdue = False
        
        # Prevent duplicate punch records for the same day
        if break_type == 'punch_in':
            today = get_local_time().date()
            existing = BreakRecord.query.filter(
                BreakRecord.agent_id == current_user.id,
                BreakRecord.break_type == 'punch_in',
                db.func.date(BreakRecord.start_time) == today
            ).first()
            if existing:
                return jsonify({'error': 'You have already punched in today'}), 400
        elif break_type == 'punch_out':
            today = get_local_time().date()
            existing = BreakRecord.query.filter(
                BreakRecord.agent_id == current_user.id,
                BreakRecord.break_type == 'punch_out',
                db.func.date(BreakRecord.start_time) == today
            ).first()
            if existing:
                return jsonify({'error': 'You have already punched out today'}), 400
    
    db.session.add(break_record)
    db.session.commit()
    
    if break_type in ['punch_in', 'punch_out']:
        action = "Punched in" if break_type == 'punch_in' else "Punched out"
        return jsonify({
            'success': True,
            'message': f'{action} successfully! ✅',
            'break': break_record.to_dict()
        })
    
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
    
    # Get active break (exclude punch_in/punch_out as they're auto-completed instantly)
    active = BreakRecord.query.filter(
        BreakRecord.agent_id == current_user.id,
        BreakRecord.end_time == None,
        not_(BreakRecord.break_type.in_(['punch_in', 'punch_out']))
    ).first()
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
    
    # Working time breaks (coaching/meetings) should never be marked as overdue
    # They count as working time regardless of duration
    if active.break_type in WORKING_TIME_BREAKS:
        active.is_overdue = False
    else:
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


@app.route('/api/fix/working-time-breaks', methods=['POST'])
@login_required
def fix_working_time_breaks_endpoint():
    """Manual fix endpoint to clear is_overdue for working time breaks"""
    if not current_user.is_rtm():
        return jsonify({'error': 'Unauthorized'}), 403
    
    fixed_count = fix_existing_working_time_breaks()
    
    return jsonify({
        'success': True,
        'message': f'Fixed {fixed_count} working time breaks',
        'fixed_count': fixed_count
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
    
    start_date = request.args.get('start_date', get_local_time().strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', start_date)
    agent_id = request.args.get('agent_id', '')
    
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
    
    # Separate breaks into working time breaks and regular breaks
    working_time_breaks = [b for b in breaks if b.break_type in WORKING_TIME_BREAKS and b.end_time]
    regular_breaks = [b for b in breaks if b.break_type not in WORKING_TIME_BREAKS + ['punch_in', 'punch_out'] and b.end_time]
    
    # Total break minutes (excluding working time breaks and punch records)
    total_break_minutes = sum(b.duration_minutes or 0 for b in regular_breaks)
    total_allowed_break_minutes = sum(b.get_allowed_duration() for b in regular_breaks)
    exceeding_break_minutes = max(0, total_break_minutes - total_allowed_break_minutes)
    
    # Count incidents (overdue breaks) - only for regular breaks
    # Use effective overdue status (working time breaks are never overdue)
    incidents = sum(1 for b in regular_breaks if b.get_effective_overdue_status())
    
    # Count emergency breaks
    emergency_count = sum(1 for b in breaks if b.break_type == 'emergency')
    
    # Count breaks by type
    break_counts = {}
    for b in breaks:
        break_counts[b.break_type] = break_counts.get(b.break_type, 0) + 1
    
    # Calculate utilization
    # Working time breaks (coaching/meetings) count as working time, not breaks
    # Time worked = scheduled time - regular break time taken
    if total_scheduled_minutes > 0:
        time_worked = total_scheduled_minutes - total_break_minutes
        utilization = (time_worked / total_scheduled_minutes) * 100
        utilization = min(100.0, utilization)  # Cap at 100%
    else:
        utilization = 0
    
    # Calculate adherence based on:
    # 1. Break durations (actual vs allowed)
    # 2. Punch in time vs shift start time
    # 3. Punch out time vs shift end time
    
    adherence_scores = []
    
    # 1. Break duration adherence (only for regular breaks)
    total_completed_breaks = len([b for b in regular_breaks if b.end_time])
    
    if total_completed_breaks > 0:
        for b in regular_breaks:
            if b.end_time and b.duration_minutes is not None:
                allowed_duration = b.get_allowed_duration()
                if allowed_duration > 0:
                    actual_duration = b.duration_minutes
                    if actual_duration <= allowed_duration:
                        break_adherence = 100.0
                    else:
                        break_adherence = (allowed_duration / actual_duration) * 100
                    adherence_scores.append(break_adherence)
    
    # 2. Punch in/out adherence based on shift times
    # Group shifts by date for easier lookup
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
        
        # Punch in adherence
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
                # Formula: max(0, (30 - time_diff) / 30 * 100)
                punch_in_adherence = max(0, (30 - time_diff_minutes) / 30 * 100)
            adherence_scores.append(punch_in_adherence)
        else:
            # No punch in = 0% adherence for that day
            adherence_scores.append(0.0)
        
        # Punch out adherence
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
                # Max penalty at 30 minutes = 0% adherence
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
    
    # Conformance (similar to adherence but measures schedule following)
    # For simplicity: conformance = did agent have shifts and follow them
    if len(shifts) > 0:
        conformance = adherence  # Using same logic for now
    else:
        conformance = 0  # No shifts assigned = 0% conformance
    
    return {
        'total_scheduled_hours': round(total_scheduled_minutes / 60, 2),
        'total_break_minutes': total_break_minutes,
        'total_allowed_break_minutes': total_allowed_break_minutes,
        'exceeding_break_minutes': exceeding_break_minutes,
        'incidents': incidents,
        'emergency_count': emergency_count,
        'total_breaks': len(breaks),
        'completed_breaks': total_completed_breaks,
        'utilization': round(utilization, 1),
        'adherence': round(adherence, 1),
        'conformance': round(conformance, 1),
        'break_counts': break_counts,
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

def fix_existing_working_time_breaks():
    """One-time fix: Clear is_overdue flag for existing working time breaks"""
    try:
        # Check if BreakRecord table exists
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        if 'break_record' not in [table.name for table in inspector.get_table_names()]:
            print("⚠️ Database tables not initialized yet, skipping fix")
            return 0
        
        working_time_breaks = BreakRecord.query.filter(
            BreakRecord.break_type.in_(WORKING_TIME_BREAKS),
            BreakRecord.is_overdue == True
        ).all()
        
        if working_time_breaks:
            for br in working_time_breaks:
                br.is_overdue = False
            db.session.commit()
            print(f"✅ Fixed {len(working_time_breaks)} working time breaks that were incorrectly marked as overdue")
        return len(working_time_breaks)
    except Exception as e:
        print(f"⚠️ Error fixing working time breaks: {e}")
        import traceback
        traceback.print_exc()
        return 0

def create_app():
    """Initialize database - called on startup"""
    with app.app_context():
        init_db()
        # Fix any existing working time breaks that were incorrectly marked as overdue
        fix_existing_working_time_breaks()
    return app

# Initialize on import (for gunicorn)
create_app()

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

