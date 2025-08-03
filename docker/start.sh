
#!/bin/bash

# Create necessary directories
mkdir -p /app/data /app/logs
chown -R signal:signal /app/data /app/logs

# Initialize database if it doesn't exist
if [ ! -f /app/data/signalerr.db ]; then
    echo "Initializing database..."
    su signal -c "cd /app && python3 -c 'from web.app import app, db; app.app_context().push(); db.create_all()'"
fi

# Check if Signal is registered
echo "Checking Signal registration..."
if ! su signal -c "signal-cli -a $SIGNAL_PHONE_NUMBER --config /home/signal/.local/share/signal-cli listContacts" > /dev/null 2>&1; then
    echo "WARNING: Signal phone number $SIGNAL_PHONE_NUMBER is not registered!"
    echo "Please register your Signal number before starting the bot."
    echo "See the setup instructions in README.md"
fi

# Start supervisor
echo "Starting Signalerr services..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/signalerr.conf
