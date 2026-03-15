#!/usr/bin/env bash
# exit on error
set -o errexit

# 1. Install your Python requirements first
pip install -r requirements.txt

# 2. Define the exact Render path
STORAGE_DIR=/opt/render/project/.render

# 3. THE FIX: Forcibly delete the old corrupted Chrome folder so Render downloads a fresh copy
rm -rf $STORAGE_DIR/chrome

echo "...Downloading Chrome and ChromeDriver"
mkdir -p $STORAGE_DIR/chrome
cd $STORAGE_DIR/chrome

# Download Chrome for Testing
wget https://storage.googleapis.com/chrome-for-testing-public/122.0.6261.94/linux64/chrome-linux64.zip
unzip chrome-linux64.zip

# THE FIX: Move ALL files and folders (*), not just the executable!
mv chrome-linux64/* ./

# Download ChromeDriver
wget https://storage.googleapis.com/chrome-for-testing-public/122.0.6261.94/linux64/chromedriver-linux64.zip
unzip chromedriver-linux64.zip
mv chromedriver-linux64/chromedriver ./

# Clean up the zip files and empty folders
rm -rf chrome-linux64 chrome-linux64.zip chromedriver-linux64 chromedriver-linux64.zip