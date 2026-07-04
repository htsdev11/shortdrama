#!/bin/bash

# Change to project directory
cd /home/tayyab-saeed/PycharmProjects/shortdrama
# Activate virtual environment
source .venv/bin/activate

# Run Retry Episodes scraper
python retry_episodes_scraper.py

# Deactivate virtual environment
deactivate