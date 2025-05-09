@echo off

rem Create docker image
docker build -t python_runner ..\docker

echo.
echo [+] Image build finished