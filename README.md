<p align="center">
  
<img width="324" height="259" alt="Untitled" src="https://github.com/user-attachments/assets/f43d022c-3faf-49d5-afcb-83e12aa9ad7a" />

</p>


<h1 align="center">Codebox</h1>
<p align="center"><i>One Box. Limitless Power.</i></p>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.0.0-blue" alt="Version 1.0.0"/>
</p>

---

## Overview

**Codebox** is a lightweight web platform for editing, storing and running Python code remotely—allowing users to execute code on demand with no setup.

With cloud-based files storage, a fast & modern editor, and secure server-side code execution, Codebox offers a flexible yet safe environment for experimenting with code directly from the browser.

---

## Core Features

- **Remote Code Execution**  – Run Python code safely on the server—no need to install anything locally
- **Secure Login & Registry** – Allowing users to safely access their account 
- **Cloud File Storage** – Save and manage your files in the cloud, accessible from anywhere
- **Create whole projects from your browser** – The system design allows your several Python modules to work together
- **Modern Code Editor** – Enjoy the benefits of the beloved monaco editor, primarily known as VS Code's editor engine
- **Secure Sandbox** – Server-side code execution is isolated and protected, preventing unsafe operations
- **Zero Setup**  
  Just open the browser and start coding—ideal for fast testing, learning, or demos

---

## Technologies Used

- **Docker containers** for secure, sandboxed code execution  
- **TLS-encrypted communication** ensuring data privacy   
- **WebSocket** protocol for real-time, bidirectional communication  
- **RSA & AES** Manual use for a secure connection with database
- **SQLite** lightweight relational database  
- Custom-built **file tracking system** for efficient file management


---

## Architecture

Codebox's system is based on four main components:

### Web Client

- **Web-Based IDE** – Built with HTML, CSS, and JavaScript, embedding the Monaco editor
- **Secure Auth** – User registration and login interface  
- **Cloud Storage UI** – Hierarchical file/folder tree with real-time updates  
- **Remote Execution** – Sends code for execution and displays output/input within the browser  
- **WebSocket Connection** – Enables real-time communication with the backend for code execution and other queries  

### HTTPS Server

- **Static Hosting** – Serves frontend assets (HTML/CSS/JS) to the client  
- **Secure Transport** – Using TLS for encryption and certificate-based authentication
- Only responsible for serving the client application over HTTP  

### Central Server  

- **TLS-Secured WebSocket** – Encrypted bidirectional communication with the client  
- **Main communication** – Handles core business logic via a uniquely designed message protocol
- **File Management** – Efficiently manages and tracks users' cloud-stored files and folders using custom algorithms  
- **Sandbox Integration** – Executes code securely inside Docker containers with resource limits  
- **Database Connection Pooling** – Maintains multiple active connections with the database for efficient querying

### Database Server

- **SQLite-Based** – Stores user accounts, credentials, and users' files structures  
- **Secure Storage** – Passwords are hashed with salt and pepper for security  
- **Encrypted Communication** – Secure connection to Central Server using RSA and (manually implemented)  
- **Low Overhead** – Lightweight and designed for fast, simple queries  

---

## Getting Started

### Docker Container Setup

Setting up the container image:
```bash
cd server/scripts
setup_docker_img.bat
```

After that, Run Docker Desktop (`WSL-2` installed required)  

### Database Server Deployment

```bash
cd server\src
python3 db\remote\database_socket_server.py
``` 

### Central Server Deployment

```bash
cd server\src
python3 server.py <database_ip>
``` 
Where:
- `database_ip`: IP address of the database server host

Note: Running the main server starts automatically both the HTTP and the WebSocket Server.

### Client Access

Access the app at `https://<main_server_ip>`

---

## 💻 System Requirements

- **Server**: Python 3.x, WSL-2, Docker Desktop
- **Client**: Web browser

---

<p align="center">
  Joyfully crafted by <strong>Ophir Hoffman</strong> | &copy; 2025
</p>
