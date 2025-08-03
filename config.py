
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Overseerr Configuration
    OVERSEERR_URL = os.getenv('OVERSEERR_URL', 'http://localhost:5055')
    OVERSEERR_API_KEY = os.getenv('OVERSEERR_API_KEY', '')
    
    # Signal Configuration
    SIGNAL_CLI_PATH = os.getenv('SIGNAL_CLI_PATH', '/usr/local/bin/signal-cli')
    SIGNAL_PHONE_NUMBER = os.getenv('SIGNAL_PHONE_NUMBER', '')
    SIGNAL_CLI_CONFIG_DIR = os.getenv('SIGNAL_CLI_CONFIG_DIR', '/home/signal/.local/share/signal-cli')
    
    # Database Configuration
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///signalerr.db')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Flask Configuration
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    PORT = int(os.getenv('FLASK_PORT', 8080))
    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    
    # Admin Configuration
    ADMIN_PHONE_NUMBERS = [
        num.strip() for num in os.getenv('ADMIN_PHONE_NUMBERS', '').split(',') 
        if num.strip()
    ]
    
    # Bot Configuration
    REQUEST_TIMEOUT_MINUTES = int(os.getenv('REQUEST_TIMEOUT_MINUTES', 2))
    MAX_REQUESTS_PER_USER_PER_DAY = int(os.getenv('MAX_REQUESTS_PER_USER_PER_DAY', 10))
    DEFAULT_VERBOSITY = os.getenv('DEFAULT_VERBOSITY', 'simple')
    ENABLE_GROUP_CHATS = os.getenv('ENABLE_GROUP_CHATS', 'true').lower() == 'true'
    ENABLE_AUTO_NOTIFICATIONS = os.getenv('ENABLE_AUTO_NOTIFICATIONS', 'true').lower() == 'true'
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', '/app/logs/signalerr.log')
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        required_fields = [
            ('OVERSEERR_URL', cls.OVERSEERR_URL),
            ('OVERSEERR_API_KEY', cls.OVERSEERR_API_KEY),
            ('SIGNAL_PHONE_NUMBER', cls.SIGNAL_PHONE_NUMBER),
        ]
        
        missing = [field for field, value in required_fields if not value]
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
        
        return True
