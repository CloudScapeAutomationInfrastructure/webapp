#!/bin/bash

# Copy the Flask app code from temp directory
sudo mv /tmp/* /var/www/html/api/
sudo groupadd csye6225
sudo useradd -r -g csye6225 -s /usr/sbin/nologin csye6225
# Change ownership of the application artifacts and configuration files
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
ExecStart=python3 /var/www/html/api/app.py

[Install]
WantedBy=multi-user.target
EOL

# Reload systemd and enable Flask service
sudo systemctl daemon-reload
sudo systemctl enable flask-api.service
