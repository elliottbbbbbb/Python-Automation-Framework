# License Server Deployment - SUCCESS! ✅

Your license server is now running on Railway!

## Server Status
- **Status:** RUNNING ✓
- **Logs show:** Application startup complete
- **Database:** Initialized successfully
- **Port:** 8000 (internal), Railway handles external routing

## Next Steps

### 1. Get Your Public URL

Go to your Railway dashboard and copy the public URL. It will look like:
```
https://your-service-name.up.railway.app
```

### 2. Test the API

```bash
# Replace YOUR_URL with your actual Railway URL
curl https://YOUR_URL/health

# Expected response:
{"status": "healthy"}
```

### 3. Create Your First License

Replace `YOUR_URL` and `YOUR_API_KEY` (from Railway environment variables):

```bash
curl -X POST "https://YOUR_URL/api/v1/admin/licenses?duration_hours=168&notes=test-license" \
  -H "X-API-Key: YOUR_API_KEY"
```

Expected response:
```json
{
  "id": 1,
  "license_key": "XXXX-XXXX-XXXX-XXXX",
  "duration_hours": 168,
  "created_at": "2026-01-11T16:30:53",
  "expires_at": null,
  "activation_count": 0,
  "is_active": true,
  "last_validated_at": null
}
```

**Save the license_key** - you'll use this to test activation!

### 4. Update Bot Configuration

Edit [src/osrsbot/config.json](src/osrsbot/config.json:353-357):

```json
"license": {
  "api_url": "https://YOUR_RAILWAY_URL",
  "purchase_url": "https://yoursite.com/buy",
  "timeout": 10,
  "cache_file": ".license_cache",
  "offline_grace_period_hours": 24
}
```

Or set environment variable:
```bash
set LICENSE_API_URL=https://YOUR_RAILWAY_URL
```

### 5. Test Bot Activation

Run any bot script:
```bash
python scripts/your_bot_script.py
```

The license dialog will appear. Enter the license key you created in step 3.

### 6. Build Executable (Optional)

To package as an EXE for distribution:

1. Update [launcher.py](launcher.py) with your Railway URL
2. Run: `python build_exe.py`
3. Executable will be in `dist/OSRS_Bot.exe`

See [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md) for details.

## API Endpoints

Your license server now has these endpoints:

### Public Endpoints
- `GET /health` - Health check
- `POST /api/v1/activate` - Activate a license key
- `POST /api/v1/validate` - Validate an existing license

### Admin Endpoints (require X-API-Key header)
- `POST /api/v1/admin/licenses` - Create new license
- `GET /api/v1/admin/licenses` - List all licenses
- `GET /api/v1/admin/licenses/{key}` - Get license details
- `DELETE /api/v1/admin/licenses/{key}` - Revoke license

### API Documentation
Visit `https://YOUR_URL/docs` for interactive API documentation!

## Common License Durations

When creating licenses, use these durations:

| Duration | Hours | Command Parameter |
|----------|-------|-------------------|
| 1 hour   | 1     | `duration_hours=1` |
| 24 hours | 24    | `duration_hours=24` |
| 3 days   | 72    | `duration_hours=72` |
| 1 week   | 168   | `duration_hours=168` |
| 1 month  | 720   | `duration_hours=720` |

## How to Use

### For Development/Testing

1. Create test licenses via admin API
2. Run bot scripts locally
3. Test activation flow

### For Production/Sales

1. Set up payment processor (Gumroad/LemonSqueezy/Stripe)
2. Configure webhook to auto-create licenses on purchase
3. Build executable with production URL
4. Distribute executable to customers
5. Customers receive license key via email
6. Customers activate through GUI dialog

## Payment Integration Example (Gumroad)

1. Create product on Gumroad
2. Set up webhook to call your Railway URL:
   ```
   POST https://YOUR_URL/api/v1/admin/licenses?duration_hours=168
   Headers: X-API-Key: YOUR_API_KEY
   ```
3. Gumroad sends license key to customer
4. Customer enters key in bot

## Monitoring

Check Railway dashboard for:
- Server logs
- Request metrics
- Database usage
- Deployment status

## Database

Railway automatically created a SQLite database. For production scale:

1. Add PostgreSQL database in Railway
2. Update `DATABASE_URL` environment variable
3. Server will automatically use PostgreSQL

## Security Checklist

- ✅ API key authentication enabled
- ✅ Rate limiting configured (10/min activation, 30/min validation)
- ✅ Hardware fingerprinting prevents key sharing
- ✅ HTTPS enforced by Railway
- ✅ Environment variables secured

## Troubleshooting

### License activation fails
- Verify `api_url` is correct in config
- Check Railway logs for errors
- Test health endpoint: `curl https://YOUR_URL/health`

### "Already activated" error
- License is tied to a different machine
- Cannot transfer licenses (by design)
- Customer needs new license

### API key errors
- Verify `X-API-Key` header matches Railway environment variable
- Check admin endpoint calls include the header

## Support

For issues:
1. Check Railway logs
2. Test API with curl
3. Review [LICENSE_SETUP_GUIDE.md](docs/LICENSE_SETUP_GUIDE.md)
4. Check [IMPLEMENTATION_COMPLETE.md](docs/IMPLEMENTATION_COMPLETE.md)

---

**Deployment Complete!** 🚀

Your license authentication system is now live and ready for use.
