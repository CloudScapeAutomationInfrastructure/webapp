#!/bin/bash

# Copy the Flask app code from temp directory
sudo mkdir -p /var/www/html/api
sudo mv /tmp/* /var/www/html/api/

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
ExecStart=/var/www/html/api/venv/bin/python /var/www/html/api/app.py

[Install]
WantedBy=multi-user.target
EOL

# Reload systemd and enable Flask service
sudo systemctl daemon-reload
sudo systemctl enable flask-api.service
