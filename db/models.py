
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from enum import Enum
import json

db = SQLAlchemy()

class VerbosityLevel(Enum):
    VERBOSE = "verbose"
    SIMPLE = "simple"
    CASUAL = "casual"

class RequestStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    DECLINED = "declined"

class MediaType(Enum):
    MOVIE = "movie"
    TV = "tv"

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    display_name = db.Column(db.String(100))
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    verbosity_level = db.Column(db.Enum(VerbosityLevel), default=VerbosityLevel.SIMPLE)
    auto_notifications = db.Column(db.Boolean, default=True)
    daily_request_limit = db.Column(db.Integer, default=10)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    requests = db.relationship('MediaRequest', backref='user', lazy=True)
    
    def get_daily_request_count(self):
        """Get number of requests made today"""
        today = datetime.utcnow().date()
        return MediaRequest.query.filter(
            MediaRequest.user_id == self.id,
            db.func.date(MediaRequest.created_at) == today
        ).count()
    
    def can_make_request(self):
        """Check if user can make another request today"""
        return self.get_daily_request_count() < self.daily_request_limit
    
    def to_dict(self):
        return {
            'id': self.id,
            'phone_number': self.phone_number,
            'display_name': self.display_name,
            'is_admin': self.is_admin,
            'is_active': self.is_active,
            'verbosity_level': self.verbosity_level.value,
            'auto_notifications': self.auto_notifications,
            'daily_request_limit': self.daily_request_limit,
            'created_at': self.created_at.isoformat(),
            'last_active': self.last_active.isoformat(),
            'daily_requests': self.get_daily_request_count()
        }

class MediaRequest(db.Model):
    __tablename__ = 'media_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    overseerr_request_id = db.Column(db.Integer)
    media_type = db.Column(db.Enum(MediaType), nullable=False)
    media_id = db.Column(db.Integer, nullable=False)  # TMDB ID
    title = db.Column(db.String(255), nullable=False)
    year = db.Column(db.Integer)
    status = db.Column(db.Enum(RequestStatus), default=RequestStatus.PENDING)
    is_4k = db.Column(db.Boolean, default=False)
    seasons_requested = db.Column(db.Text)  # JSON array for TV shows
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)
    
    def get_seasons_requested(self):
        """Get seasons requested as list"""
        if self.seasons_requested:
            return json.loads(self.seasons_requested)
        return []
    
    def set_seasons_requested(self, seasons):
        """Set seasons requested from list"""
        self.seasons_requested = json.dumps(seasons) if seasons else None
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'overseerr_request_id': self.overseerr_request_id,
            'media_type': self.media_type.value,
            'media_id': self.media_id,
            'title': self.title,
            'year': self.year,
            'status': self.status.value,
            'is_4k': self.is_4k,
            'seasons_requested': self.get_seasons_requested(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message
        }

class Settings(db.Model):
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @classmethod
    def get_setting(cls, key, default=None):
        """Get a setting value"""
        setting = cls.query.filter_by(key=key).first()
        return setting.value if setting else default
    
    @classmethod
    def set_setting(cls, key, value, description=None):
        """Set a setting value"""
        setting = cls.query.filter_by(key=key).first()
        if setting:
            setting.value = value
            if description:
                setting.description = description
        else:
            setting = cls(key=key, value=value, description=description)
            db.session.add(setting)
        db.session.commit()
        return setting
    
    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'description': self.description,
            'updated_at': self.updated_at.isoformat()
        }

class LogEntry(db.Model):
    __tablename__ = 'log_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text, nullable=False)
    module = db.Column(db.String(100))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    request_id = db.Column(db.Integer, db.ForeignKey('media_requests.id'))
    extra_data = db.Column(db.Text)  # JSON for additional data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_metadata(self):
        """Get metadata as dict"""
        if self.extra_data:
            return json.loads(self.extra_data)
        return {}
    
    def set_metadata(self, data):
        """Set metadata from dict"""
        self.extra_data = json.dumps(data) if data else None
    
    def to_dict(self):
        return {
            'id': self.id,
            'level': self.level,
            'message': self.message,
            'module': self.module,
            'user_id': self.user_id,
            'request_id': self.request_id,
            'metadata': self.get_metadata(),
            'created_at': self.created_at.isoformat()
        }
