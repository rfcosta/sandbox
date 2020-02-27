#!/bin/env python3

# This script is used to take regions in and out of server

import sys, os

EXPECTED_STATE_FILE = "/opt/aed/shp/flags/expected_state"

def save_expected_state(state):
    if os.path.isfile(EXPECTED_STATE_FILE):
        os.remove(EXPECTED_STATE_FILE)
    text_file = open(EXPECTED_STATE_FILE, "w")
    text_file.write(state)
    text_file.close()
    os.chmod(EXPECTED_STATE_FILE, 0o777)

def get_expected_state():
    try:
        text_file = open(EXPECTED_STATE_FILE, "r")
        expected_state = text_file.read()
        text_file.close()
    except:
        expected_state = "enabled"
    return expected_state


expected_state = get_expected_state()
os.chdir("/etc/httpd/conf.d")

if len(sys.argv) == 2:
    new_state = sys.argv[1]
else:
    raise ValueError("Missing argument")

if "enabled" == new_state.lower():
    save_expected_state(new_state)
elif "disabled" == new_state.lower():
    save_expected_state(new_state)
else:
    raise ValueError("Invalid State")

print("Setting Region State to " + new_state)
print("It can take up to 2 minutes to take affect.")
