FROM ubuntu:latest

# Install Python
RUN apt update
RUN apt install python3 -y

# Create a non-root user for safety
RUN useradd -m sandboxuser
USER sandboxuser

# Working directory inside the container
WORKDIR /home/sandboxuser/app

# Entrypoint for running user's code
ENTRYPOINT ["python3", "-u", "main.py"]
