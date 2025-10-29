#!/usr/bin/env bash

echo "Installing frontend dependencies"
cd /workspace/frontend && npm install

echo "installing dotnet"

curl -sSL https://aspire.dev/install.sh | bash -s -- -q dev
curl -L https://dot.net/v1/dotnet-install.sh -o dotnet-install.sh
chmod +x ./dotnet-install.sh
./dotnet-install.sh --channel 10.0

export PATH="$HOME/.aspire/bin:$HOME/.dotnet:$PATH"
echo 'export PATH="$HOME/.aspire/bin:$HOME/.dotnet:$PATH"' >> ~/.bashrc

curl -LsSf https://astral.sh/uv/install.sh | sh

echo "Setup complete!"
echo "- Python environment: ready"
echo "- Node.js: $(node --version)"
echo "- npm: $(npm --version)"
echo "- .NET SDKs installed:"
dotnet --list-sdks | while read line; do echo "  - $line"; done
echo "- Frontend dependencies: installed"
