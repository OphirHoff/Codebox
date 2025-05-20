@echo off

cd server\src

start cmd /c "py db\remote\database_tcp_server.py"
py server.py localhost

cd ..\..