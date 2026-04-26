# Social Media Integration Module

## Overview

The Social Media Integration module provides a complete solution for integrating Blotato's social media management API into your Autobus application. This module enables users to:

- **Connect multiple social media accounts** via OAuth (Twitter, LinkedIn, Facebook, Instagram, TikTok, YouTube, Threads, Bluesky, Mastodon)
- **Publish content** to one or multiple platforms simultaneously
- **Manage connected accounts** (list, refresh, disconnect)
- **Track publishing metrics** and respect rate limits
- **Handle OAuth flows** securely with CSRF protection

In addition, this repo includes a **Postiz (self-hosted)** stack and a minimal integration layer in Autobus to:

- **Provision a Postiz organization per Autobus user** (optional, on signup)
- **Proxy Postiz Public API calls** (list integrations + create posts) using the org-scoped Postiz API key

## Architecture

```
socialmedia/
├── model/
│   └── SocialAccount.py          # SQLAlchemy model for social accounts
├── dto/
│   └── socialmedia_dto.py        # Pydantic DTOs for request/response
├── service/
│   ├── blotato_api_service.py    # Blotato API client & OAuth manager
│   ├── socialmedia_service.py    # Account management business logic
│   └── post_publishing_service.py # Post publishing logic
├── controller/
│   └── socialmedia_controller.py # FastAPI routes
└── tests/
    └── test_socialmedia.py       # Unit & integration tests
```

## Core Components

### 1. Database Model (`SocialAccount`)

Stores connected social media accounts for each user.

**Fields:**
- `id`: Unique account identifier
- `user_id`: Foreign key to user
- `platform`: Social platform (TWITTER, LINKEDIN, etc.)
- `account_id`: Blotato's account ID
- `account_name`: Display name on platform
- `platform_user_id`: Original platform user ID
- `access_token`: OAuth access token (for API calls)
- `is_active`: Account status
- `connected_at`: Connection timestamp
- `last_used_at`: Last post timestamp
- `posts_today`: Daily post counter for rate limiting

### 2. API Service (`BlotatoAPIClient`)

Handles all communication with Blotato API.

**Key Methods:**
- `generate_oauth_url()` - Creates OAuth authorization URL
- `exchange_auth_code()` - Exchanges code for account info
- `get_accounts()` - Retrieves user's connected accounts
- `upload_media()` - Uploads media for posts
- `create_post()` - Publishes post to account
- `validate_rate_limit()` - Checks rate limit compliance

**Rate Limits:**
- 30 posts per minute per account
- 10 media uploads per minute
- 60MB max per media file

### 3. Social Media Service (`SocialMediaService`)

Manages database operations and business logic.

**Key Methods:**
- `connect_account()` - Stores OAuth callback result
- `get_user_accounts()` - Lists all user's accounts
- `get_user_accounts_by_platform()` - Filters by platform
- `disconnect_account()` - Removes account from database
- `refresh_accounts()` - Updates account info from Blotato
- `validate_account_ownership()` - Ensures user owns accounts

### 4. Publishing Service (`PostPublishingService`)

Handles content publishing to multiple platforms.

**Key Methods:**
- `publish_post()` - Main method for publishing
- `_upload_media()` - Helper for media uploads
- `_publish_to_platform()` - Publishes to single account

### 5. OAuth Manager (`BlotatoOAuthManager`)

Manages OAuth state for CSRF protection.

**Methods:**
- `create_state()` - Generates secure state token
- `validate_state()` - Validates state and retrieves data

### 6. API Routes (`social_routes`)

FastAPI router with the following endpoints:

#### Account Connection
- `GET /api/v1/social/connect/{platform}` - Initiates OAuth
- `GET /api/v1/social/callback` - OAuth callback handler

#### Account Management
- `GET /api/v1/social/accounts` - List accounts
- `DELETE /api/v1/social/accounts/{account_id}` - Disconnect
- `POST /api/v1/social/refresh` - Refresh accounts

#### Publishing
- `POST /api/v1/social/post` - Publish post

## Configuration

### Environment Variables

```bash
# Required
BLOTATO_API_KEY=your_api_key
BLOTATO_CLIENT_ID=your_client_id
BLOTATO_CLIENT_SECRET=your_client_secret

# Optional
BLOTATO_API_BASE=https://api.blotato.com
BLOTATO_OAUTH_BASE=https://app.blotato.com
BASE_FRONTEND_URL=http://localhost:3000

# Postiz (self-hosted)
POSTIZ_BASE_URL=http://localhost:4007
# Optional fallback when no per-user Postiz org mapping exists
POSTIZ_PUBLIC_API_KEY=your_postiz_public_api_key

# Optional: encrypt API keys/tokens at rest
TOKEN_ENCRYPTION_KEY=... # Fernet key
```

