# Use the official Python 3 image as the base
FROM python:3


# Install system dependencies
# Install system dependencies
RUN apt-get update && \
    apt-get install -y build-essential && \
    # Add any other system dependencies needed for the build here \
    pip install pyinstaller \
        bcrypt

# Set the working directory
WORKDIR /app

# Set the entrypoint to bash
ENTRYPOINT ["/bin/bash"]
