#!/bin/bash

# Update the instance and install dependencies
sudo apt-get update -y
sudo apt-get upgrade -y

# Install Python and venv
sudo apt-get install -y python3 python3-venv

# Create a directory for the Flask app
sudo mkdir -p /var/www/html/api

# Move the application files to the directory
sudo mv /tmp/*.py /var/www/html/api/
sudo mv /tmp/requirements.txt /var/www/html/api/

# Create a virtual environment
python3 -m venv /var/www/html/api/venv

# Activate the virtual environment
source /var/www/html/api/venv/bin/activate

# Install dependencies within the virtual environment
pip install --no-cache-dir -r /var/www/html/api/requirements.txt

# Deactivate the virtual environment (optional, but good practice)
deactivate
