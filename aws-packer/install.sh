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

# Install and configure CloudWatch Agent
# Download the CloudWatch Agent package directly from Amazon's repository
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb

# Install the downloaded CloudWatch Agent package
sudo dpkg -i -E ./amazon-cloudwatch-agent.deb

# Create CloudWatch configuration directory if it doesn't already exist
sudo mkdir -p /opt/aws/amazon-cloudwatch-agent/etc/

# Create a basic CloudWatch configuration JSON for log collection
cat <<EOF | sudo tee /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/syslog",
            "log_group_name": "webapp-syslog",
            "log_stream_name": "{instance_id}"
          }
        ]
      }
    }
  }
}
EOF

# Start the CloudWatch Agent with the specified configuration
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a start -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
