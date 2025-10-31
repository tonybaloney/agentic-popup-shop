#!/bin/sh
set -e

# Get API URL from environment variable or use default
API_HOST="${API_HOST:-localhost}"

echo "Configuring frontend with API_HOST: ${API_HOST}"

# Replace API_HOST_PLACEHOLDER in nginx config with actual URL
sed -i "s|API_HOST_PLACEHOLDER|${API_HOST}|g" /etc/nginx/conf.d/default.conf

echo "Nginx configuration updated successfully"
cat /etc/nginx/conf.d/default.conf

# Execute CMD
exec "$@"
