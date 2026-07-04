#!/bin/bash

# Change to project directory
cd /home/tayyab-saeed/PycharmProjects/shortdrama

# Activate virtual environment
source .venv/bin/activate

# Run ForYou scraper
python foryou_scraper.py

# Deactivate virtual environment
deactivate