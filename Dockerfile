
FROM ubuntu:22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV SIGNAL_CLI_VERSION=0.13.18

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    openjdk-21-jre-headless \
    wget \
    curl \
    unzip \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Create signal user and directories
RUN useradd -m -s /bin/bash signal && \
    mkdir -p /home/signal/.local/share/signal-cli && \
    chown -R signal:signal /home/signal && \
    mkdir -p /app/logs && \
    chown -R signal:signal /app/logs

# Install signal-cli
RUN wget https://github.com/AsamK/signal-cli/releases/download/v${SIGNAL_CLI_VERSION}/signal-cli-${SIGNAL_CLI_VERSION}.tar.gz && \
    tar xf signal-cli-${SIGNAL_CLI_VERSION}.tar.gz -C /opt && \
    ln -sf /opt/signal-cli-${SIGNAL_CLI_VERSION}/bin/signal-cli /usr/local/bin/ && \
    rm signal-cli-${SIGNAL_CLI_VERSION}.tar.gz

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create supervisor configuration
RUN mkdir -p /etc/supervisor/conf.d
COPY docker/supervisord.conf /etc/supervisor/conf.d/signalerr.conf

# Set permissions
RUN chown -R signal:signal /app

# Create startup script
COPY docker/start.sh /start.sh
RUN chmod +x /start.sh

# Expose port for web UI
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/stats || exit 1

# Start services
CMD ["/start.sh"]
