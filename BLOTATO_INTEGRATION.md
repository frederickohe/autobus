# Blotato Integration Documentation

## Overview

This document describes the complete Blotato integration for the Autobus backend. Blotato is a social media management platform that allows users to connect multiple social accounts and publish content across them.

## Environment Configuration

Add the following environment variables to your `.env` file:

```env
# Blotato Configuration
BLOTATO_API_KEY=your_api_key_here
BLOTATO_CLIENT_ID=your_client_id_here
BLOTATO_CLIENT_SECRET=your_client_secret_here
BLOTATO_REDIRECT_URI=https://your-api.com/api/social/callback
BLOTATO_API_BASE_URL=https://app.blotato.com
BLOTATO_OAUTH_URL=https://app.blotato.com/oauth/authorize
```

## Database Schema

### SocialAccount Table

```sql
CREATE TABLE social_accounts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    account_id VARCHAR(255) NOT NULL,
    account_name VARCHAR(255) NOT NULL,
    platform_user_id VARCHAR(255) NOT NULL,
    platform_handle VARCHAR(255),
    profile_picture VARCHAR(500),
    followers_count INTEGER DEFAULT 0,
    connected_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP,
    last_post_id VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    access_token VARCHAR(1000) NOT NULL,
    refresh_token VARCHAR(1000),
    token_expires_at TIMESTAMP,
    rate_limit_remaining INTEGER DEFAULT 30,
    rate_limit_reset_at TIMESTAMP,
    error_message VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_social_accounts_user_id ON social_accounts(user_id);
CREATE INDEX idx_social_accounts_platform ON social_accounts(platform);
CREATE INDEX idx_social_accounts_account_id ON social_accounts(account_id);
CREATE INDEX idx_social_accounts_is_active ON social_accounts(is_active);
```

## API Endpoints

### 1. Initiate OAuth Connection

**Endpoint:** `POST /api/social/connect/{platform}`

**Authentication:** Required (Bearer Token)

**Parameters:**
- `platform` (path): Social platform name (e.g., 'facebook', 'twitter', 'instagram', 'linkedin')

**Response:**
```json
{
  "auth_url": "https://app.blotato.com/oauth/authorize?response_type=code&client_id=...",
  "platform": "facebook",
  "state": "secure_state_token_for_csrf_protection"
}
```

**Usage (Flutter):**
```dart
// 1. Get auth URL
final response = await http.post(
  Uri.parse('https://your-api.com/api/social/connect/facebook'),
  headers: {'Authorization': 'Bearer $token'},
);
final data = jsonDecode(response.body);
final authUrl = data['auth_url'];

// 2. Open in WebView/Browser
if (await canLaunch(authUrl)) {
  await launch(authUrl, forceSafariVC: false, forceWebView: false);
}
```

---

### 2. OAuth Callback Handler

**Endpoint:** `GET /api/social/callback`

**Query Parameters:**
- `code`: OAuth authorization code from Blotato
- `state`: CSRF protection token (must match the state from step 1)

**Response:**
```json
{
  "success": true,
  "message": "Account connected successfully",
  "account_id": 123,
  "platform": "facebook",
  "account_name": "John Doe"
}
```

**Automatic Handling:**
- This endpoint is called automatically by Blotato when the user authorizes
- The callback exchanges the OAuth code for access tokens
- Account information is stored in the database
- Tokens are encrypted in production

---

### 3. List Connected Accounts

**Endpoint:** `GET /api/social/accounts`

**Authentication:** Required (Bearer Token)

**Response:**
```json
[
  {
    "id": 1,
    "platform": "facebook",
    "account_name": "John Doe",
    "platform_user_id": "fb_123456",
    "platform_handle": "johndoe",
    "profile_picture": "https://...",
    "followers_count": 5000,
    "is_active": true,
    "connected_at": "2026-03-13T10:00:00",
    "last_used_at": "2026-03-13T15:30:00"
  },
  {
    "id": 2,
    "platform": "twitter",
    "account_name": "@johndoe",
    "platform_user_id": "tw_789012",
    "platform_handle": "johndoe",
    "profile_picture": "https://...",
    "followers_count": 3000,
    "is_active": true,
    "connected_at": "2026-03-12T08:00:00",
    "last_used_at": null
  }
]
```

---

### 4. Disconnect Account

**Endpoint:** `DELETE /api/social/accounts/{account_id}`

**Authentication:** Required (Bearer Token)

**Parameters:**
- `account_id` (path): ID of the social account to disconnect

**Response:**
```json
{
  "success": true,
  "message": "Account disconnected successfully",
  "account_id": 1
}
```

