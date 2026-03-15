#!/usr/bin/env bash
# exit on error
set -o errexit

# 1. Install your Python requirements first
pip install -r requirements.txt

# 2. Define the exact Render path your Python code is looking for
STORAGE_DIR=/opt/render/project/.render

if [[ ! -d $STORAGE_DIR/chrome ]]; then
  echo "...Downloading Chrome and ChromeDriver"
  mkdir -p $STORAGE_DIR/chrome
  cd $STORAGE_DIR/chrome
  
  # Download Chrome for Testing
  wget https://storage.googleapis.com/chrome-for-testing-public/122.0.6261.94/linux64/chrome-linux64.zip
  unzip chrome-linux64.zip
  mv chrome-linux64/chrome ./
  
  # Download ChromeDriver
  wget https://storage.googleapis.com/chrome-for-testing-public/122.0.6261.94/linux64/chromedriver-linux64.zip
  unzip chromedriver-linux64.zip
  mv chromedriver-linux64/chromedriver ./
  
  # Clean up the zip files
  rm -rf chrome-linux64 chrome-linux64.zip chromedriver-linux64 chromedriver-linux64.zip
else
  echo "...Chrome is already installed in the cache"
fi