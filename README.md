
# Signalerr - Signal Bot for Overseerr

Signalerr is a Signal bot that integrates with Overseerr to allow users to request movies and TV shows via Signal messages. It includes a web-based admin interface for user management, request monitoring, and configuration.

## Features

- **Signal Bot Integration**: Request media via Signal messages
- **Overseerr API Integration**: Seamless integration with Overseerr for media requests
- **User Management**: Phone number-based authentication with admin controls
- **Request Workflow**: 2-minute wait workflow with status updates
- **Smart TV Show Handling**: Automatic season selection for shows with 4+ seasons
- **Configurable Notifications**: Three verbosity levels (casual, simple, verbose)
- **Rate Limiting**: Configurable daily request limits per user
- **Admin Web UI**: Complete web interface for administration
- **Group Chat Support**: Works in both direct messages and group chats
- **Comprehensive Logging**: Full activity logging with web interface
- **Docker Support**: Complete containerization with docker-compose

## Quick Start

### Prerequisites

- Docker and Docker Compose
- A Signal phone number (Google Voice recommended)
- Running Overseerr instance
- Overseerr API key

### 1. Clone and Setup

```bash
git clone <repository-url>
cd signalerr
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` file with your settings:

```bash
# Overseerr Configuration
OVERSEERR_URL=http://your-overseerr-url:5055
OVERSEERR_API_KEY=your_overseerr_api_key

# Signal Configuration  
SIGNAL_PHONE_NUMBER=+1234567890

# Admin Configuration
ADMIN_PHONE_NUMBERS=+1234567890,+0987654321

# Security
FLASK_SECRET_KEY=your-secure-secret-key
```

### 3. Deploy with Docker

```bash
# Build and start services
docker-compose up -d

# Check logs
docker-compose logs -f signalerr
```

### 4. Register Signal Number

The bot requires a registered Signal number. Follow these steps:

#### Option A: Using Google Voice (Recommended)

