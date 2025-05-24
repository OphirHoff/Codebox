@echo off

cd server\src

start cmd /c "python3 db\remote\database_socket_server.py"
python3 server.py localhost

cd ..\..