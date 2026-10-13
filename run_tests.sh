#!/usr/bin/env bash
# Runs every test with the network blocked. No credentials are needed or read.
set -e
cd "$(dirname "$0")"
env -u ELEVENLABS_API_KEY -u FAL_KEY VIDEO_DIRECTOR_PAID_ENABLED=0 python3 -W error::ResourceWarning -m unittest discover -s tests -t . "$@"
