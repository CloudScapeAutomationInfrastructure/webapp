#!/bin/bash

# Update the instance and install dependencies
sudo apt-get update -y
sudo apt-get upgrade -y

# Install MySQL server and client
sudo apt-get install -y mysql-server mysql-client
sudo systemctl start mysql
sudo systemctl enable mysql

# Install Python and Pip
sudo apt-get install -y python3-pip python3-venv

# Create a virtual environment for Flask app
sudo mkdir -p /var/www/html/api
python3 -m venv /var/www/html/api/venv

# Activate the virtual environment and install Python packages
source /var/www/html/api/venv/bin/activate
pip install -r /tmp/requirements.txt

# Set up MySQL database and user
sudo mysql -e "CREATE DATABASE IF NOT EXISTS webapp_db;"
sudo mysql -e "CREATE USER 'webapp_user'@'localhost' IDENTIFIED BY 'password';"
sudo mysql -e "GRANT ALL PRIVILEGES ON webapp_db.* TO 'webapp_user'@'localhost';"
sudo mysql -e "FLUSH PRIVILEGES;"

# Create the 'csye6225' user and group without a login shell
sudo groupadd csye6225
sudo useradd -g csye6225 -s /usr/sbin/nologin csye6225

# Ensure proper ownership of the app directory
sudo chown -R csye6225:csye6225 /var/www/html/api

# Reload systemd services
sudo systemctl daemon-reload
