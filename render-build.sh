set -o errexit

STORAGE_DIR=/opt/render/project/.render
CHROME_VERSION=138.0.7204.92
CHROME_DIR=$STORAGE_DIR/chrome

if [[ ! -d $CHROME_DIR ]]; then
  echo "...Downloading Chrome for Testing"
  mkdir -p $CHROME_DIR
  cd $CHROME_DIR

  # Download and unzip Chrome binary
  wget https://storage.googleapis.com/chrome-for-testing-public/$CHROME_VERSION/linux64/chrome-linux64.zip
  unzip chrome-linux64.zip
  rm chrome-linux64.zip

  # Download and unzip ChromeDriver
  wget https://storage.googleapis.com/chrome-for-testing-public/$CHROME_VERSION/linux64/chromedriver-linux64.zip
  unzip chromedriver-linux64.zip
  rm chromedriver-linux64.zip

  # Optional: symlink for easier access
  ln -sf "$CHROME_DIR/chrome-linux64/chrome" "$CHROME_DIR/chrome"
  ln -sf "$CHROME_DIR/chromedriver-linux64/chromedriver" "$CHROME_DIR/chromedriver"

  cd $HOME/project/src  # Return to project directory
else
  echo "...Using Chrome from cache"
fi
