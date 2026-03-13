# Blotato Integration - Quick Reference

## File Structure

```
src/core/blotato/
├── model/
│   ├── __init__.py
│   └── SocialAccount.py          # SQLAlchemy ORM model
├── service/
│   ├── __init__.py
│   ├── blotato_client.py         # Blotato API client wrapper
│   └── blotato_service.py        # Business logic service
├── controller/
│   ├── __init__.py
│   └── social_controller.py      # FastAPI route handlers
└── dto/
    ├── __init__.py
    ├── request/
    │   ├── __init__.py
    │   └── social_post_request.py # Request models
    └── response/
        ├── __init__.py
        └── (responses in social_post_request.py)
```

## Key Classes

### SocialAccount (Model)
- Database ORM model for storing social accounts
- Tracks OAuth tokens, rate limits, and last usage
- Methods: `is_token_expired()`, `is_rate_limited()`

### BlotatoAPIClient (Service)
- Wrapper around Blotato API
- Methods:
  - `generate_oauth_url(state)` - Create OAuth authorization URL
  - `exchange_code_for_token(code)` - Exchange OAuth code for tokens
  - `get_accounts(access_token)` - List user's Blotato accounts
  - `create_post(account_id, content, media, publish_date)` - Publish post
  - `upload_media(media_url)` - Upload media to Blotato
  - `refresh_access_token(refresh_token)` - Renew access token
  - `delete_account(account_id)` - Disconnect account

### BlotatoService (Business Logic)
- Orchestrates database and API operations
- Methods:
  - `connect_account(user_id, platform, code, access_token)` - Connect account
  - `get_user_accounts(user_id)` - List user's accounts
  - `disconnect_account(account_id, user_id)` - Disconnect account
  - `publish_post(user_id, account_ids, content, media_urls, schedule_time)` - Publish to multiple accounts

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/social/connect/{platform}` | Get OAuth URL |
| GET | `/api/social/callback` | Handle OAuth redirect |
| GET | `/api/social/accounts` | List connected accounts |
| DELETE | `/api/social/accounts/{account_id}` | Disconnect account |
| POST | `/api/social/post` | Publish post |

## Database Updates

Run migrations to create the `social_accounts` table:

```bash
alembic upgrade head
```

The User model has been updated with a relationship:
```python
social_accounts: Mapped[List["SocialAccount"]] = relationship(...)
```

## Configuration

Update your `.env` file:

```env
BLOTATO_API_KEY=your_key
BLOTATO_CLIENT_ID=your_client_id
BLOTATO_CLIENT_SECRET=your_client_secret
BLOTATO_REDIRECT_URI=https://your-api.com/api/social/callback
```

## Development Workflow

### 1. Test OAuth Connection
```bash
curl -X POST https://localhost:8000/api/social/connect/facebook \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 2. Simulate Callback
```bash
curl -X GET "https://localhost:8000/api/social/callback?code=test_code&state=test_state"
```

### 3. List Accounts
```bash
curl -X GET https://localhost:8000/api/social/accounts \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. Publish Post
```bash
curl -X POST https://localhost:8000/api/social/post \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_ids": [1],
    "content": "Hello world",
    "media_urls": ["https://example.com/image.jpg"]
  }'
```

## Error Codes

| Status | Error | Solution |
|--------|-------|----------|
| 400 | Invalid state token | Restart OAuth flow |
| 400 | Rate limit exceeded | Wait for reset |
| 401 | Missing auth token | Include Bearer token |
| 404 | Account not found | Verify account ID and ownership |
| 500 | Token refresh failed | User must reconnect |

## Testing

### Mock Blotato for Testing
```python
from unittest.mock import patch

@patch('core.blotato.service.blotato_client.BlotatoAPIClient.exchange_code_for_token')
def test_oauth_callback(mock_exchange):
    mock_exchange.return_value = {
        'access_token': 'test_token',
        'refresh_token': 'test_refresh',
        'expires_in': 3600
    }
    # Test code here
```

## Common Issues

### Issue: "Auth credentials not configured"
**Solution**: Check BLOTATO_CLIENT_ID and BLOTATO_CLIENT_SECRET in .env

### Issue: "Invalid state token"
**Solution**: State tokens expire after ~30 minutes. Restart OAuth flow.

### Issue: OAuth redirect loop
**Solution**: Ensure BLOTATO_REDIRECT_URI matches exactly in both Blotato dashboard and .env

### Issue: Tokens not saving
**Solution**: Check database constraints and User relationship setup

## Performance Considerations

- Rate limit: 30 posts/minute per account
- Token refresh buffer: 5 minutes before expiry
- Media upload: Handled asynchronously if possible
- Database indexes on: user_id, account_id, is_active

## Security Checklist

- [ ] Tokens encrypted at rest in production
- [ ] HTTPS enforced for all API calls
- [ ] CSRF tokens validated correctly
- [ ] Rate limiting enabled on endpoints
- [ ] User ownership verified before operations
- [ ] Audit logs captured for account operations
- [ ] Error messages don't leak sensitive data

## Next Steps

1. Add Blotato credentials to your environment
2. Run database migrations: `alembic upgrade head`
3. Test OAuth flow in development
4. Implement token encryption in production
5. Add monitoring for failed posts
6. Consider webhook support for post delivery status