---

### 5. Publish Post to Social Accounts

**Endpoint:** `POST /api/social/post`

**Authentication:** Required (Bearer Token)

**Request Body:**
```json
{
  "account_ids": [1, 2],
  "content": "Check out this amazing content! 🎉",
  "media_urls": [
    "https://example.com/image1.jpg",
    "https://example.com/image2.png"
  ],
  "schedule_time": "2026-03-15T14:00:00Z"
}
```

**Parameters:**
- `account_ids` (required): Array of SocialAccount IDs to post to
- `content` (required): Post content (text)
- `media_urls` (optional): Array of media URLs to attach
- `schedule_time` (optional): ISO 8601 datetime to schedule the post

**Response:**
```json
{
  "success": true,
  "message": "Post published successfully",
  "post_id": "post_abc123",
  "accounts_posted": 2
}
```

**Error Response (Partial Failure):**
```json
{
  "success": false,
  "message": "Post partially published with errors",
  "post_id": null,
  "accounts_posted": 1
}
```

---

## Features & Implementation Details

### OAuth Flow

1. **Initiate Connection**: User clicks "Connect Facebook" button in app
2. **Authorization URL**: Backend generates OAuth URL with CSRF state token
3. **User Authorization**: User logs in to Blotato and approves access
4. **Callback**: Blotato redirects to `/api/social/callback` with authorization code
5. **Token Exchange**: Backend exchanges code for access tokens
6. **Account Storage**: Account data is stored with encrypted tokens

### Rate Limiting

- **Limit**: 30 posts per minute per account
- **Tracking**: `rate_limit_remaining` field updated after each post
- **Reset**: Automatic reset tracked via `rate_limit_reset_at`
- **Error Handling**: Posts fail with rate limit error if exceeded

### Token Management

- **Access Token**: Short-lived token for API requests (~1 hour)
- **Refresh Token**: Long-lived token for renewal
- **Auto-Refresh**: Tokens are automatically refreshed before expiry
- **Buffer**: System refreshes tokens 5 minutes before expiry
- **Encryption**: Tokens should be encrypted in production database

### Media Upload

- **Formats Supported**: JPG, PNG, GIF, MP4, WebM (per Blotato specs)
- **Blotato Upload**: Media is uploaded via `/v2/media-upload/url`
- **Attachment**: Media IDs are included in post payload
- **Fallback**: Failed media doesn't block post creation

### Error Handling

| Scenario | Handling |
|----------|----------|
| Invalid Account ID | Returns 404, validates ownership |
| Rate Limited | Returns error, prevents post |
| Expired Token | Auto-refreshes, retries post |
| Failed Refresh | Stores error message, marks account |
| Partial Failure | Posts to successful accounts, returns failures |

---

## Flutter Integration Example

### Setup

```dart
import 'package:http/http.dart' as http;
import 'package:url_launcher/url_launcher.dart';
import 'dart:convert';

class BlotatoService {
  final String apiUrl = 'https://your-api.com';
  final String token = 'user_bearer_token';

  Future<void> connectAccount(String platform) async {
    final response = await http.post(
      Uri.parse('$apiUrl/api/social/connect/$platform'),
      headers: {'Authorization': 'Bearer $token'},
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      final authUrl = data['auth_url'];
      
      if (await canLaunch(authUrl)) {
        await launch(authUrl, forceSafariVC: false, forceWebView: false);
      }
    }
  }

  Future<List<dynamic>> getAccounts() async {
    final response = await http.get(
      Uri.parse('$apiUrl/api/social/accounts'),
      headers: {'Authorization': 'Bearer $token'},
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    throw Exception('Failed to fetch accounts');
  }

  Future<void> publishPost({
    required List<int> accountIds,
    required String content,
    List<String>? mediaUrls,
    String? scheduleTime,
  }) async {
    final response = await http.post(
      Uri.parse('$apiUrl/api/social/post'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'account_ids': accountIds,
        'content': content,
        'media_urls': mediaUrls,
        'schedule_time': scheduleTime,
      }),
    );

    if (response.statusCode != 200) {
      throw Exception('Failed to publish post: ${response.body}');
    }
  }

  Future<void> disconnectAccount(int accountId) async {
    final response = await http.delete(
      Uri.parse('$apiUrl/api/social/accounts/$accountId'),
      headers: {'Authorization': 'Bearer $token'},
    );

    if (response.statusCode != 200) {
      throw Exception('Failed to disconnect account');
    }
  }
}
```

### Usage in Flutter UI

