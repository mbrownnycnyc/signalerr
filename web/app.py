
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_cors import CORS
import logging
import os
from datetime import datetime, timedelta

from config import Config
from db.models import db, User, MediaRequest, Settings, LogEntry, VerbosityLevel, RequestStatus, MediaType
from db.crud import UserCRUD, MediaRequestCRUD, SettingsCRUD, LogCRUD
from api.overseerr import OverseerrAPI

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
CORS(app)

# Setup logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize database
with app.app_context():
    db.create_all()
    
    # Create default admin user if none exists
    if not UserCRUD.get_all_users():
        for admin_phone in Config.ADMIN_PHONE_NUMBERS:
            if admin_phone:
                UserCRUD.create_user(admin_phone, "Admin User", is_admin=True)
                logger.info(f"Created default admin user: {admin_phone}")

# Simple authentication decorator
def admin_required(f):
    def decorated_function(*args, **kwargs):
        if 'admin_authenticated' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page"""
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        
        if phone in Config.ADMIN_PHONE_NUMBERS:
            session['admin_authenticated'] = True
            session['admin_phone'] = phone
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid admin phone number', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Admin logout"""
    session.clear()
    flash('Logged out successfully', 'info')
    return redirect(url_for('login'))

@app.route('/')
@admin_required
def dashboard():
    """Main dashboard"""
    try:
        # Get statistics
        total_users = len(UserCRUD.get_all_users())
        recent_requests = MediaRequestCRUD.get_recent_requests(days=7)
        pending_requests = MediaRequestCRUD.get_requests_by_status('pending')
        completed_requests = MediaRequestCRUD.get_requests_by_status('completed')
        
        # Test Overseerr connection
        overseerr_api = OverseerrAPI(
            SettingsCRUD.get_setting('overseerr_url', Config.OVERSEERR_URL),
            SettingsCRUD.get_setting('overseerr_api_key', Config.OVERSEERR_API_KEY)
        )
        overseerr_connected = overseerr_api.test_connection()
        
        # Get recent logs
        recent_logs = LogCRUD.get_recent_logs(hours=24, limit=10)
        
        stats = {
            'total_users': total_users,
            'recent_requests': len(recent_requests),
            'pending_requests': len(pending_requests),
            'completed_requests': len(completed_requests),
            'overseerr_connected': overseerr_connected
        }
        
        return render_template('dashboard.html', stats=stats, recent_logs=recent_logs)
        
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        flash(f'Error loading dashboard: {e}', 'error')
        return render_template('dashboard.html', stats={}, recent_logs=[])

@app.route('/users')
@admin_required
def users():
    """User management page"""
    try:
        all_users = UserCRUD.get_all_users(active_only=False)
        return render_template('users.html', users=all_users)
    except Exception as e:
        logger.error(f"Users page error: {e}")
        flash(f'Error loading users: {e}', 'error')
        return render_template('users.html', users=[])

@app.route('/users/add', methods=['POST'])
@admin_required
def add_user():
    """Add new user"""
    try:
        phone = request.form.get('phone', '').strip()
        display_name = request.form.get('display_name', '').strip()
        is_admin = request.form.get('is_admin') == 'on'
        daily_limit = int(request.form.get('daily_limit', 10))
        
        if not phone:
            flash('Phone number is required', 'error')
            return redirect(url_for('users'))
        
        # Check if user already exists
        existing_user = UserCRUD.get_user_by_phone(phone)
        if existing_user:
            flash('User already exists', 'error')
            return redirect(url_for('users'))
        
        # Create user
        user = UserCRUD.create_user(phone, display_name, is_admin)
        UserCRUD.update_user(user.id, daily_request_limit=daily_limit)
        
        flash(f'User {phone} added successfully', 'success')
        
    except Exception as e:
        logger.error(f"Add user error: {e}")
        flash(f'Error adding user: {e}', 'error')
    
    return redirect(url_for('users'))

@app.route('/users/<int:user_id>/edit', methods=['POST'])
@admin_required
def edit_user(user_id):
    """Edit user"""
    try:
        display_name = request.form.get('display_name', '').strip()
        is_admin = request.form.get('is_admin') == 'on'
        is_active = request.form.get('is_active') == 'on'
        daily_limit = int(request.form.get('daily_limit', 10))
        verbosity = request.form.get('verbosity', 'simple')
        auto_notifications = request.form.get('auto_notifications') == 'on'
        
        UserCRUD.update_user(
            user_id,
            display_name=display_name,
            is_admin=is_admin,
            is_active=is_active,
            daily_request_limit=daily_limit,
            verbosity_level=VerbosityLevel(verbosity),
            auto_notifications=auto_notifications
        )
        
        flash('User updated successfully', 'success')
        
    except Exception as e:
        logger.error(f"Edit user error: {e}")
        flash(f'Error updating user: {e}', 'error')
    
    return redirect(url_for('users'))

