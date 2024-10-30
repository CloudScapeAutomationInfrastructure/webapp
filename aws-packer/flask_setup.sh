#!/bin/bash

# Move Flask application code to the desired directory
sudo mv /tmp/* /var/www/html/api/

# Create a system user for running the Flask application
sudo groupadd -f csye6225
sudo useradd -r -g csye6225 -s /usr/sbin/nologin csye6225

# Ensure correct ownership of the application directory
sudo chown -R csye6225:csye6225 /var/www/html/api

# Create systemd service for Flask API
sudo tee /etc/systemd/system/flask-api.service <<EOL
[Unit]
Description=Flask API Service
After=network.target

[Service]
User=csye6225
Group=csye6225
WorkingDirectory=/var/www/html/api
ExecStart=/var/www/html/api/venv/bin/python /var/www/html/api/app.py
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=flask-api

[Install]
WantedBy=multi-user.target
EOL

# Reload systemd to apply changes and enable Flask service on startup
sudo systemctl daemon-reload
sudo systemctl enable flask-api.service
