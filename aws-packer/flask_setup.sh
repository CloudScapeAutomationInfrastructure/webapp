#!/bin/bash

# Update the instance and install necessary packages
sudo apt-get update -y
sudo apt-get upgrade -y

# Install Python and pip
sudo apt-get install -y python3-pip python3-venv

# Create a directory for the Flask app and move files
sudo mkdir -p /var/www/html/api

# Move the Flask app files from /tmp to the target directory
sudo mv /tmp/*.py /var/www/html/api/
sudo mv /tmp/requirements.txt /var/www/html/api/
sudo mv /home/ubuntu/.env /var/www/html/api/

# Create a Python virtual environment in the target directory
python3 -m venv /var/www/html/api/venv

# Activate the virtual environment and install the required packages
source /var/www/html/api/venv/bin/activate
pip install --no-cache-dir -r /var/www/html/api/requirements.txt

# Setup Flask API systemd service if required
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

# Reload systemd to recognize the new service and enable it to start on boot
sudo systemctl daemon-reload
sudo systemctl enable flask-api.service
