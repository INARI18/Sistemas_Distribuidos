#!/usr/bin/env python3
import sys
import time
import os

role = sys.argv[1] if len(sys.argv) > 1 else "patient"
identifier = sys.argv[2] if len(sys.argv) > 2 else "0"

print(f"Starting role={role} id={identifier}")

if role == "patient":
    # very small simulation: instantiate class if available
    try:
        from src.patient import pacient
        p = pacient()
        print(f"Patient {identifier}: memory={p.memory}")
    except Exception as e:
        print(f"Patient runner: could not import patient class: {e}")

elif role == "health-post":
    try:
        from src.health_post import health_post
        h = health_post()
        print(f"HealthPost {identifier}: initialized")
    except Exception as e:
        print(f"HealthPost runner: import error: {e}")

elif role == "sus-db":
    print(f"SUS DB {identifier}: running (no-op)")

elif role == "national-db":
    print(f"National DB {identifier}: running (no-op)")

else:
    print(f"Unknown role {role}")

# keep container alive for observation
try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    pass
