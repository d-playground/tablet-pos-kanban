#!/bin/bash

# Update system and install EPEL
sudo yum update -y
sudo yum install -y epel-release

# Add Docker repository
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# Install Docker and Docker Compose
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add current user to docker group
sudo usermod -aG docker $USER
sudo systemctl restart docker

# Install Git
sudo yum install -y git

# Clone the repository
git clone https://github.com/d-playground/tablet-pos-kanban.git
cd tablet-pos-kanban

# Set proper permissions
sudo chown -R $USER:$USER .

# Build and start containers
sudo docker compose up -d --build

echo "Deployment complete! Please log out and log back in for the docker group changes to take effect."
echo "After logging back in, you can run docker commands without sudo."
echo "To see the logs, run: docker compose logs -f"