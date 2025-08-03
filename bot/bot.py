
import logging
import time
import threading
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger

from config import Config
from db.models import db, VerbosityLevel, RequestStatus
from db.crud import UserCRUD, MediaRequestCRUD, SettingsCRUD, LogCRUD
from api.overseerr import OverseerrAPI
from bot.signal_client import SignalClient, SignalMessage
from bot.message_handler import MessageHandler

logger = logging.getLogger(__name__)

class SignalerrBot:
    def __init__(self):
        self.config = Config()
        self.signal_client = None
        self.overseerr_api = None
        self.message_handler = None
        self.scheduler = BackgroundScheduler()
        self.is_running = False
        
    def initialize(self):
        """Initialize bot components"""
        try:
            # Validate configuration
            self.config.validate()
            
            # Initialize Overseerr API
            self.overseerr_api = OverseerrAPI(
                self.config.OVERSEERR_URL,
                self.config.OVERSEERR_API_KEY
            )
            
            # Test Overseerr connection
            if not self.overseerr_api.test_connection():
                logger.error("Failed to connect to Overseerr API")
                return False
            
            # Initialize Signal client
            self.signal_client = SignalClient(
                self.config.SIGNAL_PHONE_NUMBER,
                self.config.SIGNAL_CLI_PATH,
                self.config.SIGNAL_CLI_CONFIG_DIR
            )
            
            # Check Signal registration
            if not self.signal_client.is_registered():
                logger.error("Signal phone number is not registered")
                return False
            
            # Initialize message handler
            self.message_handler = MessageHandler(self.signal_client, self.overseerr_api)
            
            # Add message handler to signal client
            self.signal_client.add_message_handler(self.message_handler.handle_message)
            
            # Schedule periodic tasks
            self.setup_scheduler()
            
            logger.info("Bot initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            return False
    
    def setup_scheduler(self):
        """Setup scheduled tasks"""
        # Check request statuses every 30 seconds
        self.scheduler.add_job(
            func=self.check_request_statuses,
            trigger=IntervalTrigger(seconds=30),
            id='check_request_statuses',
            name='Check Request Statuses'
        )
        
        # Clean up old logs daily
        self.scheduler.add_job(
            func=self.cleanup_old_logs,
            trigger=IntervalTrigger(hours=24),
            id='cleanup_logs',
            name='Cleanup Old Logs'
        )
        
        # Send daily stats to admins
        self.scheduler.add_job(
            func=self.send_daily_stats,
            trigger=IntervalTrigger(hours=24),
            id='daily_stats',
            name='Daily Stats'
        )
    
    def start(self):
        """Start the bot"""
        if self.is_running:
            logger.warning("Bot is already running")
            return
        
        try:
            # Start scheduler
            self.scheduler.start()
            
            # Start Signal client
            if not self.signal_client.start_listening():
                logger.error("Failed to start Signal client")
                return False
            
            self.is_running = True
            logger.info("Signalerr bot started successfully")
            
            # Send startup notification to admins
            self.notify_admins("🤖 Signalerr bot has started successfully!")
            
            # Keep the main thread alive
            try:
                while self.is_running:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Received shutdown signal")
                self.stop()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            self.stop()
            return False
    
    def stop(self):
        """Stop the bot"""
        if not self.is_running:
            return
        
        logger.info("Stopping Signalerr bot...")
        
        try:
            # Stop Signal client
            if self.signal_client:
                self.signal_client.stop_listening()
            
            # Stop scheduler
            if self.scheduler.running:
                self.scheduler.shutdown(wait=False)
            
            self.is_running = False
            
            # Send shutdown notification to admins
            self.notify_admins("🤖 Signalerr bot has been stopped.")
            
            logger.info("Bot stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")
    
    def check_request_statuses(self):
        """Check status of pending requests"""
        try:
            pending_requests = MediaRequestCRUD.get_pending_requests()
            
            for request in pending_requests:
                try:
                    # Skip if request was just created (wait for timeout)
                    if request.status == RequestStatus.PENDING:
                        timeout_minutes = int(SettingsCRUD.get_setting('request_timeout_minutes', '2'))
                        if datetime.utcnow() - request.created_at < timedelta(minutes=timeout_minutes):
                            continue
                    
                    # Get status from Overseerr
                    if request.overseerr_request_id:
                        overseerr_status = self.overseerr_api.get_request_status(request.overseerr_request_id)
                        
                        if overseerr_status:
                            new_status = self.map_overseerr_status(overseerr_status.get('status', 1))
                            
                            if new_status != request.status.value:
                                # Update status
                                MediaRequestCRUD.update_request_status(request.id, new_status)
                                
                                # Notify user if they have auto notifications enabled
                                user = UserCRUD.get_user_by_id(request.user_id)
                                if user and user.auto_notifications:
                                    self.send_status_update(user, request, new_status)
                    
                except Exception as e:
                    logger.error(f"Error checking status for request {request.id}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in check_request_statuses: {e}")
    
    def map_overseerr_status(self, overseerr_status: int) -> str:
        """Map Overseerr status codes to our status enum"""
        status_map = {
            1: 'pending',      # Pending approval
            2: 'approved',     # Approved
            3: 'declined',     # Declined
            4: 'downloading',  # Processing
            5: 'completed'     # Available
        }
        return status_map.get(overseerr_status, 'pending')
    
    def send_status_update(self, user, request, new_status):
        """Send status update to user"""
        try:
            message = self.format_status_message(user, request, new_status)
            self.signal_client.send_message(user.phone_number, message)
            
            LogCRUD.create_log(
                level='INFO',
                message=f"Sent status update to {user.phone_number}",
                module='bot',
                user_id=user.id,
                request_id=request.id
            )
            
        except Exception as e:
            logger.error(f"Failed to send status update to {user.phone_number}: {e}")
    
    def format_status_message(self, user, request, status):
        """Format status update message based on user's verbosity level"""
        title = request.title
        
        if user.verbosity_level == VerbosityLevel.CASUAL:
            if status == 'downloading':
                return f"📥 '{title}' is downloadin' now!"
            elif status == 'completed':
                return f"🎉 '{title}' is done downloadin'! Enjoy!"
            elif status == 'declined':
                return f"😞 '{title}' got declined, sorry!"
            elif status == 'failed':
                return f"💥 '{title}' failed to download."
        
        elif user.verbosity_level == VerbosityLevel.SIMPLE:
            if status == 'downloading':
                return f"⬇️ {title} - Download started"
            elif status == 'completed':
                return f"✅ {title} - Download completed!"
            elif status == 'declined':
                return f"❌ {title} - Request declined"
            elif status == 'failed':
                return f"❌ {title} - Download failed"
        
        else:  # VERBOSE
            status_text = status.replace('_', ' ').title()
            message = f"📊 **Status Update**\n\n"
            message += f"🎬 **Title:** {title}\n"
            message += f"🔄 **Status:** {status_text}\n"
            message += f"⏰ **Updated:** {datetime.utcnow().strftime('%H:%M')}\n"
            
            if status == 'completed':
                message += f"🎉 **Ready to watch!**"
            elif status == 'downloading':
                message += f"📥 **Download in progress...**"
            
            return message
        
        return f"Status update: {title} - {status}"
    
    def cleanup_old_logs(self):
        """Clean up old log entries"""
        try:
            days_to_keep = int(SettingsCRUD.get_setting('log_retention_days', '30'))
            deleted_count = LogCRUD.cleanup_old_logs(days_to_keep)
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old log entries")
                
        except Exception as e:
            logger.error(f"Error cleaning up logs: {e}")
    
    def send_daily_stats(self):
        """Send daily statistics to admins"""
        try:
            # Get statistics
            total_users = len(UserCRUD.get_all_users())
            recent_requests = MediaRequestCRUD.get_recent_requests(days=1)
            pending_requests = MediaRequestCRUD.get_requests_by_status('pending')
            
            message = f"📊 **Daily Signalerr Stats**\n\n"
            message += f"👥 Active Users: {total_users}\n"
            message += f"📋 Requests Today: {len(recent_requests)}\n"
            message += f"⏳ Pending Requests: {len(pending_requests)}\n"
            message += f"📅 Date: {datetime.utcnow().strftime('%Y-%m-%d')}"
            
            self.notify_admins(message)
            
        except Exception as e:
            logger.error(f"Error sending daily stats: {e}")
    
    def notify_admins(self, message: str):
        """Send notification to all admin users"""
        try:
            admin_phones = SettingsCRUD.get_setting('admin_phone_numbers', '').split(',')
            admin_phones = [phone.strip() for phone in admin_phones if phone.strip()]
            
            for admin_phone in admin_phones:
                self.signal_client.send_message(admin_phone, message)
                
        except Exception as e:
            logger.error(f"Failed to notify admins: {e}")
    
    def schedule_request_check(self, request_id: int, delay_minutes: int = None):
        """Schedule a status check for a specific request"""
        if delay_minutes is None:
            delay_minutes = int(SettingsCRUD.get_setting('request_timeout_minutes', '2'))
        
        run_time = datetime.utcnow() + timedelta(minutes=delay_minutes)
        
        self.scheduler.add_job(
            func=self.check_single_request,
            trigger=DateTrigger(run_date=run_time),
            args=[request_id],
            id=f'check_request_{request_id}',
            name=f'Check Request {request_id}',
            replace_existing=True
        )
        
        logger.info(f"Scheduled status check for request {request_id} in {delay_minutes} minutes")
    
    def check_single_request(self, request_id: int):
        """Check status of a single request"""
        try:
            request = MediaRequestCRUD.get_request_by_id(request_id)
            if not request:
                logger.warning(f"Request {request_id} not found for status check")
                return
            
            if request.overseerr_request_id:
                overseerr_status = self.overseerr_api.get_request_status(request.overseerr_request_id)
                
                if overseerr_status:
                    new_status = self.map_overseerr_status(overseerr_status.get('status', 1))
                    
                    if new_status != request.status.value:
                        MediaRequestCRUD.update_request_status(request.id, new_status)
                        
                        # Notify user
                        user = UserCRUD.get_user_by_id(request.user_id)
                        if user:
                            self.send_status_update(user, request, new_status)
                    
                    # Schedule another check if still in progress
                    if new_status in ['approved', 'downloading']:
                        self.schedule_request_check(request_id, 5)  # Check again in 5 minutes
                        
        except Exception as e:
            logger.error(f"Error checking single request {request_id}: {e}")

def main():
    """Main entry point"""
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(Config.LOG_FILE),
            logging.StreamHandler()
        ]
    )
    
    # Create bot instance
    bot = SignalerrBot()
    
    # Initialize and start
    if bot.initialize():
        bot.start()
    else:
        logger.error("Failed to initialize bot")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
