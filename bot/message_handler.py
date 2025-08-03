
import re
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from db.crud import UserCRUD, MediaRequestCRUD, SettingsCRUD, LogCRUD
from db.models import VerbosityLevel, RequestStatus
from api.overseerr import OverseerrAPI
from bot.signal_client import SignalMessage, SignalClient

logger = logging.getLogger(__name__)

class MessageHandler:
    def __init__(self, signal_client: SignalClient, overseerr_api: OverseerrAPI):
        self.signal_client = signal_client
        self.overseerr_api = overseerr_api
        self.commands = {
            'help': self.handle_help,
            'request': self.handle_request,
            'status': self.handle_status,
            'settings': self.handle_settings,
            'search': self.handle_search,
            'myrequest': self.handle_my_requests,
            'myrequests': self.handle_my_requests,
            'cancel': self.handle_cancel_request,
            'creategroup': self.handle_create_group,
        }
        
        # Admin-only commands
        self.admin_commands = {
            'adduser': self.handle_add_user,
            'removeuser': self.handle_remove_user,
            'listusers': self.handle_list_users,
            'approve': self.handle_approve_request,
            'decline': self.handle_decline_request,
            'broadcast': self.handle_broadcast,
            'stats': self.handle_stats,
        }
    
    def handle_message(self, message: SignalMessage):
        """Main message handler"""
        try:
            sender = message.get_sender()
            text = message.get_text()
            
            if not text:
                return
            
            # Log the message
            LogCRUD.create_log(
                level='INFO',
                message=f"Received message from {sender}: {text[:100]}",
                module='message_handler'
            )
            
            # Get or create user
            user = UserCRUD.get_user_by_phone(sender)
            if not user:
                # Only admins can add users, so reject unknown users
                self.send_response(sender, "❌ You are not authorized to use this bot. Please contact an administrator.", message)
                return
            
            # Update user's last active time
            UserCRUD.update_user(user.id, last_active=datetime.utcnow())
            
            # Check if bot is in maintenance mode
            if SettingsCRUD.get_setting('maintenance_mode', 'false').lower() == 'true' and not user.is_admin:
                self.send_response(sender, "🔧 The bot is currently in maintenance mode. Please try again later.", message)
                return
            
            # Parse command
            command, args = self.parse_command(text)
            
            if command in self.commands:
                self.commands[command](user, args, message)
            elif command in self.admin_commands:
                if user.is_admin:
                    self.admin_commands[command](user, args, message)
                else:
                    self.send_response(sender, "❌ You don't have permission to use this command.", message)
            else:
                # Try to interpret as a search/request
                self.handle_natural_request(user, text, message)
                
        except Exception as e:
            logger.error(f"Error handling message from {message.get_sender()}: {e}")
            self.send_error_to_admins(f"Error handling message: {e}", message.get_sender())
    
    def parse_command(self, text: str) -> Tuple[str, List[str]]:
        """Parse command and arguments from message text"""
        parts = text.strip().split()
        if not parts:
            return '', []
        
        command = parts[0].lower().lstrip('/')
        args = parts[1:] if len(parts) > 1 else []
        
        return command, args
    
    def send_response(self, recipient: str, message: str, original_message: SignalMessage = None):
        """Send response message"""
        try:
            if original_message and original_message.is_group_message:
                # Reply in group
                self.signal_client.send_message_to_group(original_message.group_id, message)
            else:
                # Send direct message
                self.signal_client.send_message(recipient, message)
        except Exception as e:
            logger.error(f"Failed to send response to {recipient}: {e}")
    
    def send_error_to_admins(self, error_message: str, user_phone: str = None):
        """Send error notification to admin users"""
        try:
            admin_phones = SettingsCRUD.get_setting('admin_phone_numbers', '').split(',')
            admin_phones = [phone.strip() for phone in admin_phones if phone.strip()]
            
            message = f"🚨 Signalerr Error\n\n{error_message}"
            if user_phone:
                message += f"\n\nUser: {user_phone}"
            
            for admin_phone in admin_phones:
                self.signal_client.send_message(admin_phone, message)
                
        except Exception as e:
            logger.error(f"Failed to send error to admins: {e}")
    
    def handle_help(self, user, args, message):
        """Handle help command"""
        help_text = """🤖 **Signalerr Bot Commands**

**Media Requests:**
• `request <movie/show name>` - Request media
• `search <query>` - Search for media
• `status` - Check your recent requests
• `myrequests` - List all your requests
• `cancel <request_id>` - Cancel a request

**Settings:**
• `settings` - View your settings
• `settings verbosity <verbose/simple/casual>` - Change notification style
• `settings notifications <on/off>` - Toggle auto notifications

**Groups:**
• `creategroup <name> <phone1> <phone2>...` - Create group chat

**General:**
• `help` - Show this help message

**Examples:**
• `request The Matrix`
• `request Breaking Bad seasons 1-4`
• `search marvel movies`
• `settings verbosity casual`

You can also just type the name of a movie or show to request it!"""

        if user.is_admin:
            help_text += """

**Admin Commands:**
• `adduser <phone> [name]` - Add new user
• `removeuser <phone>` - Remove user
• `listusers` - List all users
• `approve <request_id>` - Approve request
• `decline <request_id> [reason]` - Decline request
• `broadcast <message>` - Send message to all users
• `stats` - Show bot statistics"""

        self.send_response(user.phone_number, help_text, message)
    
    def handle_request(self, user, args, message):
        """Handle media request command"""
        if not args:
            self.send_response(user.phone_number, "❌ Please specify what you want to request.\nExample: `request The Matrix`", message)
            return
        
        query = ' '.join(args)
        self.process_media_request(user, query, message)
    
    def handle_natural_request(self, user, text, message):
        """Handle natural language requests"""
        # Skip if it looks like a command
        if text.startswith('/') or text.lower().startswith(tuple(self.commands.keys())):
            self.send_response(user.phone_number, "❓ Unknown command. Type `help` for available commands.", message)
            return
        
        # Treat as media request
        self.process_media_request(user, text, message)
    
    def process_media_request(self, user, query, message):
        """Process a media request"""
        try:
            # Check if user can make requests
            if not user.can_make_request():
                self.send_response(
                    user.phone_number,
                    f"❌ You've reached your daily request limit ({user.daily_request_limit}). Try again tomorrow!",
                    message
                )
                return
            
            # Search for media
            self.send_response(user.phone_number, f"🔍 Searching for '{query}'...", message)
            
            search_results = self.overseerr_api.search_media(query)
            
            if not search_results:
                self.send_response(user.phone_number, f"❌ No results found for '{query}'. Try a different search term.", message)
                return
            
            # Get the best match (first result)
            best_match = search_results[0]
            media_info = self.overseerr_api.parse_media_info(best_match)
            
            # Check if already available
            if self.overseerr_api.is_media_available(media_info['tmdb_id']):
                self.send_response(
                    user.phone_number,
                    f"✅ '{media_info['title']}' is already available!",
                    message
                )
                return
            
            # Handle TV shows with season selection
            seasons_to_request = None
            if media_info['media_type'] == 'tv':
                seasons_to_request = self.determine_seasons_to_request(media_info, query)
            
            # Create request in database
            db_request = MediaRequestCRUD.create_request(
                user_id=user.id,
                media_type=media_info['media_type'],
                media_id=media_info['tmdb_id'],
                title=media_info['title'],
                year=media_info.get('year'),
                seasons=seasons_to_request
            )
            
            # Submit to Overseerr
            if media_info['media_type'] == 'movie':
                success, overseerr_id, error = self.overseerr_api.request_movie(media_info['tmdb_id'])
            else:
                success, overseerr_id, error = self.overseerr_api.request_tv_show(
                    media_info['tmdb_id'], 
                    seasons_to_request
                )
            
            if success:
                # Update request with Overseerr ID
                MediaRequestCRUD.update_request_status(
                    db_request.id, 
                    'approved', 
                    overseerr_request_id=overseerr_id
                )
                
                # Send confirmation
                confirmation = self.format_request_confirmation(media_info, seasons_to_request, user.verbosity_level)
                self.send_response(user.phone_number, confirmation, message)
                
                # Schedule status check
                self.schedule_status_check(db_request.id)
                
            else:
                # Update request with error
                MediaRequestCRUD.update_request_status(db_request.id, 'failed', error_message=error)
                self.send_response(user.phone_number, f"❌ Failed to request '{media_info['title']}': {error}", message)
                
        except Exception as e:
            logger.error(f"Error processing request for {user.phone_number}: {e}")
            self.send_response(user.phone_number, "❌ An error occurred while processing your request. Please try again.", message)
            self.send_error_to_admins(f"Request processing error: {e}", user.phone_number)
    
    def determine_seasons_to_request(self, media_info: Dict, query: str) -> Optional[List[int]]:
        """Determine which seasons to request for TV shows"""
        total_seasons = media_info.get('seasons', 0)
        
        # Check if user specified seasons in query
        season_match = re.search(r'season[s]?\s*(\d+)(?:\s*[-–]\s*(\d+))?', query.lower())
        if season_match:
            start_season = int(season_match.group(1))
            end_season = int(season_match.group(2)) if season_match.group(2) else start_season
            return list(range(start_season, end_season + 1))
        
        # Check for "latest" or "recent" keywords
        if any(word in query.lower() for word in ['latest', 'recent', 'new', 'current']):
            if total_seasons >= 4:
                return list(range(max(1, total_seasons - 3), total_seasons + 1))
        
        # Default behavior based on total seasons
        if total_seasons >= 4:
            # Ask user if they want latest 4 seasons or all
            return list(range(max(1, total_seasons - 3), total_seasons + 1))
        
        # Request all seasons for shows with < 4 seasons
        return None
    
    def format_request_confirmation(self, media_info: Dict, seasons: List[int], verbosity: VerbosityLevel) -> str:
        """Format request confirmation message based on verbosity level"""
        title = media_info['title']
        year = f" ({media_info['year']})" if media_info.get('year') else ""
        
        if verbosity == VerbosityLevel.CASUAL:
            if media_info['media_type'] == 'movie':
                return f"👍 Gotcha! Requesting '{title}' for ya."
            else:
                season_text = f" seasons {seasons[0]}-{seasons[-1]}" if seasons else ""
                return f"👍 Gotcha! Requesting '{title}'{season_text} for ya."
        
        elif verbosity == VerbosityLevel.SIMPLE:
            if media_info['media_type'] == 'movie':
                return f"✅ Requested: {title}{year}\n⏱️ I'll check back in 2 minutes!"
            else:
                season_text = f" (Seasons {seasons[0]}-{seasons[-1]})" if seasons else " (All seasons)"
                return f"✅ Requested: {title}{year}{season_text}\n⏱️ I'll check back in 2 minutes!"
        
        else:  # VERBOSE
            base_msg = f"✅ **Request Submitted Successfully**\n\n"
            base_msg += f"📺 **Title:** {title}{year}\n"
            base_msg += f"🎬 **Type:** {media_info['media_type'].title()}\n"
            
            if media_info['media_type'] == 'tv' and seasons:
                base_msg += f"📅 **Seasons:** {seasons[0]}-{seasons[-1]}\n"
            
            base_msg += f"⏱️ **Status Check:** I'll update you in 2 minutes\n"
            base_msg += f"🔄 **Current Status:** Processing request..."
            
            return base_msg
    
    def handle_search(self, user, args, message):
        """Handle search command"""
        if not args:
            self.send_response(user.phone_number, "❌ Please specify what to search for.\nExample: `search Marvel movies`", message)
            return
        
        query = ' '.join(args)
        
        try:
            results = self.overseerr_api.search_media(query)
            
            if not results:
                self.send_response(user.phone_number, f"❌ No results found for '{query}'.", message)
                return
            
            # Format results (show top 5)
            response = f"🔍 **Search Results for '{query}':**\n\n"
            
            for i, result in enumerate(results[:5], 1):
                media_info = self.overseerr_api.parse_media_info(result)
                title = media_info['title']
                year = f" ({media_info['year']})" if media_info.get('year') else ""
                media_type = media_info['media_type'].title()
                
                response += f"{i}. {title}{year} [{media_type}]\n"
            
            response += f"\nTo request any of these, just type: `request [title]`"
            
            self.send_response(user.phone_number, response, message)
            
        except Exception as e:
            logger.error(f"Search error for {user.phone_number}: {e}")
            self.send_response(user.phone_number, "❌ Search failed. Please try again.", message)
    
    def handle_status(self, user, args, message):
        """Handle status command"""
        try:
            recent_requests = MediaRequestCRUD.get_user_requests(user.id, limit=5)
            
            if not recent_requests:
                self.send_response(user.phone_number, "📭 You haven't made any requests yet.", message)
                return
            
            response = "📊 **Your Recent Requests:**\n\n"
            
            for req in recent_requests:
                status_emoji = self.get_status_emoji(req.status)
                response += f"{status_emoji} {req.title}"
                
                if req.year:
                    response += f" ({req.year})"
                
                response += f" - {req.status.value.title()}\n"
                
                if req.error_message:
                    response += f"   ❌ {req.error_message}\n"
            
            self.send_response(user.phone_number, response, message)
            
        except Exception as e:
            logger.error(f"Status check error for {user.phone_number}: {e}")
            self.send_response(user.phone_number, "❌ Failed to get status. Please try again.", message)
    
    def handle_my_requests(self, user, args, message):
        """Handle my requests command"""
        try:
            all_requests = MediaRequestCRUD.get_user_requests(user.id, limit=20)
            
            if not all_requests:
                self.send_response(user.phone_number, "📭 You haven't made any requests yet.", message)
                return
            
            response = f"📋 **All Your Requests ({len(all_requests)}):**\n\n"
            
            for req in all_requests:
                status_emoji = self.get_status_emoji(req.status)
                response += f"{status_emoji} #{req.id} {req.title}"
                
                if req.year:
                    response += f" ({req.year})"
                
                response += f" - {req.status.value.title()}\n"
                
                if req.completed_at:
                    response += f"   ✅ Completed: {req.completed_at.strftime('%m/%d %H:%M')}\n"
                elif req.error_message:
                    response += f"   ❌ Error: {req.error_message}\n"
            
            response += f"\nDaily requests used: {user.get_daily_request_count()}/{user.daily_request_limit}"
            
            self.send_response(user.phone_number, response, message)
            
        except Exception as e:
            logger.error(f"My requests error for {user.phone_number}: {e}")
            self.send_response(user.phone_number, "❌ Failed to get your requests. Please try again.", message)
    
    def get_status_emoji(self, status: RequestStatus) -> str:
        """Get emoji for request status"""
        emoji_map = {
            RequestStatus.PENDING: "⏳",
            RequestStatus.APPROVED: "✅",
            RequestStatus.DOWNLOADING: "⬇️",
            RequestStatus.COMPLETED: "🎉",
            RequestStatus.FAILED: "❌",
            RequestStatus.DECLINED: "❌"
        }
        return emoji_map.get(status, "❓")
    
    def handle_settings(self, user, args, message):
        """Handle settings command"""
        if not args:
            # Show current settings
            response = f"⚙️ **Your Settings:**\n\n"
            response += f"🔊 **Verbosity:** {user.verbosity_level.value}\n"
            response += f"🔔 **Auto Notifications:** {'On' if user.auto_notifications else 'Off'}\n"
            response += f"📊 **Daily Limit:** {user.daily_request_limit}\n"
            response += f"📈 **Today's Requests:** {user.get_daily_request_count()}/{user.daily_request_limit}\n\n"
            response += "**Change Settings:**\n"
            response += "• `settings verbosity <verbose/simple/casual>`\n"
            response += "• `settings notifications <on/off>`"
            
            self.send_response(user.phone_number, response, message)
            return
        
        setting_type = args[0].lower()
        
        if setting_type == 'verbosity' and len(args) > 1:
            verbosity = args[1].lower()
            if verbosity in ['verbose', 'simple', 'casual']:
                UserCRUD.update_user(user.id, verbosity_level=VerbosityLevel(verbosity))
                self.send_response(user.phone_number, f"✅ Verbosity set to '{verbosity}'", message)
            else:
                self.send_response(user.phone_number, "❌ Invalid verbosity. Use: verbose, simple, or casual", message)
        
        elif setting_type == 'notifications' and len(args) > 1:
            setting = args[1].lower()
            if setting in ['on', 'off']:
                auto_notifications = setting == 'on'
                UserCRUD.update_user(user.id, auto_notifications=auto_notifications)
                self.send_response(user.phone_number, f"✅ Auto notifications turned {setting}", message)
            else:
                self.send_response(user.phone_number, "❌ Use 'on' or 'off' for notifications", message)
        
        else:
            self.send_response(user.phone_number, "❌ Invalid setting. Type `settings` to see options.", message)
    
    def handle_create_group(self, user, args, message):
        """Handle create group command"""
        if len(args) < 2:
            self.send_response(user.phone_number, "❌ Usage: `creategroup <name> <phone1> <phone2>...`", message)
            return
        
        group_name = args[0]
        members = args[1:]
        
        # Add the user who created the group
        members.append(user.phone_number)
        
        try:
            group_id = self.signal_client.create_group(group_name, members)
            if group_id:
                self.send_response(user.phone_number, f"✅ Group '{group_name}' created successfully!", message)
            else:
                self.send_response(user.phone_number, f"❌ Failed to create group '{group_name}'", message)
        except Exception as e:
            logger.error(f"Group creation error: {e}")
            self.send_response(user.phone_number, "❌ Failed to create group. Please try again.", message)
    
    # Admin commands
    def handle_add_user(self, user, args, message):
        """Handle add user command (admin only)"""
        if not args:
            self.send_response(user.phone_number, "❌ Usage: `adduser <phone> [display_name]`", message)
            return
        
        phone = args[0]
        display_name = ' '.join(args[1:]) if len(args) > 1 else None
        
        try:
            existing_user = UserCRUD.get_user_by_phone(phone)
            if existing_user:
                self.send_response(user.phone_number, f"❌ User {phone} already exists", message)
                return
            
            new_user = UserCRUD.create_user(phone, display_name)
            self.send_response(user.phone_number, f"✅ Added user: {phone}", message)
            
            # Welcome the new user
            welcome_msg = f"🎉 Welcome to Signalerr! You've been added by an admin.\n\nType `help` to see available commands."
            self.signal_client.send_message(phone, welcome_msg)
            
        except Exception as e:
            logger.error(f"Add user error: {e}")
            self.send_response(user.phone_number, f"❌ Failed to add user: {e}", message)
    
    def handle_remove_user(self, user, args, message):
        """Handle remove user command (admin only)"""
        if not args:
            self.send_response(user.phone_number, "❌ Usage: `removeuser <phone>`", message)
            return
        
        phone = args[0]
        
        try:
            target_user = UserCRUD.get_user_by_phone(phone)
            if not target_user:
                self.send_response(user.phone_number, f"❌ User {phone} not found", message)
                return
            
            UserCRUD.delete_user(target_user.id)
            self.send_response(user.phone_number, f"✅ Removed user: {phone}", message)
            
        except Exception as e:
            logger.error(f"Remove user error: {e}")
            self.send_response(user.phone_number, f"❌ Failed to remove user: {e}", message)
    
    def handle_list_users(self, user, args, message):
        """Handle list users command (admin only)"""
        try:
            users = UserCRUD.get_all_users()
            
            if not users:
                self.send_response(user.phone_number, "📭 No users found", message)
                return
            
            response = f"👥 **All Users ({len(users)}):**\n\n"
            
            for u in users:
                status = "👑" if u.is_admin else "👤"
                response += f"{status} {u.phone_number}"
                if u.display_name:
                    response += f" ({u.display_name})"
                response += f" - {u.get_daily_request_count()}/{u.daily_request_limit} requests today\n"
            
            self.send_response(user.phone_number, response, message)
            
        except Exception as e:
            logger.error(f"List users error: {e}")
            self.send_response(user.phone_number, "❌ Failed to list users", message)
    
    def handle_stats(self, user, args, message):
        """Handle stats command (admin only)"""
        try:
            # Get various statistics
            total_users = len(UserCRUD.get_all_users())
            recent_requests = MediaRequestCRUD.get_recent_requests(days=7)
            pending_requests = MediaRequestCRUD.get_requests_by_status('pending')
            completed_requests = MediaRequestCRUD.get_requests_by_status('completed')
            
            response = f"📊 **Bot Statistics:**\n\n"
            response += f"👥 **Total Users:** {total_users}\n"
            response += f"📋 **Requests (7 days):** {len(recent_requests)}\n"
            response += f"⏳ **Pending Requests:** {len(pending_requests)}\n"
            response += f"✅ **Completed Requests:** {len(completed_requests)}\n"
            
            # Overseerr connection status
            if self.overseerr_api.test_connection():
                response += f"🟢 **Overseerr:** Connected\n"
            else:
                response += f"🔴 **Overseerr:** Disconnected\n"
            
            self.send_response(user.phone_number, response, message)
            
        except Exception as e:
            logger.error(f"Stats error: {e}")
            self.send_response(user.phone_number, "❌ Failed to get statistics", message)
    
    def schedule_status_check(self, request_id: int):
        """Schedule a status check for a request"""
        # This is handled by the main bot's scheduler
        logger.info(f"Status check scheduled for request {request_id}")
        pass
