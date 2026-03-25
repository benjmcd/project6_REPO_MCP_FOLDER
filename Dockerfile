# Use a lightweight, stable Node image
FROM node:20-slim

# Install git (required for Claude to read history/context) and basic tools
RUN apt-get update && apt-get install -y git curl bash && rm -rf /var/lib/apt/lists/*

# Install Claude Code globally
RUN npm install -g @anthropic-ai/claude-code

# Set the working directory inside the container
WORKDIR /workspace

# Set bash as the default command so we can log in interactively
CMD ["/bin/bash"]