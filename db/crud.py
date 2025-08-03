
from db.models import db, User, MediaRequest, Settings, LogEntry, VerbosityLevel, RequestStatus, MediaType
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
import logging

logger = logging.getLogger(__name__)

class UserCRUD:
    @staticmethod
    def create_user(phone_number, display_name=None, is_admin=False):
        """Create a new user"""
        try:
            user = User(
                phone_number=phone_number,
                display_name=display_name,
                is_admin=is_admin
            )
            db.session.add(user)
            db.session.commit()
            logger.info(f"Created user: {phone_number}")
            return user
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating user {phone_number}: {e}")
            raise
    
    @staticmethod
    def get_user_by_phone(phone_number):
        """Get user by phone number"""
        return User.query.filter_by(phone_number=phone_number).first()
    
    @staticmethod
    def get_user_by_id(user_id):
        """Get user by ID"""
        return User.query.get(user_id)
    
    @staticmethod
    def get_all_users(active_only=True):
        """Get all users"""
        query = User.query
        if active_only:
            query = query.filter_by(is_active=True)
        return query.all()
    
    @staticmethod
    def update_user(user_id, **kwargs):
        """Update user"""
        try:
            user = User.query.get(user_id)
            if not user:
                return None
            
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            
            user.last_active = datetime.utcnow()
            db.session.commit()
            logger.info(f"Updated user {user.phone_number}")
            return user
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating user {user_id}: {e}")
            raise
    
    @staticmethod
    def delete_user(user_id):
        """Delete user (soft delete by setting inactive)"""
        try:
            user = User.query.get(user_id)
            if not user:
                return False
            
            user.is_active = False
            db.session.commit()
            logger.info(f"Deactivated user {user.phone_number}")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deactivating user {user_id}: {e}")
            raise

class MediaRequestCRUD:
    @staticmethod
    def create_request(user_id, media_type, media_id, title, year=None, is_4k=False, seasons=None):
        """Create a new media request"""
        try:
            request = MediaRequest(
                user_id=user_id,
                media_type=MediaType(media_type),
                media_id=media_id,
                title=title,
                year=year,
                is_4k=is_4k
            )
            
            if seasons:
                request.set_seasons_requested(seasons)
            
            db.session.add(request)
            db.session.commit()
            logger.info(f"Created request: {title} for user {user_id}")
            return request
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating request {title}: {e}")
            raise
    
    @staticmethod
    def get_request_by_id(request_id):
        """Get request by ID"""
        return MediaRequest.query.get(request_id)
    
    @staticmethod
    def get_user_requests(user_id, status=None, limit=None):
        """Get requests for a user"""
        query = MediaRequest.query.filter_by(user_id=user_id)
        
        if status:
            query = query.filter_by(status=RequestStatus(status))
        
        query = query.order_by(MediaRequest.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @staticmethod
    def get_pending_requests():
        """Get all pending requests"""
        return MediaRequest.query.filter(
            MediaRequest.status.in_([RequestStatus.PENDING, RequestStatus.APPROVED, RequestStatus.DOWNLOADING])
        ).all()
    
    @staticmethod
    def update_request_status(request_id, status, overseerr_request_id=None, error_message=None):
        """Update request status"""
        try:
            request = MediaRequest.query.get(request_id)
            if not request:
                return None
            
            request.status = RequestStatus(status)
            request.updated_at = datetime.utcnow()
            
            if overseerr_request_id:
                request.overseerr_request_id = overseerr_request_id
            
            if error_message:
                request.error_message = error_message
            
            if status == 'completed':
                request.completed_at = datetime.utcnow()
            
            db.session.commit()
            logger.info(f"Updated request {request_id} status to {status}")
            return request
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating request {request_id}: {e}")
            raise
    
    @staticmethod
    def get_requests_by_status(status):
        """Get requests by status"""
        return MediaRequest.query.filter_by(status=RequestStatus(status)).all()
    
    @staticmethod
    def get_recent_requests(days=7, limit=50):
        """Get recent requests"""
        since = datetime.utcnow() - timedelta(days=days)
        return MediaRequest.query.filter(
            MediaRequest.created_at >= since
        ).order_by(MediaRequest.created_at.desc()).limit(limit).all()

class SettingsCRUD:
    @staticmethod
    def get_setting(key, default=None):
        """Get setting value"""
        return Settings.get_setting(key, default)
    
    @staticmethod
    def set_setting(key, value, description=None):
        """Set setting value"""
        return Settings.set_setting(key, value, description)
    
    @staticmethod
    def get_all_settings():
        """Get all settings"""
        return Settings.query.all()
    
    @staticmethod
    def update_multiple_settings(settings_dict):
        """Update multiple settings at once"""
        try:
            for key, value in settings_dict.items():
                Settings.set_setting(key, str(value))
            logger.info(f"Updated {len(settings_dict)} settings")
            return True
        except Exception as e:
            logger.error(f"Error updating settings: {e}")
            raise

class LogCRUD:
    @staticmethod
    def create_log(level, message, module=None, user_id=None, request_id=None, metadata=None):
        """Create a log entry"""
        try:
            log_entry = LogEntry(
                level=level.upper(),
                message=message,
                module=module,
                user_id=user_id,
                request_id=request_id
            )
            
            if metadata:
                log_entry.set_metadata(metadata)
            
            db.session.add(log_entry)
            db.session.commit()
            return log_entry
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating log entry: {e}")
            raise
    
    @staticmethod
    def get_logs(level=None, module=None, user_id=None, limit=100, offset=0):
        """Get log entries with filters"""
        query = LogEntry.query
        
        if level:
            query = query.filter_by(level=level.upper())
        
        if module:
            query = query.filter_by(module=module)
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        return query.order_by(LogEntry.created_at.desc()).offset(offset).limit(limit).all()
    
    @staticmethod
    def get_recent_logs(hours=24, limit=100):
        """Get recent log entries"""
        since = datetime.utcnow() - timedelta(hours=hours)
        return LogEntry.query.filter(
            LogEntry.created_at >= since
        ).order_by(LogEntry.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def cleanup_old_logs(days=30):
        """Clean up old log entries"""
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            deleted = LogEntry.query.filter(LogEntry.created_at < cutoff).delete()
            db.session.commit()
            logger.info(f"Cleaned up {deleted} old log entries")
            return deleted
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error cleaning up logs: {e}")
            raise
