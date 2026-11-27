#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script with sudo or as root." >&2
  exit 1
fi

DEPLOY_USER="${1:-${SUDO_USER:-}}"
if [[ -z "${DEPLOY_USER}" ]]; then
  echo "Usage: sudo ./bootstrap-centos.sh <ssh-deploy-user>" >&2
  exit 1
fi

dnf -y install dnf-plugins-core
dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
dnf -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable --now docker
usermod -aG docker "${DEPLOY_USER}"

install -d -m 0750 -o "${DEPLOY_USER}" -g "${DEPLOY_USER}" /root/peter_kukurelo/form-automation-backend

if systemctl is-active --quiet firewalld; then
  firewall-cmd --permanent --add-service=http
  firewall-cmd --permanent --add-service=https
  firewall-cmd --reload
fi

echo "Docker and Compose are ready. Deployment directory: /root/peter_kukurelo/form-automation-backend"
echo "Log out and back in so ${DEPLOY_USER} receives Docker group access."
