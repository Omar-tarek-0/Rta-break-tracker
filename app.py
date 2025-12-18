"""
RTA Break Tracker - Web Application
Flask-based web app for tracking agent breaks
"""
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from pathlib import Path
import bcrypt
import os
import uuid

from config import (
    SECRET_KEY, SQLALCHEMY_DATABASE_URI, UPLOAD_FOLDER, 
    ALLOWED_EXTENSIONS, BREAK_DURATIONS, BREAK_INFO,
    ROLE_AGENT, ROLE_RTM, DEFAULT_USERS, DEBUG, ENV, TIMEZONE
)
import pytz

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
    break_type = db.Column(db.String(50), nullable=False)
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
    
    return render_template('agent.html',
        user=current_user,
        active_break=active_break,
        today_breaks=today_breaks,
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


@app.route('/api/shift/create', methods=['POST'])
@login_required
def create_shift():
    """Create a new shift"""
    if not current_user.is_rtm():
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    agent_id = data.get('agent_id')
    shift_date = data.get('shift_date')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    
    if not all([agent_id, shift_date, start_time, end_time]):
        return jsonify({'error': 'All fields are required'}), 400
    
    # Verify agent exists
    agent = User.query.filter_by(id=agent_id, role=ROLE_AGENT).first()
    if not agent:
        return jsonify({'error': 'Agent not found'}), 404
    
    try:
        shift_date_obj = datetime.strptime(shift_date, '%Y-%m-%d').date()
        start_time_obj = datetime.strptime(start_time, '%H:%M').time()
        end_time_obj = datetime.strptime(end_time, '%H:%M').time()
    except ValueError:
        return jsonify({'error': 'Invalid date or time format'}), 400
    
    # Check if shift already exists for this agent on this date
    existing = Shift.query.filter_by(agent_id=agent_id, shift_date=shift_date_obj).first()
    if existing:
        # Update existing shift
        existing.start_time = start_time_obj
        existing.end_time = end_time_obj
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Shift updated',
            'shift': existing.to_dict()
        })
    
    # Create new shift
    shift = Shift(
        agent_id=agent_id,
        shift_date=shift_date_obj,
        start_time=start_time_obj,
        end_time=end_time_obj,
        created_by=current_user.id
    )
    db.session.add(shift)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Shift created',
        'shift': shift.to_dict()
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


@app.route('/api/shift/bulk', methods=['POST'])
@login_required
def create_bulk_shifts():
    """Create shifts for multiple agents at once"""
    if not current_user.is_rtm():
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    agent_ids = data.get('agent_ids', [])
    shift_date = data.get('shift_date')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    
    if not all([agent_ids, shift_date, start_time, end_time]):
        return jsonify({'error': 'All fields are required'}), 400
    
    try:
        shift_date_obj = datetime.strptime(shift_date, '%Y-%m-%d').date()
        start_time_obj = datetime.strptime(start_time, '%H:%M').time()
        end_time_obj = datetime.strptime(end_time, '%H:%M').time()
    except ValueError:
        return jsonify({'error': 'Invalid date or time format'}), 400
    
    created = 0
    updated = 0
    
    for agent_id in agent_ids:
        agent = User.query.filter_by(id=agent_id, role=ROLE_AGENT).first()
        if not agent:
            continue
        
        existing = Shift.query.filter_by(agent_id=agent_id, shift_date=shift_date_obj).first()
        if existing:
            existing.start_time = start_time_obj
            existing.end_time = end_time_obj
            updated += 1
        else:
            shift = Shift(
                agent_id=agent_id,
                shift_date=shift_date_obj,
                start_time=start_time_obj,
                end_time=end_time_obj,
                created_by=current_user.id
            )
            db.session.add(shift)
            created += 1
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Created {created} shifts, updated {updated} shifts'
    })


# ==================== STARTUP ====================

def create_app():
    """Initialize database - called on startup"""
    with app.app_context():
        init_db()
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

