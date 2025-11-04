#!/bin/sh
set -e

# Get API URL from environment variable or use default
API_HOST="${API_HOST:-localhost}"

echo "Configuring frontend with API_HOST: ${API_HOST}"

# Replace API_HOST_PLACEHOLDER in nginx config with actual URL
sed -i "s|API_HOST_PLACEHOLDER|${API_HOST}|g" /etc/nginx/conf.d/default.conf

echo "Nginx configuration updated successfully"
cat /etc/nginx/conf.d/default.conf

# Generate runtime environment configuration file
echo "Generating runtime environment configuration..."
cat > /usr/share/nginx/html/env.js <<EOF
// Runtime environment configuration
// This file is generated at container startup
window.ENV = {
  CHATKIT_DOMAIN_KEY: '${VITE_CHATKIT_DOMAIN_KEY:-}',
  APPLICATIONINSIGHTS_CONNECTION_STRING: '${APPLICATIONINSIGHTS_CONNECTION_STRING:-}'
};
console.log('Runtime environment loaded:', window.ENV);
EOF

echo "Runtime configuration generated:"
cat /usr/share/nginx/html/env.js

# Execute CMD
exec "$@"