1. **Get Google Voice Number**:
   - Go to [voice.google.com](https://voice.google.com)
   - Sign up and get a free phone number
   - Verify the number with your existing phone

2. **Register with Signal**:
   ```bash
   # Enter the container
   docker-compose exec signalerr bash
   
   # Switch to signal user
   su signal
   
   # Get CAPTCHA token
   # Visit: https://signalcaptchas.org/registration/generate.html
   # Solve the CAPTCHA and copy the token
   
   # Register (replace with your number and token)
   signal-cli -a +1234567890 register --captcha signal-hcaptcha.XXXXXX
   
   # You'll receive an SMS/call with verification code
   # Verify (replace with your code)
   signal-cli -a +1234567890 verify 123456
   ```

3. **Test Registration**:
   ```bash
   # Test if registration worked
   signal-cli -a +1234567890 listContacts
   
   # Send test message to yourself
   signal-cli -a +1234567890 send -m "Test message" +1234567890
   ```

#### Option B: Using Existing Signal Number

If you have an existing Signal number, you can link it:

1. **Link Device**:
   ```bash
   # Generate linking QR code
   docker-compose exec signalerr su signal -c "signal-cli link -n 'Signalerr Bot'"
   
   # Scan the QR code with your Signal app:
   # Signal Settings > Linked Devices > Link New Device
   ```

### 5. Access Admin Interface

1. Open http://localhost:8080 in your browser
2. Login with one of your admin phone numbers
3. Add users and configure settings

## Usage

### Bot Commands

**Media Requests:**
- `request The Matrix` - Request a movie
- `request Breaking Bad seasons 1-4` - Request specific TV seasons
- `search marvel movies` - Search for media
- `status` - Check your recent requests
- `myrequests` - List all your requests

**Settings:**
- `settings` - View your settings
- `settings verbosity casual` - Change notification style
- `settings notifications off` - Toggle auto notifications

**Groups:**
- `creategroup MovieNight +1234567890 +0987654321` - Create group chat

**Natural Language:**
You can also just type movie/show names directly:
- "The Matrix"
- "Breaking Bad latest seasons"
- "Marvel movies"

### Admin Commands

**User Management:**
- `adduser +1234567890 John Doe` - Add new user
- `removeuser +1234567890` - Remove user
- `listusers` - List all users

**Request Management:**
- `approve 123` - Approve request
- `decline 123 Not available` - Decline request
- `broadcast Hello everyone!` - Message all users
- `stats` - Show bot statistics

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OVERSEERR_URL` | Overseerr server URL | `http://localhost:5055` |
| `OVERSEERR_API_KEY` | Overseerr API key | Required |
| `SIGNAL_PHONE_NUMBER` | Bot's Signal number | Required |
| `ADMIN_PHONE_NUMBERS` | Comma-separated admin numbers | Required |
| `REQUEST_TIMEOUT_MINUTES` | Status check delay | `2` |
| `MAX_REQUESTS_PER_USER_PER_DAY` | Daily request limit | `10` |
| `DEFAULT_VERBOSITY` | Default notification style | `simple` |
| `FLASK_SECRET_KEY` | Web UI secret key | Required |

### Verbosity Levels

**Casual**: Friendly, informal messages
- "Gotcha! Requesting 'The Matrix' for ya."
- "Still downloadin'..."
- "Done downloadin'! Enjoy!"

**Simple**: Clean, informative messages  
- "✅ Requested: The Matrix (1999)"
- "⬇️ The Matrix - Download started"
- "✅ The Matrix - Download completed!"

**Verbose**: Detailed status information
- Full request details with timestamps
- Progress updates with technical info
- Complete status breakdowns

## Web Admin Interface

Access the admin interface at `http://localhost:8080`:

### Dashboard
- System statistics and health status
- Recent activity logs
- Quick action buttons
- Overseerr connection status

### User Management
- Add/remove users
- Configure individual settings
- View request history
- Set custom daily limits

### Request Monitoring
- View all requests with filters
- Update request statuses
- Monitor download progress
- Handle failed requests

### Settings Configuration
- Overseerr connection settings
- Bot behavior configuration
- Feature toggles
- Admin notifications

### System Logs
- Real-time log monitoring
- Filter by level and module
- Error tracking and debugging
- Performance monitoring

## Architecture

### Components

1. **Signal Bot** (`bot/`):
   - Signal message handling
   - Command processing
   - Request workflow management
   - Status monitoring

2. **Overseerr API Client** (`api/`):
   - Media search and requests
   - Status checking
   - Request management

3. **Web Admin Interface** (`web/`):
   - Flask-based admin panel
   - User and request management
   - Configuration interface
   - Real-time monitoring

4. **Database Layer** (`db/`):
   - SQLite database
   - User and request models
   - Settings and logging
   - CRUD operations

### Request Workflow

1. User sends message to bot
2. Bot authenticates user
3. Bot searches Overseerr for media
4. Bot creates request in database
5. Bot submits request to Overseerr
6. Bot schedules status check (2 minutes)
7. Bot monitors download progress
8. Bot notifies user of completion

### Database Schema

- **Users**: Phone numbers, settings, permissions
- **Requests**: Media requests with status tracking
- **Settings**: Bot configuration
- **Logs**: System activity and errors

## Troubleshooting

### Common Issues

**Signal Registration Failed**:
- Ensure phone number format is correct (+1234567890)
- Try voice verification if SMS fails
- Check CAPTCHA token is valid and recent
- Verify container has internet access

**Overseerr Connection Failed**:
- Check Overseerr URL is accessible from container
- Verify API key is correct and has permissions
- Test connection in admin interface
- Check Overseerr logs for errors

**Bot Not Responding**:
- Check bot logs: `docker-compose logs signalerr`
- Verify Signal daemon is running
- Test Signal registration manually
- Check user is added to bot database

**Web Interface Not Loading**:
- Verify port 8080 is accessible
- Check Flask logs for errors
- Ensure admin phone number is configured
- Try different browser/clear cache

### Log Locations

```bash
# Container logs
docker-compose logs -f signalerr

# Application logs (inside container)
docker-compose exec signalerr tail -f /app/logs/signalerr.log
docker-compose exec signalerr tail -f /app/logs/bot.log
docker-compose exec signalerr tail -f /app/logs/web.log

# Host logs (if volume mounted)
tail -f ./logs/signalerr.log
```

### Debug Mode

Enable debug logging:

```bash
# In .env file
LOG_LEVEL=DEBUG
FLASK_DEBUG=true

# Restart container
docker-compose restart signalerr
```

## Security Considerations

- **Phone Number Authentication**: Only admin-added users can use the bot
- **API Key Protection**: Overseerr API key stored securely
- **Session Management**: Web interface uses secure sessions
- **Rate Limiting**: Configurable request limits prevent abuse
- **Input Validation**: All user inputs are validated and sanitized
- **Error Handling**: Errors are logged but not exposed to users

## Development

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your settings

# Initialize database
python -c "from web.app import app, db; app.app_context().push(); db.create_all()"

# Run components separately
python -m bot.bot          # Signal bot
python -m web.app          # Web interface
```

### Testing

```bash
# Run tests
pytest

# Test Signal connection
python -c "from bot.signal_client import SignalClient; client = SignalClient('+1234567890'); print(client.is_registered())"

# Test Overseerr connection  
python -c "from api.overseerr import OverseerrAPI; api = OverseerrAPI('http://localhost:5055', 'your-key'); print(api.test_connection())"
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs for error messages
3. Search existing GitHub issues
4. Create a new issue with detailed information

## Acknowledgments

- [signal-cli](https://github.com/AsamK/signal-cli) - Signal command line interface
- [Overseerr](https://github.com/sct/overseerr) - Media request management
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database ORM


# Produced using DeepAgent by abacus.ai

* this is really a test project for using DeepAgent.
  * initial token cost, including questions and answers: ~2200.
  * To complete the DeepAgent tasks, I had to upgrade to Pro ($20USD/month).  I used my Cashapp card, and funded it with $10 to sign up then $10 to move to Pro so the subscription will break if I don't get any traction on use.

## prompt
```
My goal is to create a signal bot which runs on a docker container.  This signal bot will interface with overseerr via an API.

The goal of the bot is to allow people to request tv shows and movies via overseerr.

The name of the project is called signalerr

If the movie or tv show is available, let the user know that "overseerr will begin communicating with sonarr or radarr to search now. An update will be given in no less than two minutes."  Then send the request to overseerr.  Allow two minutes to pass, then check with overseerr to obtain status of the download.  If the movie or tv show are downloading, then let the user know that their download has begun, listing the name of the movie or tv show, and the time remaining.  If the movie or tv show are not downloading, then let the user know "Unfortunately, it doesn't appear that sonarr or radarr have been able to locate your movie or tv show.  That doesn't mean it won't be found, as sonarr or radarr will keep searching for it to arrive.  This may happen if you've requested a movie that hasn't been released yet or if you're a hipster and have requested a movie or tv show that's obscure."

Use the overseerr API to request the entire tv show, or the movie.

If the movie is part of a series, prompt the user with a question such as "[Movie name] is part of a movie series called: [movie series name].  Would you like to request all movies in the series instead of just the movie?"  Then call the API to do just that.

If the TV series is more than four seasons, prompt the user with "The TV show [tv show name] has more than four seasons.  Would you like to download only the latest four seasons?"  then call the API to do just that.

As movies or tv shows are downloaded, provide a user with download status only when the user asks.

Everything should be run within a docker container.  Overseerr is accessible with an API key and an http connection.  Each user's signal number or ID must be known by an admin and added via a simple administrative web UI.  The UI should provide the ability to enter any settings related to the signal client config, as well as issue any bot invites.  If it makes it easier to start a group conversation with the bot and the user, then that's fine (and preferred), but the only people in the signal group that can interact with the bot will be the ones onboarded through the admin UI.

Include explicit configuration instructions, including a docker compose file to make it easy.  Also, provide exact step by step instructions on setting up a google voice account and signal number.

Include all code files as a source.

Ask as many questions as you need.
```

## questions and answers
```
1. Overseerr API Details: Do you have the Overseerr API documentation URL or specific endpoints you want me to reference? Or should I use the standard Overseerr API endpoints?
2. Signal Bot Framework: Would you prefer to use a specific Signal bot library/framework (like signal-cli, or a Python library), or do you have a preference?
3. Database: Do you need persistent storage for user management and request tracking? Should I include a simple database (like SQLite) in the Docker setup?
4. Admin UI Features: Besides adding users and Signal config, what other admin features would you like? (e.g., view all requests, manage download queue, bot statistics)
5. User Authentication: Should the bot verify users by their Signal phone number, or do you want additional authentication layers?
6. Notification Preferences: Should the bot automatically notify users when their downloads complete, or only when they ask for status updates?
7. Request Limits: Should there be any limits on how many requests a user can make per day/hour?

1. Use the standard Overseerr API documentation.
2. i have no specific preference, but I will be asking you to add features as the project grows, so whatever is easier. 
3. yes, i'd like persistent tracking of user requests, maybe users will be able to look up their fulfillment and other activity stats.  Whatever you feel is appropriate is fine.  SQLite is fine.  It won't scale past 50 users.
4. the admin UI MUST be served from the docker container itself, not on abacus.  No exceptions.  Bot statistics is fine.
5. just by phone number, as added by the admin themselves.  The bot will reject anyone who isn't the added number.
6. by default, alert the user when their download completes; but allow them to disable this.
7. You can enable this as a feature that is configurable in the admin ui.

If you have any more questions, please ask.


1. Admin UI Port: What port should the admin web UI run on inside the container? (e.g., port 8080, 3000, etc.)
2. Signal Bot Setup: Should the bot create a group chat with each user when they're added, or should users initiate contact with the bot directly? You mentioned preferring group conversations.
3. Overseerr Connection: Should the Overseerr API URL and API key be configurable through the admin UI, or just through environment variables/config files?
4. Download Status Format: For the download status messages, do you want specific details like file size, download speed, ETA, or just basic "downloading/completed" status?
5. Movie Series Detection: Should I use a specific movie database API (like TMDB) to detect movie series, or rely on Overseerr's built-in series detection?
6. Error Handling: How should the bot handle cases where Overseerr is unreachable or returns errors? Should it queue requests to retry later?
7. Logging: Do you want detailed logging for debugging purposes, and should logs be accessible through the admin UI?

1. the overseerr integration should be configuable through the admin ui.
2. there is a requirement that the signal number be added to the admin ui.  a group conversation is fine, or direct messaging is also  fine.  If the user adds the signal bot number to a chat or group, then that's fine.  If a group doesn't exist, there should be a user issued command to have the bot create a group.
3. yes, generally all variable items should be configurable through the admin ui.  Remember: the admin UI is not to be hosted on ababus, but to be hosted in the container.  No exceptions.
4. By default provide verbose information about downloads.  However, provide verbosity levels as follows: verbose (contains all information about downloads), simple (provides the simply the name of items and their remaining time to download), casual (just providing whether or not the users requests are downloading with the strings "still downloadin'"  "done downloadin'"
5. rely on built in overseerr.
6. yes, share that there is an error, and state that the sysop has been contacted, then use signal to contact the admin with the error information.  The admin signal number should be configurable in the admin ui.  You may have many admins.
7. yes, verbose logging if levels are selected,  yes, make available in web ui and in docker container.

```