### Postiz Provisioning Flow (Autobus → Postiz)

If `POSTIZ_BASE_URL` is set, `POST /auth/signup` will attempt to:

- call `POST {POSTIZ_BASE_URL}/api/auth/register` with `{provider:"LOCAL", email, password, company}`
- call `GET {POSTIZ_BASE_URL}/api/user/self` (same cookie jar) to obtain `orgId` + `publicApi`
- store the mapping in the Autobus DB table `postiz_organizations`

### Postiz Public API Proxy Endpoints (Autobus)

- `GET /api/v1/social/postiz/integrations` → calls Postiz `GET /api/public/v1/integrations`
- `POST /api/v1/social/postiz/posts` → calls Postiz `POST /api/public/v1/posts` (raw payload passthrough)

API key resolution order for the Postiz proxy routes:
1. User-scoped key from `postiz_organizations` (provisioned flow)
2. `POSTIZ_PUBLIC_API_KEY` (or `POSTIZ_GLOBAL_PUBLIC_API_KEY`) from environment

### Settings Integration

Configuration is loaded from `src/config.py`:

```python
class Settings(BaseSettings):
    BLOTATO_API_KEY: str = os.environ.get('BLOTATO_API_KEY', '')
    BLOTATO_CLIENT_ID: str = os.environ.get('BLOTATO_CLIENT_ID', '')
    BLOTATO_CLIENT_SECRET: str = os.environ.get('BLOTATO_CLIENT_SECRET', '')
    BLOTATO_API_BASE: str = ...
    BLOTATO_OAUTH_BASE: str = ...
```

## Database Schema

The module creates a `social_accounts` table with the following structure:

```sql
CREATE TABLE social_accounts (
    id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(20) NOT NULL FOREIGN KEY REFERENCES users(id),
    platform VARCHAR(50) NOT NULL,
    account_id VARCHAR(100) NOT NULL UNIQUE,
    account_name VARCHAR(255) NOT NULL,
    platform_user_id VARCHAR(100),
    access_token VARCHAR(500),
    refresh_token VARCHAR(500),
    token_expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    connected_at TIMESTAMP NOT NULL,
    last_used_at TIMESTAMP,
    updated_at TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_post_time TIMESTAMP,
    posts_today INTEGER DEFAULT 0,
    INDEX(user_id),
    INDEX(platform)
);
```

### Create Migration

```bash
cd /path/to/autobus
alembic revision --autogenerate -m "Add social_accounts table"
alembic upgrade head
```

## Usage Examples

### 1. Connect Account (OAuth Flow)

```python
# Frontend initiates OAuth
GET /api/v1/social/connect/TWITTER
# Response:
{
  "authorization_url": "https://app.blotato.com/oauth/authorize?...",
  "platform": "TWITTER"
}

# User is redirected to authorization_url
# After authorization, Blotato redirects to:
GET /api/v1/social/callback?code=xyz&state=abc
```

### 2. Publish Post

```python
POST /api/v1/social/post
{
  "account_ids": ["sa_123", "sa_456"],
  "content": "Check this out! 🚀",
  "media_urls": [
    {"url": "https://example.com/image.jpg", "type": "image"}
  ],
  "schedule_time": null,
  "hashtags": ["tech", "innovation"]
}

# Response:
{
  "success": true,
  "total_platforms": 2,
  "successful_posts": 2,
  "failed_posts": 0,
  "results": [
    {
      "account_id": "sa_123",
      "platform": "TWITTER",
      "success": true,
      "post_id": "post_xyz"
    }
  ]
}
```

### 3. Chatbot Integration

```python
@bot.command()
async def post_command(user_id: str, platform: str, content: str, db: Session):
    """Post to user's social media via chatbot"""
    service = SocialMediaService(db, blotato_client)
    accounts = service.get_user_accounts_by_platform(user_id, platform)
    
    if not accounts:
        return f"Please connect your {platform} account first"
    
    publishing = PostPublishingService(db, blotato_client)
    request = PublishPostRequest(
        account_ids=[acc.id for acc in accounts],
        content=content
    )
    result = await publishing.publish_post(user_id, request)
    
    if result.success:
        return f"✅ Posted to {result.successful_posts} platforms"
    return f"❌ {result.message}"
```

## Testing

### Run Tests

