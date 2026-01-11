# License Admin Panel - Quick Start

A GUI application for managing your OSRS bot licenses without using curl commands.

## Running the Admin Panel

```powershell
python deployment/license_admin.py
```

## First Time Setup

When you run the admin panel for the first time, you'll see a setup dialog:

1. **API URL**: Enter your Railway URL
   ```
   https://osrs-automation-framework-production.up.railway.app
   ```

2. **API Key**: Enter your admin API key from Railway environment variables

3. Click **Save Configuration**

Settings are saved locally for future use.

---

## Features

### 1. Create License Tab

**Preset Durations:**
- 1 Hour (Free trial)
- 24 Hours
- 3 Days
- 1 Week
- 1 Month
- Custom (enter hours manually)

**Process:**
1. Select duration
2. Add notes (optional) - customer email, order ID, etc.
3. Click **Create License**
4. License key automatically copied to clipboard
5. Send to customer via email

### 2. View Licenses Tab

**Shows all licenses in table:**
- License Key
- Status (Active, Expired, Revoked)
- Created date
- Expires date
- Machine (activated on)
- Notes

**Actions:**
- Click **Refresh** to reload
- Click **Export to JSON** to save license list
- Double-click any row to view full details

### 3. Search License Tab

**Search by key:**
1. Enter license key (XXXX-XXXX-XXXX-XXXX)
2. Click **Search**
3. View full details including metadata
4. Click **Revoke License** if needed

---

## Common Tasks

### Creating a License for a Customer

1. Go to **Create License** tab
2. Select **1 Week** (168 hours)
3. Enter customer email in notes: `customer@email.com`
4. Click **Create License**
5. Key is now in your clipboard
6. Paste into email/Discord and send to customer

### Checking if a License is Active

1. Go to **Search License** tab
2. Paste the license key
3. Click **Search**
4. Check status and expiration date

### Revoking a License (Refund/Abuse)

1. Go to **Search License** tab
2. Enter the license key
3. Click **Search**
4. Click **Revoke License**
5. Confirm in dialog
6. License is immediately deactivated

### Viewing All Active Licenses

1. Go to **View Licenses** tab
2. Click **Refresh**
3. Sort by Status column to group active licenses
4. Export to JSON for record keeping

---

## Status Meanings

- **Active**: License is valid and not expired
- **Expired**: License time period has ended
- **Revoked**: License was manually deactivated

---

## Troubleshooting

### "Connection Error"
- Check Railway server is running
- Verify API URL is correct
- Test: `curl https://your-url.railway.app/health`

### "Authentication Failed"
- Verify API key is correct in Railway environment variables
- Check API key in Settings

### Can't see new license after creating
- Click **Refresh** in View Licenses tab

---

## Tips

- Keep the admin panel open while managing customers
- Use notes field to track customer info
- Export licenses regularly for backup
- Double-click rows in View tab for quick details
- License keys are automatically formatted with hyphens

---

## Payment Integration

When you connect Gumroad/Stripe webhooks, you can:
1. Receive webhook on successful payment
2. Auto-call your admin API to create license
3. Email license key to customer
4. No manual license creation needed

For now, use this GUI to manually create licenses after receiving payments.

---

## Need Help?

Check these files for more info:
- `README_LICENSING.md` - Overall system overview
- `BUILD_EXE.md` - Building customer executable
- `docs/guides/LICENSE_SYSTEM.md` - Full technical details
