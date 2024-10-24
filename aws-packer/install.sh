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


# sudo systemctl enable mysql
