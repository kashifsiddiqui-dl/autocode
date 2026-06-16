#!/bin/bash
set -euo pipefail

# Log all output for debugging
exec > >(tee /var/log/user-data.log) 2>&1
echo "=== User Data Script Start: $(date) ==="

# System updates
yum update -y

# Install Docker
amazon-linux-extras install docker -y || yum install -y docker
systemctl enable docker
systemctl start docker

# Install Docker Compose v2
DOCKER_COMPOSE_VERSION="v2.29.2"
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL "https://github.com/docker/compose/releases/download/$${DOCKER_COMPOSE_VERSION}/docker-compose-linux-x86_64" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Add ec2-user to docker group
usermod -aG docker ec2-user

# Install CloudWatch agent
yum install -y amazon-cloudwatch-agent
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json <<'CWCONFIG'
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
            "file_path": "/var/log/docker/*.log",
            "log_group_name": "/${project_name}/${environment}/docker",
            "log_stream_name": "{instance_id}",
            "retention_in_days": 30
          },
          {
            "file_path": "/var/log/user-data.log",
            "log_group_name": "/${project_name}/${environment}/user-data",
            "log_stream_name": "{instance_id}",
            "retention_in_days": 7
          }
        ]
      }
    }
  },
  "metrics": {
    "namespace": "${project_name}/${environment}",
    "metrics_collected": {
      "cpu": {
        "measurement": ["cpu_usage_idle", "cpu_usage_user", "cpu_usage_system"],
        "totalcpu": true
      },
      "disk": {
        "measurement": ["used_percent"],
        "resources": ["*"]
      },
      "mem": {
        "measurement": ["mem_used_percent", "mem_available"]
      }
    },
    "append_dimensions": {
      "InstanceId": "$${aws:InstanceId}"
    }
  }
}
CWCONFIG

/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config -m ec2 \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json -s

# Format and mount Qdrant EBS volume (if not already formatted)
DEVICE="/dev/xvdf"
MOUNT_POINT="/data/qdrant"
mkdir -p $MOUNT_POINT

if ! blkid "$DEVICE" > /dev/null 2>&1; then
  mkfs.xfs "$DEVICE"
fi

mount "$DEVICE" "$MOUNT_POINT"
echo "$DEVICE $MOUNT_POINT xfs defaults,nofail 0 2" >> /etc/fstab
chown ec2-user:ec2-user "$MOUNT_POINT"

# Configure Docker log rotation
cat > /etc/docker/daemon.json <<'DOCKERCONFIG'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "5"
  }
}
DOCKERCONFIG
systemctl restart docker

# Login to ECR
aws ecr get-login-password --region ${aws_region} | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.${aws_region}.amazonaws.com

echo "=== User Data Script Complete: $(date) ==="
