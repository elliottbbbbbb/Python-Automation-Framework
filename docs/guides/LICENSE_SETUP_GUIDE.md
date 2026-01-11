# License System Setup Guide

This guide walks you through setting up and deploying the complete license authentication system for the OSRS Bot Framework.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Backend Setup](#backend-setup)
3. [Testing the System](#testing-the-system)
4. [Deployment](#deployment)
5. [Creating Licenses](#creating-licenses)
6. [Client Usage](#client-usage)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL (production) or SQLite (development)
- Domain name (for production deployment)

### 1. Install Dependencies

For the **bot client**:
```bash
pip install -r requirements.txt
# or
pip install -e .
```

For the **license server**:
```bash
cd license-server
pip install -r requirements.txt
```

### 2. Configure Environment

Create `license-server/.env`:
```env
DATABASE_URL=sqlite:///./licenses.db
API_KEY=your-secret-api-key-change-this-to-something-random
ENVIRONMENT=development
SECRET_KEY=your-secret-key-change-this
HOST=0.0.0.0
PORT=8000
```

### 3. Start the License Server

```bash
cd license-server
uvicorn app.main:app --reload
```

The server will start at `http://localhost:8000`

### 4. Create a Test License

```bash
curl -X POST "http://localhost:8000/api/v1/admin/licenses?duration_hours=24&notes=test_license" \
  -H "X-API-Key: your-secret-api-key-change-this-to-something-random"
```

Response will include your license key (format: `XXXX-XXXX-XXXX-XXXX`).

### 5. Run the Bot

When you start any bot script, it will:
1. Check for a valid license
2. Show activation dialog if no license found
3. Enter the license key from step 4
4. Start the bot if license is valid

---

## Backend Setup

### Database Configuration

#### Development (SQLite)

SQLite is perfect for testing and development:

```env
DATABASE_URL=sqlite:///./licenses.db
```

No additional setup required!

#### Production (PostgreSQL)

For production, use PostgreSQL:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/licenses
```

**Setup PostgreSQL:**

1. Install PostgreSQL
2. Create database:
   ```sql
   CREATE DATABASE licenses;
   ```
3. Update `.env` with connection string

### API Security

The admin endpoints require an API key. Generate a secure one:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Add to `.env`:
```env
API_KEY=your_generated_key_here
```

### Rate Limiting

The server includes rate limiting to prevent abuse:
- Activation endpoint: 10 requests/minute per IP
- Validation endpoint: 30 requests/minute per IP

---

## Testing the System

### 1. Test Hardware Fingerprinting

```bash
python -m osrsbot.services.hardware_fingerprint
```

This will display your machine's unique fingerprint.

### 2. Test License Service

Create `test_license.py`:

```python
from osrsbot.services.license_service import LicenseService

# Initialize service
service = LicenseService(api_url="http://localhost:8000")

# Activate a license
try:
    result = service.activate("YOUR-LICENSE-KEY-HERE")
    print(f"Activated: {result}")
except Exception as e:
    print(f"Error: {e}")

# Validate license
try:
    is_valid = service.validate()
    print(f"Valid: {is_valid}")
except Exception as e:
    print(f"Error: {e}")

# Check status
status = service.get_license_status()
print(f"Status: {status}")
```

### 3. Test License Dialog

```bash
python -m osrsbot.ui.license_dialog
```

This will show the activation GUI.

### 4. API Health Check

```bash
curl http://localhost:8000/health
```

---

## Deployment

### Option 1: Railway.app (Recommended)

**Pros:** Easy setup, auto-deploy, built-in PostgreSQL
**Cost:** Free tier available, $5/mo for production

**Steps:**

1. Push code to GitHub:
   ```bash
   git add license-server/
   git commit -m "Add license server"
   git push
   ```

2. Go to [railway.app](https://railway.app)
3. Click "New Project" → "Deploy from GitHub"
4. Select your repository
5. Set root directory to `license-server`
6. Add environment variables:
   - `DATABASE_URL` (Railway will auto-provide PostgreSQL)
   - `API_KEY`
   - `ENVIRONMENT=production`
   - `ALLOWED_ORIGINS=*` (or your specific domains)

7. Deploy!

Your API will be at: `https://your-app.railway.app`

### Option 2: DigitalOcean App Platform

**Pros:** Full control, SSH access, scalable
**Cost:** $5/mo minimum

**Steps:**

1. Create Dockerfile (already included)
2. Push to GitHub
3. Create new app on DigitalOcean
4. Connect GitHub repository
5. Set environment variables
6. Deploy

### Option 3: Render.com

**Pros:** Similar to Railway, good free tier
**Cost:** Free tier, $7/mo for production

**Steps:**

1. Go to [render.com](https://render.com)
2. Create new "Web Service"
3. Connect GitHub repository
4. Select `license-server` directory
5. Set build command: `pip install -r requirements.txt`
6. Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
7. Add environment variables
8. Deploy

### Docker Deployment

Build and run with Docker:

```bash
cd license-server

# Build image
docker build -t osrs-license-server .

# Run container
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:pass@host:5432/licenses" \
  -e API_KEY="your-secret-key" \
  --name license-server \
  osrs-license-server
```

### Update Client Configuration

After deploying, update `src/osrsbot/config.json`:

```json
{
  "license": {
    "api_url": "https://your-deployed-api.railway.app",
    "purchase_url": "https://yoursite.com/buy",
    "timeout": 10,
    "cache_file": ".license_cache"
  }
}
```

Or use environment variable:
```bash
export LICENSE_API_URL=https://your-deployed-api.railway.app
```

---

## Creating Licenses

### Admin API Endpoints

All admin endpoints require the `X-API-Key` header.

### Create a License

```bash
curl -X POST "https://your-api.com/api/v1/admin/licenses?duration_hours=168&notes=customer@email.com" \
  -H "X-API-Key: your-secret-api-key"
```

**Duration Examples:**
- 1 hour: `duration_hours=1`
- 24 hours: `duration_hours=24`
- 7 days: `duration_hours=168`
- 30 days: `duration_hours=720`

### List All Licenses

```bash
curl -X GET "https://your-api.com/api/v1/admin/licenses" \
  -H "X-API-Key: your-secret-api-key"
```

### Get License Details

```bash
curl -X GET "https://your-api.com/api/v1/admin/licenses/XXXX-XXXX-XXXX-XXXX" \
  -H "X-API-Key: your-secret-api-key"
```

### Revoke a License

```bash
curl -X DELETE "https://your-api.com/api/v1/admin/licenses/XXXX-XXXX-XXXX-XXXX" \
  -H "X-API-Key: your-secret-api-key"
```

### Automation Script

Create `create_license.py`:

```python
import requests
import sys

API_URL = "https://your-api.com"
API_KEY = "your-secret-api-key"

def create_license(duration_hours, notes=""):
    response = requests.post(
        f"{API_URL}/api/v1/admin/licenses",
        params={"duration_hours": duration_hours, "notes": notes},
        headers={"X-API-Key": API_KEY}
    )
    response.raise_for_status()
    license_data = response.json()

    print(f"\n✓ License Created Successfully!")
    print(f"License Key: {license_data['license_key']}")
    print(f"Duration: {license_data['duration_hours']} hours")
    print(f"Created: {license_data['created_at']}")

    return license_data

if __name__ == "__main__":
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    notes = sys.argv[2] if len(sys.argv) > 2 else ""

    create_license(duration, notes)
```

Usage:
```bash
python create_license.py 168 "7-day license for customer123"
```

---

## Client Usage

### First Time Setup

1. User starts the bot for the first time
2. License validation fails (no license found)
3. GUI dialog appears asking for license key
4. User enters purchased license key
5. Key is validated and tied to their machine
6. Bot starts

### Subsequent Runs

1. User starts the bot
2. Cached license is validated automatically
3. Bot starts immediately (no dialog)

### License Expiry

When license expires:
1. Bot refuses to start
2. Clear error message shown
3. Link to purchase new license displayed

### Offline Mode

The system includes a 24-hour grace period for offline usage:
- If validation fails due to network issues
- And cached license was validated within last 24 hours
- Bot will start using cached license

---

## Troubleshooting

### "License key not found"

**Cause:** License key doesn't exist in database

**Solution:**
- Verify license key is correct
- Check if license was created successfully
- Contact admin to verify license in database

### "License already activated on different machine"

**Cause:** License is hardware-locked to another computer

**Solution:**
- Use license on original machine
- Purchase new license for second machine
- Contact support for license transfer (manual admin action required)

### "Network error"

**Cause:** Can't reach license server

**Solution:**
- Check internet connection
- Verify API URL in config is correct
- Check if license server is running
- Check firewall/antivirus blocking connection

### "License expired"

**Cause:** Time-based license has expired

**Solution:**
- Purchase new license
- Or contact admin to extend existing license

### License Server Not Starting

**Check logs:**
```bash
cd license-server
python -m uvicorn app.main:app --log-level debug
```

**Common issues:**
- Port 8000 already in use → Change `PORT` in `.env`
- Database connection failed → Check `DATABASE_URL`
- Missing dependencies → Run `pip install -r requirements.txt`

### Clear License Cache

If you need to reset the client-side cache:

```bash
rm .license_cache
```

Next startup will require re-activation.

---

## Integration with Payment Processors

### Gumroad Integration

1. Create product on Gumroad
2. Set up webhook for purchases
3. Webhook handler creates license automatically:

```python
from flask import Flask, request
import requests

app = Flask(__name__)

@app.route('/webhook/gumroad', methods=['POST'])
def gumroad_webhook():
    data = request.json

    # Extract purchase info
    email = data['email']
    product = data['product_name']

    # Determine duration based on product
    duration_map = {
        "1 Day License": 24,
        "7 Day License": 168,
        "30 Day License": 720,
    }
    duration = duration_map.get(product, 24)

    # Create license
    response = requests.post(
        "https://your-api.com/api/v1/admin/licenses",
        params={"duration_hours": duration, "notes": email},
        headers={"X-API-Key": "your-api-key"}
    )

    license_data = response.json()

    # Email license key to customer
    send_email(email, license_data['license_key'])

    return {"status": "success"}
```

### Manual License Distribution

1. Customer purchases via any method
2. Admin creates license manually
3. License key emailed to customer
4. Customer enters key in bot activation dialog

---

## Security Best Practices

1. **Never commit secrets to git**
   - Add `.env` to `.gitignore`
   - Use environment variables in production

2. **Use strong API keys**
   - Generate with `secrets.token_urlsafe(32)`
   - Rotate periodically

3. **Enable HTTPS**
   - Use SSL/TLS in production
   - Most hosting platforms provide this automatically

4. **Monitor for abuse**
   - Check server logs for suspicious activity
   - Rate limiting is already enabled

5. **Database backups**
   - Regularly backup license database
   - Most hosting platforms provide automatic backups

6. **Customer support**
   - Keep notes field updated with customer info
   - Log all activation attempts for debugging

---

## Next Steps

1. ✅ Deploy license server to production
2. ✅ Update client config with production API URL
3. ✅ Create test licenses and verify activation
4. ✅ Set up payment processing (Gumroad/Stripe)
5. ✅ Create purchase page
6. ✅ Test full flow end-to-end
7. ✅ Launch!

---

## Support

For issues or questions:
- Check the [LICENSE_SYSTEM.md](LICENSE_SYSTEM.md) plan document
- Review server logs: `docker logs license-server`
- Check API documentation: `https://your-api.com/docs`
- Test endpoints with Postman or curl

## License

This license system is part of the OSRS Bot Framework and is MIT licensed.
