FROM ubuntu:latest

# Install Python and strace
RUN apt update
RUN apt install python3 -y lsof

# Create a non-root user for safety
RUN useradd -m sandboxuser

# Set PATH explicitly (adds /usr/sbin where strace lives)
# ENV PATH="/usr/sbin:/usr/bin:/bin:$PATH"

USER sandboxuser
WORKDIR /home/sandboxuser/app
