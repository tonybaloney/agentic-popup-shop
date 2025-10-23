# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install UV
RUN pip install uv

# Create workspace directory structure to match expected paths
RUN mkdir -p /workspace/data

# Copy the entire app structure to maintain relative paths
# Copy shared package first
COPY ../shared /app/shared

# Copy MCP server code
COPY . /app/mcp

# Set working directory to MCP server
WORKDIR /app/mcp

# Install dependencies using UV
# This will install the MCP server and the local shared package
RUN uv sync --frozen

# Create a symlink so the database path matches what the code expects
# The database will be mounted at /app/data/retail.db and linked to /workspace/data/retail.db
RUN ln -sf /app/data/retail.db /workspace/data/retail.db

# Expose port (if needed for HTTP MCP server)
EXPOSE 8002

# Set environment variables for the MCP server
ENV PYTHONPATH=/app/mcp:/app/shared/src
ENV PYTHONUNBUFFERED=1

# Create a startup script to handle the database symlink at runtime
RUN echo '#!/bin/bash\n\
# Ensure the database directory exists\n\
mkdir -p /app/data\n\
mkdir -p /workspace/data\n\
\n\
# Create symlink if database file exists\n\
if [ -f /app/data/retail.db ]; then\n\
    ln -sf /app/data/retail.db /workspace/data/retail.db\n\
    echo "Database linked: /app/data/retail.db -> /workspace/data/retail.db"\n\
else\n\
    echo "Warning: Database file not found at /app/data/retail.db"\n\
fi\n\
\n\
# Start the MCP server\n\
exec uv run python -m github_shop_mcp.supplier_server "$@"\n' > /app/start.sh

RUN chmod +x /app/start.sh

# Use the startup script as the entrypoint
ENTRYPOINT ["/app/start.sh"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Labels
LABEL maintainer="GitHub Shop Team"
LABEL description="MCP Server for GitHub Shop Supplier Management"
LABEL version="0.1.0"