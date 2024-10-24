#!/bin/bash

# Prevent interactive prompts from blocking the install
export DEBIAN_FRONTEND=noninteractive

# Update the instance and install dependencies
sudo apt-get update -y
sudo apt-get upgrade -y

# Install Python and venv
sudo apt-get install -y python3 python3-venv

# Create a directory for the Flask app with the correct permissions
sudo mkdir -p /var/www/html/api
sudo chown -R ubuntu:ubuntu /var/www/html/api  # Change ownership to the default user

# Move the application files to the directory
sudo mv /tmp/*.py /var/www/html/api/
sudo mv /tmp/requirements.txt /var/www/html/api/

# Create a virtual environment in the app directory
python3 -m venv /var/www/html/api/venv

# Activate the virtual environment
source /var/www/html/api/venv/bin/activate

# Install dependencies within the virtual environment
pip install --no-cache-dir -r /var/www/html/api/requirements.txt

# Deactivate the virtual environment
deactivate
