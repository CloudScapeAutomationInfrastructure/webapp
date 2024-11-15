#!/bin/bash

# Prevent interactive prompts from blocking the install
export DEBIAN_FRONTEND=noninteractive

# Update the system and install required dependencies
sudo apt-get update -y
sudo apt-get upgrade -y

# Install Python and required tools
sudo apt-get install -y python3 python3-venv python3-pip wget unzip

# Install CloudWatch Agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i amazon-cloudwatch-agent.deb

# Create a directory for the application
sudo mkdir -p /var/www/html/api
sudo chown -R ubuntu:ubuntu /var/www/html/api  # Change ownership to the default user

# Move application files to the designated directory
sudo mv /tmp/*.py /var/www/html/api/
sudo mv /tmp/requirements.txt /var/www/html/api/

# Set up Python virtual environment
python3 -m venv /var/www/html/api/venv
source /var/www/html/api/venv/bin/activate

# Install Python dependencies
pip install --no-cache-dir -r /var/www/html/api/requirements.txt

# Deactivate the virtual environment
deactivate

# Configure CloudWatch Agent to monitor logs and metrics
sudo mkdir -p /opt/aws/amazon-cloudwatch-agent/etc/
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
  },
  "metrics": {
    "append_dimensions": {
      "AutoScalingGroupName": "\${aws:AutoScalingGroupName}"
    },
    "metrics_collected": {
      "cpu": {
        "measurement": [
          "usage_idle",
          "usage_system",
          "usage_user"
        ],
        "metrics_collection_interval": 60
      },
      "disk": {
        "measurement": [
          "used_percent"
        ],
        "metrics_collection_interval": 60
      },
      "memory": {
        "measurement": [
          "used_percent"
        ],
        "metrics_collection_interval": 60
      }
    }
  }
}
EOF

# Start CloudWatch Agent
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a start -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
