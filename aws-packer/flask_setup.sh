#!/bin/bash

# Update the instance and install dependencies
sudo apt-get update -y
sudo apt-get install -y python3 python3-venv python3-pip jq awscli amazon-cloudwatch-agent

# Move Flask application code to the desired directory
sudo mkdir -p /var/www/html/api
sudo mv /tmp/* /var/www/html/api/

# Create a system user for running the Flask application
sudo groupadd -f csye6225
sudo useradd -r -g csye6225 -s /usr/sbin/nologin csye6225

# Ensure correct ownership of the application directory
sudo chown -R csye6225:csye6225 /var/www/html/api

# Create and activate Python virtual environment
cd /var/www/html/api
python3 -m venv venv
source venv/bin/activate

# Install application dependencies
pip install --no-cache-dir -r requirements.txt

# Fetch secrets and environment variables from AWS Secrets Manager
DB_SECRETS=$(aws secretsmanager get-secret-value --secret-id database-credentials --query 'SecretString' --output text)
EMAIL_SECRETS=$(aws secretsmanager get-secret-value --secret-id email-service-credentials --query 'SecretString' --output text)

DB_HOST=$(echo $DB_SECRETS | jq -r '.DB_HOST')
DB_USER=$(echo $DB_SECRETS | jq -r '.DB_USER')
DB_PASSWORD=$(echo $DB_SECRETS | jq -r '.DB_PASSWORD')
DB_NAME=$(echo $DB_SECRETS | jq -r '.DB_NAME')
FROM_EMAIL=$(echo $EMAIL_SECRETS | jq -r '.FROM_EMAIL')
DOMAIN_NAME=$(echo $EMAIL_SECRETS | jq -r '.DOMAIN_NAME')
SENDGRID_API_KEY=$(echo $EMAIL_SECRETS | jq -r '.SENDGRID_API_KEY')
KMS_KEY_ALIAS=$(aws kms describe-key --key-id alias/sensitive-data-kms-key --query 'KeyMetadata.Arn' --output text)

# Create the environment variables file
sudo tee /etc/flask-api.env <<EOL
AWS_REGION=us-east-2
DB_HOST=$DB_HOST
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
DB_NAME=$DB_NAME
FROM_EMAIL=$FROM_EMAIL
DOMAIN_NAME=$DOMAIN_NAME
SENDGRID_API_KEY=$SENDGRID_API_KEY
KMS_KEY_ALIAS=$KMS_KEY_ALIAS
EOL

# Set ownership and permissions for the environment file
sudo chown csye6225:csye6225 /etc/flask-api.env
sudo chmod 600 /etc/flask-api.env

# Create the systemd service for the Flask API
sudo tee /etc/systemd/system/flask-api.service <<EOL
[Unit]
Description=Flask API Service
After=network.target

[Service]
User=csye6225
Group=csye6225
WorkingDirectory=/var/www/html/api
EnvironmentFile=/etc/flask-api.env
ExecStart=/var/www/html/api/venv/bin/python /var/www/html/api/app.py
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=flask-api
Restart=always

[Install]
WantedBy=multi-user.target
EOL

# Reload systemd to apply changes and enable Flask service on startup
sudo systemctl daemon-reload
sudo systemctl enable flask-api.service

# Start the Flask service
sudo systemctl start flask-api.service

# Verify Flask service status
if sudo systemctl is-active --quiet flask-api.service; then
    echo "Flask API service started successfully."
else
    echo "Flask API service failed to start. Check logs for details."
    exit 1
fi

# Configure and start CloudWatch Agent
sudo mkdir -p /opt/aws/amazon-cloudwatch-agent/etc/
sudo tee /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json <<EOL
{
  "agent": {
    "metrics_collection_interval": 60,
    "run_as_user": "root"
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/syslog",
            "log_group_name": "flask-app-logs",
            "log_stream_name": "{instance_id}",
            "timezone": "UTC"
          }
        ]
      }
    }
  }
}
EOL

sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a start -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json

# Verify CloudWatch Agent status
if sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a status | grep "running"; then
    echo "CloudWatch Agent started successfully."
else
    echo "CloudWatch Agent failed to start. Check configuration for details."
    exit 1
fi

echo "Flask setup script completed successfully."