```dart
class SocialMediaPage extends StatefulWidget {
  @override
  State<SocialMediaPage> createState() => _SocialMediaPageState();
}

class _SocialMediaPageState extends State<SocialMediaPage> {
  final BlotatoService _service = BlotatoService();
  List<dynamic> accounts = [];

  @override
  void initState() {
    super.initState();
    _loadAccounts();
  }

  Future<void> _loadAccounts() async {
    try {
      final result = await _service.getAccounts();
      setState(() => accounts = result);
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e')),
      );
    }
  }

  Future<void> _connectPlatform(String platform) async {
    try {
      await _service.connectAccount(platform);
      // Reload accounts after user returns from OAuth
      await Future.delayed(Duration(seconds: 2));
      _loadAccounts();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e')),
      );
    }
  }

  Future<void> _publishPost() async {
    try {
      final selectedIds = accounts
          .where((acc) => acc['is_active'])
          .map((acc) => acc['id'])
          .cast<int>()
          .toList();

      await _service.publishPost(
        accountIds: selectedIds,
        content: 'Check out this post!',
        mediaUrls: ['https://example.com/image.jpg'],
      );

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Post published!')),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Social Media')),
      body: ListView(
        children: [
          Padding(
            padding: EdgeInsets.all(16),
            child: Column(
              children: [
                ElevatedButton(
                  onPressed: () => _connectPlatform('facebook'),
                  child: Text('Connect Facebook'),
                ),
                ElevatedButton(
                  onPressed: () => _connectPlatform('twitter'),
                  child: Text('Connect Twitter'),
                ),
              ],
            ),
          ),
          ListView.builder(
            itemCount: accounts.length,
            itemBuilder: (context, index) {
              final account = accounts[index];
              return ListTile(
                leading: CircleAvatar(
                  backgroundImage: NetworkImage(account['profile_picture']),
                ),
                title: Text(account['account_name']),
                subtitle: Text(account['platform']),
                trailing: account['is_active']
                    ? Icon(Icons.check, color: Colors.green)
                    : Icon(Icons.close, color: Colors.red),
              );
            },
          ),
          Padding(
            padding: EdgeInsets.all(16),
            child: ElevatedButton(
              onPressed: _publishPost,
              child: Text('Publish Post'),
            ),
          ),
        ],
      ),
    );
  }
}
```

---

## Security Considerations

1. **Token Encryption**: Store access tokens encrypted at rest
2. **HTTPS Only**: All API calls must use HTTPS in production
3. **CSRF Protection**: State tokens prevent CSRF attacks
4. **Scope Limiting**: Request only necessary OAuth scopes
5. **Token Rotation**: Implement refresh token rotation
6. **Rate Limiting**: Implement API rate limiting on all endpoints
7. **Input Validation**: Sanitize user content before posting
8. **Audit Logging**: Log all account connections and post publishes

---

## Troubleshooting

### "Invalid state token"
- State token expired (valid for ~30 minutes)
- User took too long to authorize
- Solution: Restart the connection process

### "Rate limit exceeded"
- Account has reached 30 posts/minute limit
- Wait for limit reset (tracked in `rate_limit_reset_at`)
- Solution: Return error to user, allow retry after reset

### "Token expired"
- Access token expired and refresh failed
- Account credentials may be invalid
- Solution: User must reconnect account

### "Account not found"
- Account was deleted from Blotato
- User removed account authorization
- Solution: Suggest reconnecting account

---

## Migration Guide

To add Blotato integration to existing databases:

```bash
# Generate migration
alembic revision --autogenerate -m "Add social account support"

# Review migration in alembic/versions/

# Apply migration
alembic upgrade head
```

The migration will automatically create the `social_accounts` table with all required columns.

---

## Testing

### Unit Tests

```python
import pytest
from core.blotato.service.blotato_service import BlotatoService
from core.blotato.model.SocialAccount import SocialAccount

@pytest.fixture
def db_session():
    # Setup test database
    pass

def test_connect_account(db_session):
    service = BlotatoService(db_session)
    account = service.connect_account(
        user_id=1,
        platform='facebook',
        code='test_code',
        access_token='test_token'
    )
    assert account.platform == 'facebook'

def test_publish_post(db_session):
    service = BlotatoService(db_session)
    result = service.publish_post(
        user_id=1,
        account_ids=[1],
        content='Test post'
    )
    assert result['success'] == True
```

### Integration Tests

Use Blotato's sandbox environment for testing without publishing real posts.

---

## Support & Resources

- **Blotato API Docs**: https://docs.blotato.com
- **Blotato Dashboard**: https://app.blotato.com
- **API Support**: support@blotato.com

