#!/bin/sh
# Prosty skrypt do przeładowania listy kanałów (bukietów) w Enigma2

wget -qO - "http://127.0.0.1/web/servicelistreload?mode=0" > /dev/null 2>&1
wget -qO - "http://127.0.0.1/web/servicelistreload?mode=4" > /dev/null 2>&1

exit 0
