# Building Your Bot as an Executable

This guide shows you how to package your OSRS bot into a standalone `.exe` file for distribution to customers.

## Quick Summary for Users

**Your customers will:**
1. Download and run `OSRS_Bot.exe`
2. A GUI dialog will pop up asking for a license key
3. They enter the key they purchased from you
4. The bot activates and starts running
5. Future runs are automatic (no dialog)

**They never need to:**
- Install Python
- Edit any config files
- Use command line
- Know anything technical

---

## Prerequisites

```powershell
# Install PyInstaller
pip install pyinstaller
```

## Step 1: Update Configuration

**CRITICAL: Do this BEFORE building!**

Edit `src/osrsbot/config.json`:

```json
"license": {
  "api_url": "https://osrs-automation-framework-production.up.railway.app",
  "purchase_url": "https://your-sales-page.com/buy",
  "timeout": 10,
  "cache_file": ".license_cache",
  "offline_grace_period_hours": 24
}
```

Replace:
- `api_url` → Your Railway URL
- `purchase_url` → Your actual sales/purchase page

## Step 2: Build the Executable

### Option A: Use the Build Script (Recommended)

```powershell
python deployment/build_exe.py
```

This will:
- Create a single `OSRS_Bot.exe` file
- Include all dependencies
- Bundle the license system
- Place it in `dist/OSRS_Bot.exe`

### Option B: Manual Build

```powershell
pyinstaller src/osrsbot/app/menu.py ^
    --name=OSRS_Bot ^
    --onefile ^
    --add-data="src/osrsbot;osrsbot" ^
    --add-data="src/osrsbot/config.json;osrsbot" ^
    --add-data="src/osrsbot/images;osrsbot/images" ^
    --hidden-import=osrsbot ^
    --hidden-import=osrsbot.services.license_service ^
    --hidden-import=osrsbot.services.hardware_fingerprint ^
    --hidden-import=osrsbot.ui.license_dialog ^
    --clean ^
    --noconfirm
```

## Step 3: Test the Executable

**Test on your development machine:**

```powershell
# Delete your cached license first
Remove-Item .license_cache

# Run the exe
.\dist\OSRS_Bot.exe
```

You should see:
1. "Validating license..."
2. GUI dialog appears (since no license cached)
3. Enter a test license key
4. Bot menu appears

**Test on a clean machine:**
- Copy `OSRS_Bot.exe` to a computer without Python
- Run it
- Verify license activation works
- Verify bot functionality

## Step 4: Distribution

Your `dist/OSRS_Bot.exe` file is ready to distribute!

**File size:** ~100-200 MB (includes Python + all dependencies)

**What customers need:**
- Windows 10/11
- Old School RuneScape (RuneLite recommended)
- Internet connection (for license validation)
- A license key (purchased from you)

---

## First-Time User Experience

1. **Download:** Customer downloads `OSRS_Bot.exe` from your website
2. **Run:** They double-click to run it
3. **License Dialog:** A window pops up:
   ```
   ╔════════════════════════════════════════╗
   ║   OSRS Bot - License Activation       ║
   ╠════════════════════════════════════════╣
   ║                                        ║
   ║  Enter License Key:                    ║
   ║  [                              ]      ║
   ║                                        ║
   ║  [Activate]    [Purchase License]     ║
   ║                                        ║
   ╚════════════════════════════════════════╝
   ```
4. **Activate:** They paste their key and click "Activate"
5. **Success:** Dialog closes, bot starts
6. **Future Use:** No dialog, bot starts immediately

---

## Advanced: Adding a Custom Icon

1. Create or download a `.ico` file
2. Place it in the project root: `bot_icon.ico`
3. Update `build_exe.py`:
   ```python
   '--icon=bot_icon.ico',  # Add this line
   ```
4. Rebuild

---

## Advanced: Multiple Bot Scripts

If you want users to choose which bot to run, the menu system already handles this!

The `osrs-bot` command (which becomes the EXE) shows a menu:
```
============================================================
OSRS BOT - TASK SCRIPT RUNNER
============================================================
1. Calibrate Colors & Coordinates
2. Comprehensive Test Bot
3. Stats Tracker
4. Template Click Test
5. Manual Cleaning Bankstander
6. NMZ AFK Bot
7. Zulrah Boss Bot
8. Basic NPC Killer

Select:
```

Users just enter the number of the bot they want to run.

---

## Troubleshooting

### "Module not found" errors when running EXE

Add the missing module to `build_exe.py`:
```python
'--hidden-import=missing_module_name',
```

### Images/resources not loading

Ensure paths are included:
```python
f'--add-data={SOURCE_PATH};{DESTINATION_PATH}',
```

### License activation fails

- Verify `api_url` in config.json is correct
- Check Railway server is running
- Test API: `curl https://your-url.railway.app/health`

### EXE too large

Exclude unused packages:
```python
'--exclude-module=matplotlib',
'--exclude-module=pandas',
```

---

## Payment Integration

To automatically create licenses when customers purchase:

### Option 1: Gumroad (Recommended - Easiest)

1. Create product on Gumroad
2. Set up webhook to call your Railway API:
   ```
   POST https://your-url.railway.app/api/v1/admin/licenses?duration_hours=168
   Headers: X-API-Key: YOUR_API_KEY
   ```
3. Gumroad emails the license key to customer
4. Done!

### Option 2: Stripe

1. Create product in Stripe
2. Set up webhook endpoint
3. On successful payment, call your admin API to create license
4. Email customer the license key

### Option 3: LemonSqueezy

Similar to Gumroad, supports webhooks for automatic license creation.

---

## Distribution Checklist

Before distributing your bot:

- [ ] Railway server is deployed and running
- [ ] Production `api_url` is set in config.json
- [ ] Purchase URL is set to your actual sales page
- [ ] EXE built with latest code
- [ ] Tested on clean machine without Python
- [ ] License activation tested end-to-end
- [ ] All bot features work in EXE
- [ ] Payment system configured
- [ ] License delivery system set up (email/webhook)
- [ ] Created a few test licenses
- [ ] Tested license expiration behavior

---

## Support

If customers have license issues:

1. Check Railway logs for activation attempts
2. Verify their license key exists in database
3. Check if license is already activated on different machine
4. Verify license hasn't expired
5. Test API health endpoint

**Admin tools:**

```bash
# Create license
curl -X POST "https://your-url.railway.app/api/v1/admin/licenses?duration_hours=168" -H "X-API-Key: YOUR_KEY"

# List all licenses
curl "https://your-url.railway.app/api/v1/admin/licenses" -H "X-API-Key: YOUR_KEY"

# Get license details
curl "https://your-url.railway.app/api/v1/admin/licenses/XXXX-XXXX-XXXX-XXXX" -H "X-API-Key: YOUR_KEY"

# Revoke license
curl -X DELETE "https://your-url.railway.app/api/v1/admin/licenses/XXXX-XXXX-XXXX-XXXX" -H "X-API-Key: YOUR_KEY"
```

---

## Ready to Launch! 🚀

Your bot is now ready for production distribution with full license protection!
