# ChromeDriver Service - Quick Start

## 🚀 Start the Service

```bash
./start_chromedriver_service.sh
```

**This starts:**
- Django server → http://127.0.0.1:8000/
- ChromeDriver → http://127.0.0.1:9515/

**To stop:** Press `Ctrl+C`

---

## ✅ Prerequisites

### Install ChromeDriver (one-time setup)

**macOS:**
```bash
brew install chromedriver
```

**Linux:**
```bash
wget https://chromedriver.storage.googleapis.com/LATEST_RELEASE
CHROMEDRIVER_VERSION=$(cat LATEST_RELEASE)
wget https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip
unzip chromedriver_linux64.zip
sudo mv chromedriver /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver
```

### Install Selenium (for testing)
```bash
pip install selenium
```

---

## 🧪 Run Test

**Terminal 1:**
```bash
./start_chromedriver_service.sh
```

**Terminal 2:**
```bash
python test_chromedriver.py
```

---

## 🔧 Advanced Usage

### Custom Ports
```bash
python manage.py chromedriver_service --port 8080 --chromedriver-port 9516
```

### ChromeDriver Only (no Django)
```bash
python manage.py chromedriver_service --no-server
```

### Custom ChromeDriver Path
```bash
python manage.py chromedriver_service --chromedriver-path /path/to/chromedriver
```

---

## 📝 Use in Your Code

```python
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

# Connect to ChromeDriver service
service = Service()
service.port = 9515

driver = webdriver.Chrome(service=service)
driver.get("http://127.0.0.1:8000/")

# Your automation code here...

driver.quit()
```

---

## 📚 Documentation

- **Full docs:** `CHROMEDRIVER_SERVICE.md`
- **Summary:** `CHROMEDRIVER_SUMMARY.md`
- **Example test:** `test_chromedriver.py`

---

## ⚠️ Troubleshooting

### ChromeDriver not found
```bash
# Install it:
brew install chromedriver  # macOS

# Or specify path:
python manage.py chromedriver_service --chromedriver-path /path/to/chromedriver
```

### Port already in use
```bash
# Use different ports:
python manage.py chromedriver_service --port 8001 --chromedriver-port 9516
```

### Process won't stop
```bash
# Force kill:
lsof -ti:8000 | xargs kill -9  # Django
lsof -ti:9515 | xargs kill -9  # ChromeDriver
```

---

## 🎯 That's It!

You're ready to automate browser testing for the Tax Budget Allocator app.
