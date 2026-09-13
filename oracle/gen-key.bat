@echo off
echo y | ssh-keygen -t rsa -b 2048 -f C:\Users\veera\.ssh\id_rsa_new -N "" -m PEM
echo Done
pause
