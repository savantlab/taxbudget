# ChromeDriver Service

A Django management command that starts the Tax Budget Allocator app with ChromeDriver for automated testing and browser automation.

## Features

✨ **Integrated Service Management**
- Starts Django development server and ChromeDriver together
- Graceful shutdown handling (Ctrl+C stops both services)
- Process monitoring and automatic cleanup
- Signal handling for SIGINT and SIGTERM

🔧 **Configurable**
- Custom ports for Django and ChromeDriver
- Optional ChromeDriver-only mode
- Custom ChromeDriver executable path

🛡️ **Robust**
- Automatic process cleanup on errors
- Cross-platform support (macOS, Linux, Windows)
- Graceful handling of unexpected process termination

## Prerequisites

### 1. Install ChromeDriver

#### macOS (Homebrew)
```bash
brew install chromedriver
```

#### Linux
```bash
# Download ChromeDriver
wget https://chromedriver.storage.googleapis.com/LATEST_RELEASE
CHROMEDRIVER_VERSION=$(cat LATEST_RELEASE)
wget https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip
unzip chromedriver_linux64.zip
sudo mv chromedriver /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver
```

#### Manual Installation
Download from: https://chromedriver.chromium.org/downloads

### 2. Install Selenium (for testing)
```bash
pip install selenium
```

## Usage

### Quick Start

```bash
# Start both Django server and ChromeDriver
./start_chromedriver_service.sh
```

This will start:
- Django server at http://127.0.0.1:8000/
- ChromeDriver at http://127.0.0.1:9515/

Press `Ctrl+C` to stop both services gracefully.

### Manual Start

```bash
python manage.py chromedriver_service
```

### Advanced Options

#### Custom Ports
```bash
python manage.py chromedriver_service --port 8080 --chromedriver-port 9516
```

#### ChromeDriver Only (No Django Server)
```bash
python manage.py chromedriver_service --no-server
```

#### Custom ChromeDriver Path
```bash
python manage.py chromedriver_service --chromedriver-path /path/to/chromedriver
```

## Testing

Run the included test script to verify the service is working:

```bash
# Terminal 1: Start the service
./start_chromedriver_service.sh

# Terminal 2: Run the test
python test_chromedriver.py
```

The test script will:
1. Connect to ChromeDriver
2. Open the Tax Budget Allocator app
3. Fill out the allocation form
4. Verify form validation is working
5. Close the browser

## Example: Using ChromeDriver with Selenium

```python
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# Configure Chrome options
chrome_options = Options()
chrome_options.add_argument('--headless')  # Optional: run in headless mode

# Connect to ChromeDriver service
service = Service()
service.port = 9515

# Create driver instance
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    # Navigate to the app
    driver.get("http://127.0.0.1:8000/")
    
    # Your automation code here...
    print(f"Page title: {driver.title}")
    
finally:
    driver.quit()
```

## Architecture

### Service Flow

```
start_chromedriver_service.sh
    ↓
python manage.py chromedriver_service
    ↓
    ├─→ Start Django Server (subprocess)
    │   └─→ http://127.0.0.1:8000/
    │
    ├─→ Start ChromeDriver (subprocess)
    │   └─→ http://127.0.0.1:9515/
    │
    └─→ Monitor processes & handle signals
        └─→ Ctrl+C → Graceful shutdown
```

### Signal Handling

The service registers handlers for:
- **SIGINT** (Ctrl+C): Graceful shutdown
- **SIGTERM**: Graceful shutdown
- **Process monitoring**: Auto-cleanup if subprocess dies

### Shutdown Process

1. Receive shutdown signal (SIGINT/SIGTERM)
2. Stop ChromeDriver process (SIGTERM → wait → SIGKILL if needed)
3. Stop Django server process (SIGTERM → wait → SIGKILL if needed)
4. Clean up and exit

## Command-Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--port` | 8000 | Django server port |
| `--chromedriver-port` | 9515 | ChromeDriver port |
| `--no-server` | False | Skip starting Django server |
| `--chromedriver-path` | `chromedriver` | Path to ChromeDriver executable |

## Troubleshooting

### ChromeDriver not found
```
❌ ChromeDriver not found at "chromedriver"
```

**Solution**: Install ChromeDriver or specify the path:
```bash
python manage.py chromedriver_service --chromedriver-path /path/to/chromedriver
```

### Port already in use
```
Error: That port is already in use.
```

**Solution**: Use different ports:
```bash
python manage.py chromedriver_service --port 8001 --chromedriver-port 9516
```

### ChromeDriver version mismatch
```
SessionNotCreatedException: Chrome version must be ...
```

**Solution**: Update ChromeDriver to match your Chrome version:
```bash
# macOS
brew upgrade chromedriver

# Or download manually from:
# https://chromedriver.chromium.org/downloads
```

### Process won't stop
If processes don't stop gracefully, manually kill them:
```bash
# Find and kill processes
lsof -ti:8000 | xargs kill -9  # Django
lsof -ti:9515 | xargs kill -9  # ChromeDriver
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install selenium
      
      - name: Install ChromeDriver
        run: |
          wget https://chromedriver.storage.googleapis.com/LATEST_RELEASE
          CHROMEDRIVER_VERSION=$(cat LATEST_RELEASE)
          wget https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip
          unzip chromedriver_linux64.zip
          sudo mv chromedriver /usr/local/bin/
          sudo chmod +x /usr/local/bin/chromedriver
      
      - name: Run migrations
        run: python manage.py migrate
      
      - name: Start service in background
        run: |
          python manage.py chromedriver_service &
          sleep 5
      
      - name: Run tests
        run: python test_chromedriver.py
      
      - name: Stop service
        run: pkill -f chromedriver_service
```

## Use Cases

1. **Automated Testing**: Run Selenium tests against your app
2. **Browser Automation**: Automate form submissions and interactions
3. **Screenshot Testing**: Capture screenshots for visual regression testing
4. **Web Scraping**: Test scraping logic against your own app
5. **E2E Testing**: Full end-to-end testing in CI/CD pipelines

## License

MIT License