```bash
# All tests
pytest src/core/socialmedia/tests/ -v

# Specific test
pytest src/core/socialmedia/tests/test_socialmedia.py::TestBlotatoAPIClient::test_generate_oauth_url -v

# With coverage
pytest src/core/socialmedia/tests/ --cov=src/core/socialmedia --cov-report=html
```

### Test Coverage

- `TestBlotatoAPIClient` - API client functionality (OAuth, requests)
- `TestBlotatoOAuthManager` - OAuth state management
- `TestSocialMediaService` - Account management operations
- `TestPostPublishingService` - Post publishing logic
- `TestIntegration` - End-to-end workflows

## Security Considerations

### OAuth Security

1. **State Parameter**: Every OAuth request includes a secure random state token
2. **CSRF Protection**: State is validated on callback before processing
3. **State Expiration**: States expire after 10 minutes
4. **One-time Use**: States are deleted after validation

### Token Security

1. **Access Tokens**: Should be encrypted in production
2. **Refresh Tokens**: Should be encrypted and stored securely
3. **Token Rotation**: Consider implementing token refresh logic
4. **Token Scopes**: Limited to necessary permissions (read accounts, write posts, upload media)

### Rate Limiting

1. **Per-Account Limits**: 30 posts per minute per account
2. **Daily Tracking**: Posts per day tracked in `posts_today` field
3. **Enforcement**: API returns error if limits exceeded

### Data Validation

1. **Account Ownership**: All operations verify user owns the account
2. **Input Validation**: Pydantic models validate all inputs
3. **Content Length**: Post content limited to 5000 characters
4. **Media Size**: Media uploads limited to 60MB

## Error Handling

### Common Errors

| Error | Status | Description |
|-------|--------|-------------|
| No connected accounts | 400 | User hasn't connected any social accounts |
| Account not found | 404 | Requested account doesn't exist |
| Account not owned | 400 | User doesn't own the account |
| Invalid platform | 400 | Platform not in supported list |
| Rate limit exceeded | 429 | Post/media upload limit exceeded |
| Invalid token | 401 | OAuth token invalid or expired |
| Invalid state | 400 | OAuth state parameter invalid/expired |

### Error Response Format

```json
{
  "success": false,
  "error": "Account validation failed",
  "detail": "Account sa_xyz not found or not owned by user"
}
```

## Performance Optimizations

1. **Lazy Loading**: Account refresh queried on-demand
2. **Batch Operations**: Multi-platform publishing in single request
3. **Async/Await**: Non-blocking API calls via httpx
4. **Caching**: OAuth endpoints cached (in production, use Redis)
5. **Indexing**: Database indexes on `user_id` and `platform`

## Future Enhancements

- [ ] **Webhook Integration**: Receive updates from Blotato
- [ ] **Analytics Dashboard**: Track engagement metrics
- [ ] **Advanced Scheduling**: Recurring posts, timezone support
- [ ] **Draft Management**: Save and schedule drafts
- [ ] **AI Integration**: Content suggestions, hashtag recommendations
- [ ] **Media Gallery**: Store and reuse media
- [ ] **Team Collaboration**: Share accounts across team members
- [ ] **Compliance Tracking**: GDPR, data retention policies
- [ ] **Multi-language Support**: Translate content across platforms
- [ ] **Bulk Operations**: CSV upload for batch posting

## Troubleshooting

### OAuth Not Working

**Problem**: Redirect URL doesn't match Blotato settings
**Solution**: 
- Verify `BASE_FRONTEND_URL` matches registered callback in Blotato dashboard
- Check `BLOTATO_CLIENT_ID` and `BLOTATO_CLIENT_SECRET` are correct

### Post Publishing Fails

**Problem**: All posts failing
**Solution**:
- Check accounts are connected: `GET /api/v1/social/accounts`
- Verify `is_active` is `true` for accounts
- Check access tokens haven't expired
- Review Blotato API status

### Database Errors

**Problem**: `social_accounts` table not found
**Solution**:
- Run migrations: `alembic upgrade head`
- Verify `dbmodels.py` imports `SocialAccount` model
- Check PostgreSQL connection is working

### Rate Limits

**Problem**: "Daily post limit reached"
**Solution**:
- Check `posts_today` counter in account
- Rate limits reset daily
- Contact Blotato to increase limits if needed

## Support & Documentation

- [Blotato API Documentation](https://docs.blotato.com)
- [Autobus README](../../../README.md)
- [Full Integration Guide](../../../BLOTATO_INTEGRATION_GUIDE.md)

## License

MIT License - See LICENSE file
