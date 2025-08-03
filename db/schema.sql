
-- Signalerr Database Schema
-- SQLite database for user management, requests, settings, and logging

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    display_name VARCHAR(100),
    is_admin BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    verbosity_level VARCHAR(20) DEFAULT 'simple',
    auto_notifications BOOLEAN DEFAULT TRUE,
    daily_request_limit INTEGER DEFAULT 10,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_active DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Media requests table
CREATE TABLE IF NOT EXISTS media_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    overseerr_request_id INTEGER,
    media_type VARCHAR(10) NOT NULL,
    media_id INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    year INTEGER,
    status VARCHAR(20) DEFAULT 'pending',
    is_4k BOOLEAN DEFAULT FALSE,
    seasons_requested TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    error_message TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- Settings table
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT,
    description TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Log entries table
CREATE TABLE IF NOT EXISTS log_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    module VARCHAR(100),
    user_id INTEGER,
    request_id INTEGER,
    extra_data TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (request_id) REFERENCES media_requests (id)
);

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_phone_number ON users(phone_number);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);
CREATE INDEX IF NOT EXISTS idx_media_requests_user_id ON media_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_media_requests_status ON media_requests(status);
CREATE INDEX IF NOT EXISTS idx_media_requests_created_at ON media_requests(created_at);
CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(key);
CREATE INDEX IF NOT EXISTS idx_log_entries_level ON log_entries(level);
CREATE INDEX IF NOT EXISTS idx_log_entries_created_at ON log_entries(created_at);

-- Insert default settings
INSERT OR IGNORE INTO settings (key, value, description) VALUES
('overseerr_url', 'http://localhost:5055', 'Overseerr server URL'),
('overseerr_api_key', '', 'Overseerr API key for authentication'),
('request_timeout_minutes', '2', 'Minutes to wait before checking request status'),
('max_requests_per_user_per_day', '10', 'Maximum requests per user per day'),
('default_verbosity', 'simple', 'Default verbosity level for new users'),
('enable_group_chats', 'true', 'Enable group chat functionality'),
('enable_auto_notifications', 'true', 'Enable automatic download completion notifications'),
('admin_phone_numbers', '', 'Comma-separated list of admin phone numbers'),
('bot_enabled', 'true', 'Enable/disable the bot'),
('maintenance_mode', 'false', 'Enable maintenance mode');
