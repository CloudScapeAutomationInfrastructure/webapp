#!/bin/bash

# Update the instance and install dependencies
sudo apt-get update -y
sudo apt-get upgrade -y
# Create the 'csye6225' user and group without a login shell

# Install MySQL server and client
sudo apt-get install -y mysql-server mysql-client
sudo systemctl start mysql
sudo systemctl enable mysql

# Install Python and pip (Python venv as well)
sudo apt-get install -y python3-pip python3-venv

# Create a directory for the Flask app and move files
#comment
sudo mkdir -p /var/www/html/api

sudo mv /tmp/*.py /var/www/html/api/
sudo mv /tmp/requirements.txt /var/www/html/api/
sudo mv /home/ubuntu/.env /var/www/html/api/

# Create the virtual environment in /tmp, where there are no permission issues
python3 -m venv /tmp/venv

# Move the virtual environment to the target directory
sudo mv /tmp/venv /var/www/html/api/venv

# Change ownership of the app directory and virtual environment to the correct user


# Activate the virtual environment and install the required packages
source /var/www/html/api/venv/bin/activate 
pip install --break-system-packages --no-cache-dir -r /tmp/requirements.txt


# Set up MySQL database and user
sudo mysql -e "CREATE DATABASE IF NOT EXISTS webapp_db;"
sudo mysql -e "CREATE USER 'webapp_user'@'localhost' IDENTIFIED BY 'password';"
sudo mysql -e "GRANT ALL PRIVILEGES ON webapp_db.* TO 'webapp_user'@'localhost';"
sudo mysql -e "FLUSH PRIVILEGES;"

