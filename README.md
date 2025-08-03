
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
