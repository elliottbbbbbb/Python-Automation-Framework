# License Server

FastAPI-based license validation and management system for OSRS Bot Framework.

## Features

- **License Activation**: Tie licenses to specific machines via hardware fingerprinting
- **License Validation**: Validate licenses on bot startup
- **Time-based Licenses**: Support for 1hr, 24hr, 7 days, or custom durations
- **Admin API**: Create, list, and revoke licenses
- **Rate Limiting**: Prevent abuse with request rate limiting
- **Security**: API key authentication for admin endpoints

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Edit `.env`:
```env
DATABASE_URL=sqlite:///./licenses.db
API_KEY=your-secret-api-key-here
ENVIRONMENT=development
```

### 3. Run the Server

```bash
# Development
uvicorn app.main:app --reload

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

### Public Endpoints

#### POST /api/v1/activate
Activate a license key for a specific machine.

**Request:**
```json
{
  "license_key": "XXXX-XXXX-XXXX-XXXX",
  "machine_fingerprint": "sha256_hash",
  "client_version": "1.0.0"
}
```

**Response:**
```json
{
  "success": true,
  "expires_at": "2026-01-12T15:30:00",
  "duration_hours": 24,
  "message": "License activated successfully"
}
```

#### POST /api/v1/validate
Validate a license key.

**Request:**
```json
{
  "license_key": "XXXX-XXXX-XXXX-XXXX",
  "machine_fingerprint": "sha256_hash"
}
```

**Response:**
```json
{
  "valid": true,
  "expires_at": "2026-01-12T15:30:00",
  "hours_remaining": 23.5,
  "message": "License valid"
}
```

### Admin Endpoints

Require `X-API-Key` header with admin API key.

#### POST /api/v1/admin/licenses
Create a new license.

**Query Parameters:**
- `duration_hours`: License duration in hours
- `notes`: Optional notes (email, customer ID, etc.)

**Response:**
```json
{
  "id": 1,
  "license_key": "A1B2-C3D4-E5F6-G7H8",
  "duration_hours": 24,
  "created_at": "2026-01-11T10:00:00",
  "expires_at": null,
  "activation_count": 0,
  "is_active": true,
  "last_validated_at": null
}
```

#### GET /api/v1/admin/licenses
List all licenses.

#### GET /api/v1/admin/licenses/{license_key}
Get license details.

#### DELETE /api/v1/admin/licenses/{license_key}
Revoke a license.

## Testing with cURL

### Create a License
```bash
curl -X POST "http://localhost:8000/api/v1/admin/licenses?duration_hours=24&notes=test" \
  -H "X-API-Key: your-secret-api-key"
```

### Activate License
```bash
curl -X POST "http://localhost:8000/api/v1/activate" \
  -H "Content-Type: application/json" \
  -d '{
    "license_key": "A1B2-C3D4-E5F6-G7H8",
    "machine_fingerprint": "abc123def456...",
    "client_version": "1.0.0"
  }'
```

### Validate License
```bash
curl -X POST "http://localhost:8000/api/v1/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "license_key": "A1B2-C3D4-E5F6-G7H8",
    "machine_fingerprint": "abc123def456..."
  }'
```

## Docker Deployment

### Build Image
```bash
docker build -t license-server .
```

### Run Container
```bash
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL="sqlite:///./licenses.db" \
  -e API_KEY="your-secret-key" \
  --name license-server \
  license-server
```

## Production Deployment

### Railway.app
1. Push code to GitHub
2. Connect Railway to your repository
3. Set environment variables in Railway dashboard
4. Deploy automatically

### DigitalOcean App Platform
1. Create new app from GitHub repository
2. Set environment variables
3. Deploy

### Render.com
1. Create new web service
2. Connect GitHub repository
3. Set environment variables
4. Deploy

## Database

### SQLite (Development)
- Default: `sqlite:///./licenses.db`
- File-based, no setup required

### PostgreSQL (Production)
Update `DATABASE_URL` in `.env`:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/licenses
```

## Security Considerations

1. **HTTPS Only**: Always use HTTPS in production
2. **API Key**: Use strong, random API key for admin endpoints
3. **Rate Limiting**: Configured to prevent brute force attacks
4. **Database**: Use managed PostgreSQL in production
5. **Secrets**: Never commit `.env` file to version control

## Monitoring

- Health check: `GET /health`
- API documentation: `GET /docs` (FastAPI auto-generated)
- Logs: Check server logs for activation/validation attempts

## License

MIT License
