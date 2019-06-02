#!/bin/sh
PATH=/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/sbin:/usr/local/bin
export GOOGLE_APPLICATION_CREDENTIALS="/home/pi/google_sdk_key.json"
python3 /home/pi/p2000/p2000.py "$@" > /home/pi/p2000/output.txt
