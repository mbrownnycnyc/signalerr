
# Signalerr Setup Guide

This guide provides detailed step-by-step instructions for setting up Signalerr with Google Voice and Signal registration.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Google Voice Setup](#google-voice-setup)
3. [Signal Registration](#signal-registration)
4. [Docker Deployment](#docker-deployment)
5. [Configuration](#configuration)
6. [Testing](#testing)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **Docker**: Version 20.10 or higher
- **Docker Compose**: Version 2.0 or higher
- **Internet Connection**: Required for Signal registration and Overseerr communication
- **Overseerr Instance**: Running and accessible
- **Domain/IP**: For accessing the admin interface

### Overseerr Requirements

1. **Running Overseerr Instance**:
   - Accessible via HTTP/HTTPS
   - Configured with Radarr/Sonarr
   - API access enabled

2. **API Key Generation**:
   - Open Overseerr web interface
   - Go to Settings → General
   - Scroll to "API Key" section
   - Click "Generate API Key" if none exists
   - Copy the API key for later use

## Google Voice Setup

Google Voice provides a free phone number that works perfectly with Signal registration.

### Step 1: Create Google Voice Account

1. **Visit Google Voice**:
   - Go to [voice.google.com](https://voice.google.com)
   - Sign in with your Google account

2. **Choose a Number**:
   - Click "Get a Voice number"
   - Search by area code or city
   - Select an available number
   - Click "Select"

3. **Verify Your Number**:
   - Enter your existing phone number for verification
   - Choose SMS or call verification
   - Enter the verification code received
   - Complete the setup process

### Step 2: Configure Google Voice

1. **Enable SMS Forwarding** (Optional):
   - Go to Settings → Messages
   - Enable "Forward messages to email"
   - This helps you receive verification codes

2. **Test the Number**:
   - Send a test SMS to your Google Voice number
   - Verify you receive it in the Google Voice app/web interface

### Step 3: Note Your Number

- Your Google Voice number will be in format: `+1XXXXXXXXXX`
- Write this down as you'll need it for Signal registration
- Example: `+15551234567`

## Signal Registration

### Step 1: Prepare Environment

1. **Clone Repository**:
   ```bash
   git clone <repository-url>
   cd signalerr
   ```

2. **Create Environment File**:
   ```bash
   cp .env.example .env
   ```

3. **Edit Environment File**:
   ```bash
   nano .env
   ```
   
   Set at minimum:
   ```bash
   SIGNAL_PHONE_NUMBER=+15551234567  # Your Google Voice number
   ADMIN_PHONE_NUMBERS=+15551234567  # Same number for initial setup
   OVERSEERR_URL=http://your-overseerr:5055
   OVERSEERR_API_KEY=your_api_key_here
   FLASK_SECRET_KEY=your-secure-random-key
   ```

### Step 2: Start Container for Registration

1. **Build and Start Container**:
   ```bash
   docker-compose up -d
   ```

2. **Enter Container**:
   ```bash
   docker-compose exec signalerr bash
   ```

3. **Switch to Signal User**:
   ```bash
   su signal
   cd /home/signal
   ```

### Step 3: Get CAPTCHA Token

Signal requires CAPTCHA verification for registration:

1. **Visit CAPTCHA Site**:
   - Open [signalcaptchas.org/registration/generate.html](https://signalcaptchas.org/registration/generate.html)
   - Complete the CAPTCHA challenge
   - Copy the entire token (starts with `signal-hcaptcha.`)

2. **Token Format**:
   - Should look like: `signal-hcaptcha.XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX.XXXXXXXXXX`
   - Must be used within a few minutes of generation

### Step 4: Register Phone Number

1. **Initiate Registration**:
   ```bash
   signal-cli -a +15551234567 register --captcha signal-hcaptcha.YOUR_TOKEN_HERE
   ```
   
   Replace:
   - `+15551234567` with your Google Voice number
   - `signal-hcaptcha.YOUR_TOKEN_HERE` with your CAPTCHA token

2. **Expected Output**:
   ```
   Requesting SMS verification code for +15551234567
   ```

3. **If SMS Fails, Try Voice**:
   ```bash
   signal-cli -a +15551234567 register --voice --captcha signal-hcaptcha.YOUR_TOKEN_HERE
   ```

### Step 5: Verify Registration

1. **Check for Verification Code**:
   - Check your Google Voice app/web interface
   - Look for SMS from Signal (usually 6-digit code)
   - If using voice, answer the call and note the code

2. **Verify with Code**:
   ```bash
   signal-cli -a +15551234567 verify 123456
   ```
   
   Replace `123456` with your actual verification code

3. **If You Have a Signal PIN**:
   ```bash
   signal-cli -a +15551234567 verify 123456 --pin YOUR_PIN
   ```

4. **Successful Verification Output**:
   ```
   Verification successful
   ```

### Step 6: Test Registration

1. **Test Basic Functionality**:
   ```bash
   signal-cli -a +15551234567 listContacts
   ```
   
   Should return without errors (may be empty list)

2. **Send Test Message**:
   ```bash
   signal-cli -a +15551234567 send -m "Test message from Signalerr bot" +15551234567
   ```
   
   You should receive this message in your Signal app

3. **Exit Container**:
   ```bash
   exit  # Exit from signal user
   exit  # Exit from container
   ```

## Docker Deployment

### Step 1: Final Configuration

1. **Review Environment File**:
   ```bash
   nano .env
   ```
   
   Ensure all required variables are set:
   ```bash
   # Overseerr Configuration
   OVERSEERR_URL=http://your-overseerr:5055
   OVERSEERR_API_KEY=your_overseerr_api_key
   
   # Signal Configuration
   SIGNAL_PHONE_NUMBER=+15551234567
   
   # Admin Configuration
   ADMIN_PHONE_NUMBERS=+15551234567,+15559876543
   
   # Security
   FLASK_SECRET_KEY=your-secure-secret-key-here
   
   # Optional: Customize behavior
   REQUEST_TIMEOUT_MINUTES=2
   MAX_REQUESTS_PER_USER_PER_DAY=10
   DEFAULT_VERBOSITY=simple
   ```

### Step 2: Deploy Services

1. **Restart with Final Configuration**:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

2. **Check Service Status**:
   ```bash
   docker-compose ps
   ```
   
   All services should show "Up" status

3. **Monitor Startup Logs**:
   ```bash
   docker-compose logs -f signalerr
   ```
   
   Look for:
   - "Bot initialized successfully"
   - "Signalerr bot started successfully"
   - No error messages

### Step 3: Verify Deployment

1. **Check Health Status**:
   ```bash
   docker-compose exec signalerr curl -f http://localhost:8080/api/stats
   ```

2. **Test Web Interface**:
   - Open http://your-server:8080
   - Should show login page

## Configuration

### Step 1: Access Admin Interface

1. **Open Web Interface**:
   - Navigate to `http://your-server:8080`
   - Enter one of your admin phone numbers
   - Click "Login"

2. **First Login**:
   - You should see the dashboard
   - Statistics should show "0" for most items initially
   - Overseerr status should show "Connected" (green)

### Step 2: Configure Settings

1. **Go to Settings Page**:
   - Click "Settings" in the sidebar
   - Review all configuration options

2. **Test Overseerr Connection**:
   - Click "Test Overseerr Connection" button
   - Should show "✅ Connection successful!"
   - If failed, check URL and API key

3. **Configure Bot Behavior**:
   - Set request timeout (default: 2 minutes)
   - Set daily request limits
   - Choose default verbosity level
   - Enable/disable features as needed

4. **Save Settings**:
   - Click "Save Settings"
   - Should show success message

### Step 3: Add Users

1. **Go to Users Page**:
   - Click "Users" in the sidebar
   - Should see your admin user listed

2. **Add New User**:
   - Click "Add User" button
   - Enter phone number (format: +1234567890)
   - Enter display name (optional)
   - Set daily request limit
   - Check "Admin User" if needed
   - Click "Add User"

3. **Test User Addition**:
   - New user should appear in the list
   - User will receive welcome message via Signal

## Testing

### Step 1: Test Bot Functionality

1. **Send Test Message**:
   - From your Signal app, send "help" to the bot number
   - Should receive help message with available commands

2. **Test Search**:
   - Send: "search The Matrix"
   - Should receive search results

3. **Test Request**:
   - Send: "request The Matrix"
   - Should receive confirmation message
   - Check admin interface for new request

### Step 2: Test Admin Functions

1. **Check Dashboard**:
   - Should show updated statistics
   - Recent activity should show your test messages

2. **View Requests**:
   - Go to Requests page
   - Should see your test request
   - Try updating request status

3. **Check Logs**:
   - Go to Logs page
   - Should see bot activity
   - Filter by different log levels

### Step 3: Test Group Functionality

1. **Create Test Group**:
   - Send: "creategroup TestGroup +1234567890"
   - Should create group and add specified users

2. **Test Group Commands**:
   - Send commands in the group chat
   - Bot should respond in the group

## Troubleshooting

### Signal Registration Issues

**Problem**: "CAPTCHA required" error
- **Solution**: Get fresh CAPTCHA token from signalcaptchas.org
- **Note**: Tokens expire quickly, use immediately

**Problem**: "Rate limited" error
- **Solution**: Wait 1-2 hours before retrying registration
- **Prevention**: Don't attempt registration too many times

**Problem**: SMS not received
- **Solution**: Try voice verification with `--voice` flag
- **Alternative**: Check Google Voice app/web interface

**Problem**: "Invalid verification code"
- **Solution**: Ensure code is entered exactly as received
- **Note**: Codes expire after a few minutes

### Connection Issues

**Problem**: Overseerr connection failed
- **Solution**: 
  - Verify Overseerr URL is accessible from container
  - Check API key is correct
  - Ensure Overseerr is running
  - Test with curl: `curl -H "X-Api-Key: YOUR_KEY" http://overseerr:5055/api/v1/status`

**Problem**: Web interface not accessible
- **Solution**:
  - Check port 8080 is not blocked by firewall
  - Verify container is running: `docker-compose ps`
  - Check logs: `docker-compose logs signalerr`

**Problem**: Bot not responding to messages
- **Solution**:
  - Check Signal daemon is running in container
  - Verify user is added to database
  - Check bot logs for errors
  - Test Signal registration manually

### Database Issues

**Problem**: Database errors on startup
- **Solution**:
  - Delete database file: `rm ./data/signalerr.db`
  - Restart container: `docker-compose restart signalerr`
  - Database will be recreated automatically

**Problem**: Users not persisting
- **Solution**:
  - Check data volume is mounted correctly
  - Verify permissions on data directory
  - Check for disk space issues

### Performance Issues

**Problem**: Slow response times
- **Solution**:
  - Check system resources (CPU, memory)
  - Monitor container logs for bottlenecks
  - Consider increasing container resources

**Problem**: High memory usage
- **Solution**:
  - Restart container periodically
  - Check for memory leaks in logs
  - Consider log cleanup settings

### Getting Help

If you encounter issues not covered here:

1. **Check Logs**:
   ```bash
   docker-compose logs -f signalerr
   ```

2. **Enable Debug Mode**:
   ```bash
   # In .env file
   LOG_LEVEL=DEBUG
   
   # Restart
   docker-compose restart signalerr
   ```

3. **Test Components Individually**:
   ```bash
   # Test Signal
   docker-compose exec signalerr su signal -c "signal-cli -a +1234567890 listContacts"
   
   # Test Overseerr
   docker-compose exec signalerr curl -H "X-Api-Key: YOUR_KEY" http://overseerr:5055/api/v1/status
   ```

4. **Create GitHub Issue**:
   - Include relevant log excerpts
   - Describe steps to reproduce
   - Include environment details
   - Sanitize sensitive information (phone numbers, API keys)

## Next Steps

After successful setup:

1. **Add More Users**: Invite friends and family to use the bot
2. **Customize Settings**: Adjust verbosity levels and limits per user
3. **Monitor Usage**: Use the admin interface to track requests and activity
4. **Set Up Backups**: Backup the data directory regularly
5. **Update Regularly**: Keep the container updated with latest releases

Congratulations! Your Signalerr bot should now be fully operational.
