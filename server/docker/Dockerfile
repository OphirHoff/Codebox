FROM ubuntu:latest

# Install Python and lsof
RUN apt update
RUN apt install python3 -y lsof

# Create a non-root user for safety
RUN useradd -m sandboxuser

USER sandboxuser
WORKDIR /home/sandboxuser/app