@app.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Delete (deactivate) user"""
    try:
        user = UserCRUD.get_user_by_id(user_id)
        if user:
            UserCRUD.delete_user(user_id)
            flash(f'User {user.phone_number} deactivated', 'success')
        else:
            flash('User not found', 'error')
            
    except Exception as e:
        logger.error(f"Delete user error: {e}")
        flash(f'Error deleting user: {e}', 'error')
    
    return redirect(url_for('users'))

@app.route('/requests')
@admin_required
def requests():
    """Requests management page"""
    try:
        status_filter = request.args.get('status', '')
        page = int(request.args.get('page', 1))
        per_page = 20
        
        # Get requests with pagination
        if status_filter:
            all_requests = MediaRequestCRUD.get_requests_by_status(status_filter)
        else:
            all_requests = MediaRequestCRUD.get_recent_requests(days=30, limit=100)
        
        # Simple pagination
        start = (page - 1) * per_page
        end = start + per_page
        requests_page = all_requests[start:end]
        
        # Get users for display
        user_map = {user.id: user for user in UserCRUD.get_all_users(active_only=False)}
        
        return render_template('requests.html', 
                             requests=requests_page, 
                             user_map=user_map,
                             status_filter=status_filter,
                             page=page,
                             has_next=end < len(all_requests))
        
    except Exception as e:
        logger.error(f"Requests page error: {e}")
        flash(f'Error loading requests: {e}', 'error')
        return render_template('requests.html', requests=[], user_map={})

@app.route('/requests/<int:request_id>/update_status', methods=['POST'])
@admin_required
def update_request_status(request_id):
    """Update request status"""
    try:
        new_status = request.form.get('status')
        error_message = request.form.get('error_message', '').strip()
        
        if new_status:
            MediaRequestCRUD.update_request_status(
                request_id, 
                new_status, 
                error_message=error_message if error_message else None
            )
            flash('Request status updated', 'success')
        else:
            flash('Invalid status', 'error')
            
    except Exception as e:
        logger.error(f"Update request status error: {e}")
        flash(f'Error updating request: {e}', 'error')
    
    return redirect(url_for('requests'))

@app.route('/settings')
@admin_required
def settings():
    """Settings page"""
    try:
        all_settings = SettingsCRUD.get_all_settings()
        settings_dict = {setting.key: setting for setting in all_settings}
        
        return render_template('settings.html', settings=settings_dict)
        
    except Exception as e:
        logger.error(f"Settings page error: {e}")
        flash(f'Error loading settings: {e}', 'error')
        return render_template('settings.html', settings={})

@app.route('/settings/update', methods=['POST'])
@admin_required
def update_settings():
    """Update settings"""
    try:
        settings_to_update = {}
        
        # Get all form data
        for key, value in request.form.items():
            if key.startswith('setting_'):
                setting_key = key.replace('setting_', '')
                settings_to_update[setting_key] = value
        
        # Update settings
        SettingsCRUD.update_multiple_settings(settings_to_update)
        
        flash('Settings updated successfully', 'success')
        
    except Exception as e:
        logger.error(f"Update settings error: {e}")
        flash(f'Error updating settings: {e}', 'error')
    
    return redirect(url_for('settings'))

@app.route('/logs')
@admin_required
def logs():
    """Logs page"""
    try:
        level_filter = request.args.get('level', '')
        module_filter = request.args.get('module', '')
        page = int(request.args.get('page', 1))
        per_page = 50
        
        offset = (page - 1) * per_page
        
        logs = LogCRUD.get_logs(
            level=level_filter if level_filter else None,
            module=module_filter if module_filter else None,
            limit=per_page,
            offset=offset
        )
        
        return render_template('logs.html', 
                             logs=logs,
                             level_filter=level_filter,
                             module_filter=module_filter,
                             page=page,
                             has_next=len(logs) == per_page)
        
    except Exception as e:
        logger.error(f"Logs page error: {e}")
        flash(f'Error loading logs: {e}', 'error')
        return render_template('logs.html', logs=[])

@app.route('/api/test_overseerr', methods=['POST'])
@admin_required
def test_overseerr():
    """Test Overseerr connection"""
    try:
        data = request.get_json()
        url = data.get('url', '')
        api_key = data.get('api_key', '')
        
        if not url or not api_key:
            return jsonify({'success': False, 'message': 'URL and API key required'})
        
        overseerr_api = OverseerrAPI(url, api_key)
        connected = overseerr_api.test_connection()
        
        if connected:
            return jsonify({'success': True, 'message': 'Connection successful'})
        else:
            return jsonify({'success': False, 'message': 'Connection failed'})
            
    except Exception as e:
        logger.error(f"Test Overseerr error: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/stats')
@admin_required
def api_stats():
    """API endpoint for dashboard stats"""
    try:
        total_users = len(UserCRUD.get_all_users())
        recent_requests = MediaRequestCRUD.get_recent_requests(days=1)
        pending_requests = MediaRequestCRUD.get_requests_by_status('pending')
        
        return jsonify({
            'total_users': total_users,
            'requests_today': len(recent_requests),
            'pending_requests': len(pending_requests)
        })
        
    except Exception as e:
        logger.error(f"API stats error: {e}")
        return jsonify({'error': str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', error='Page not found'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error='Internal server error'), 500

if __name__ == '__main__':
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
