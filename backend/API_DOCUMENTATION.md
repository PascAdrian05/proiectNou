# Security Monitor API Documentation

## Overview
Security Monitor provides a RESTful API for security monitoring, scanning, and alerting. All endpoints are prefixed with `/api/v1`.

## Authentication
Most endpoints require authentication via JWT tokens. Include the token in the Authorization header:
```
Authorization: Bearer <your_token>
```

## Base URL
- Local development: `http://localhost:8000/api/v1`
- Production: `https://your-domain.com/api/v1`

## Interactive Documentation
- **Swagger UI**: `/api/v1/docs` - Interactive API explorer
- **ReDoc**: `/api/v1/redoc` - Beautiful API documentation

## Core Endpoints

### Authentication
- `POST /auth/register` - Register new user and tenant
- `POST /auth/login` - Login with email/password
- `POST /auth/logout` - Logout and invalidate token
- `POST /auth/refresh` - Refresh access token
- `POST /auth/2fa/setup` - Setup 2FA (TOTP)
- `POST /auth/2fa/enable` - Enable 2FA after verification
- `POST /auth/2fa/disable` - Disable 2FA
- `POST /auth/2fa/verify` - Login with 2FA token

### Websites
- `GET /websites` - List all websites
- `POST /websites` - Add new website to monitor
- `GET /websites/{id}` - Get website details
- `DELETE /websites/{id}` - Remove website
- `POST /websites/{id}/refresh` - Trigger immediate scan

### Scans
- `GET /scans` - List scan runs
- `GET /scans/{id}` - Get scan details
- `POST /scans/enqueue` - Enqueue new scan
- `GET /scans/{id}/findings` - Get findings from scan

### Findings
- `GET /findings` - List all findings
- `GET /findings/{id}` - Get finding details
- `PATCH /findings/{id}` - Update finding status

### Alerts
- `GET /alerts` - List alert configurations
- `POST /alerts` - Create alert configuration
- `DELETE /alerts/{id}` - Delete alert

### AI Assistant
- `GET /ai/status` - Check AI availability
- `POST /ai/security-tips` - Get AI security tips
- `POST /ai/verify-posture` - Verify security posture
- `POST /ai/analyze-finding/{id}` - Analyze specific finding
- `POST /ai/proactive-insights` - Get proactive AI recommendations

### Billing
- `GET /billing/subscription` - Get subscription details
- `POST /billing/stripe/checkout-session` - Create Stripe checkout
- `POST /billing/stripe/portal` - Access billing portal

### Trust (Public)
- `GET /trust/stats` - Get public trust statistics

### Status (Public)
- `GET /status/public` - Get system status

## Rate Limiting
API endpoints are rate-limited to prevent abuse:
- Login: 30 requests/minute
- Register: 20 requests/minute
- Other endpoints: Varies by endpoint

Failed login attempts trigger account lockout after multiple failures.

## Error Responses
All endpoints return consistent error responses:
```json
{
  "detail": "Error message description"
}
```

Common HTTP status codes:
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `429` - Too Many Requests
- `500` - Internal Server Error

## Webhooks
Stripe webhooks are handled at:
- `POST /billing/stripe/webhook`

Configure your Stripe webhook URL to point to this endpoint.

## Security Features
- JWT-based authentication with refresh tokens
- Rate limiting on all endpoints
- Account lockout after failed login attempts
- 2FA support (TOTP)
- Audit logging for all critical actions
- CORS protection
- SQL injection prevention (via SQLModel)

## Data Models
Key models include:
- `User` - User accounts with 2FA support
- `Tenant` - Multi-tenant organization
- `Website` - Monitored websites
- `ScanRun` - Scan execution records
- `Finding` - Security findings
- `Alert` - Alert configurations
- `Subscription` - Billing subscriptions
- `AuditLog` - Action audit trail

## Environment Variables
Required environment variables:
- `GROQ_API_KEY` - For AI features
- `STRIPE_API_KEY` - For billing
- `STRIPE_WEBHOOK_SECRET` - For Stripe webhooks
- `SECRET_KEY` - For JWT signing
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string

## Support
For API issues or questions, refer to the interactive documentation at `/api/v1/docs` or contact support.
