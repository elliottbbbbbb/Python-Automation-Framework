# OSRS Bot - License System Quick Reference

## For You (Developer)

### Building the Executable

```powershell
# 1. Install PyInstaller
pip install pyinstaller

# 2. Build the EXE
python deployment/build_exe.py

# 3. Test it
dist/OSRS_Bot.exe
```

Full guide: [`deployment/BUILD_EXE.md`](deployment/BUILD_EXE.md)

### Creating Licenses (Admin)

```powershell
# Create a 7-day license
curl -X POST "https://osrs-automation-framework-production.up.railway.app/api/v1/admin/licenses?duration_hours=168&notes=customer-email" -H "X-API-Key: YOUR_API_KEY"

# List all licenses
curl "https://osrs-automation-framework-production.up.railway.app/api/v1/admin/licenses" -H "X-API-Key: YOUR_API_KEY"

# Revoke a license
curl -X DELETE "https://osrs-automation-framework-production.up.railway.app/api/v1/admin/licenses/XXXX-XXXX-XXXX-XXXX" -H "X-API-Key: YOUR_API_KEY"
```

---

## For Your Customers (Users)

### First Time Use

1. **Download** `OSRS_Bot.exe`
2. **Double-click** to run
3. **GUI dialog appears** asking for license key
4. **Paste license key** (format: XXXX-XXXX-XXXX-XXXX)
5. **Click "Activate"**
6. **Done!** Bot starts immediately

### Every Other Time

1. **Double-click** `OSRS_Bot.exe`
2. **Bot starts immediately** (no dialog)

### If License Expires

- Bot shows error message
- Link to purchase new license
- Bot refuses to start until renewed

---

## How It Works

### User Experience Flow

```
First Run:
  Launch EXE
    ↓
  "Validating license..."
    ↓
  [GUI Dialog Appears]
    ↓
  User enters key
    ↓
  Key validates & ties to machine
    ↓
  Bot starts

Subsequent Runs:
  Launch EXE
    ↓
  "Validating license..." (silent check)
    ↓
  ✓ Valid
    ↓
  Bot starts immediately
```

### Technical Flow

1. **Activation**: License key ties to machine fingerprint (hardware ID)
2. **Validation**: Every launch checks with Railway server
3. **Caching**: Last validation cached for 24-hour offline grace period
4. **Expiry**: Time-based (hourly), automatic enforcement

---

## Project Structure

```
OSRS-Automation-Framework/
├── deployment/              # Build scripts
│   ├── build_exe.py        # EXE builder
│   └── BUILD_EXE.md        # Build guide
│
├── docs/guides/             # Documentation
│   ├── LICENSE_SYSTEM.md
│   ├── LICENSE_SETUP_GUIDE.md
│   └── IMPLEMENTATION_COMPLETE.md
│
├── license-server/          # Backend API (Railway)
│   ├── app/
│   │   ├── main.py         # FastAPI app
│   │   ├── routes/         # API endpoints
│   │   └── models.py       # Database models
│   └── requirements.txt
│
├── src/osrsbot/
│   ├── app/
│   │   └── menu.py         # Main entry point (becomes EXE)
│   ├── services/
│   │   ├── license_service.py       # License validation
│   │   └── hardware_fingerprint.py  # Machine ID
│   ├── ui/
│   │   └── license_dialog.py        # GUI activation
│   └── config.json         # IMPORTANT: Update URLs here!
│
└── scripts/
    ├── run_bot.py          # Alternative launcher
    └── examples/           # Test scripts
```

---

## Configuration

### CRITICAL: Update Before Building EXE

Edit `src/osrsbot/config.json`:

```json
"license": {
  "api_url": "https://osrs-automation-framework-production.up.railway.app",
  "purchase_url": "https://your-actual-sales-page.com/buy",
  "timeout": 10,
  "cache_file": ".license_cache",
  "offline_grace_period_hours": 24
}
```

**Must update:**
- `api_url` → Your Railway URL
- `purchase_url` → Your sales/purchase page

---

## Common License Durations

| Duration | Hours | Price Suggestion |
|----------|-------|------------------|
| 1 hour   | 1     | Free trial       |
| 24 hours | 24    | $5               |
| 3 days   | 72    | $10              |
| 1 week   | 168   | $15              |
| 1 month  | 720   | $40              |

---

## FAQ

### Do users need Python?
**No.** The EXE includes everything.

### Do users edit config.json?
**No.** They just enter the license key in the GUI.

### Can users share license keys?
**No.** Keys are hardware-locked to one machine.

### What if users lose internet?
24-hour grace period using cached license.

### Can I revoke licenses?
Yes, using the admin API.

### How do I auto-create licenses on purchase?
Set up webhook from Gumroad/Stripe to your admin API.

---

## Support

### For You

- Railway logs: Check activation attempts
- Admin API: List/view/revoke licenses
- Database: SQLite (dev) or PostgreSQL (prod)

### For Customers

Common issues:
- "Already activated on different machine" → They need a new license
- "License expired" → They need to purchase renewal
- "Network error" → Check Railway is running
- "Invalid key" → They typed it wrong

---

## Ready to Distribute! 🚀

1. ✅ Railway server deployed
2. ✅ License system integrated
3. ✅ Build script ready
4. ✅ Documentation complete

**Next:** Build the EXE and start selling!
