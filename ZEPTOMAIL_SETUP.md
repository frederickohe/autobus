# Zoho Zeptomail Email Service Integration

## Overview
This guide explains how to set up and use Zoho Zeptomail as your email service provider in the Autobus application.

## Prerequisites
- Zoho Zeptomail account with SMTP access
- SMTP credentials (hostname, port, username, password)
- Verified sender domain

## Configuration Steps

### 1. Obtain Your Zeptomail Credentials
From your Zoho Zeptomail account, collect the following:

```
Server name: smtp.zeptomail.com
Port: 587 (TLS) or 465 (SSL)
Username: emailapikey
Password: [Your API Key from platform]
Domain: greenbrain.com
```

### 2. Set Environment Variables
Add the following to your `.env` file (or copy from `.env.zeptomail.example`):

```bash
ZEPTOMAIL_SMTP_HOST=smtp.zeptomail.com
ZEPTOMAIL_SMTP_PORT=587                           # Use 587 for TLS or 465 for SSL
ZEPTOMAIL_SMTP_USERNAME=emailapikey
ZEPTOMAIL_SMTP_PASSWORD=your_api_key_here
ZEPTOMAIL_SENDER_DOMAIN=greenbraintech.com
EMAIL_PROVIDER=zeptomail
```

### 3. Port Selection
- **Port 587 (Recommended)**: Uses TLS encryption - better for IPv6 and modern systems
- **Port 465**: Uses SSL encryption - alternative option

The default configuration uses port 587 (TLS).

## Code Integration

The email service automatically uses Zeptomail when configured. The EmailTool class handles:

1. **Rate Limiting**: Prevents spam (100 emails/hour per user by default)
2. **Email Validation**: Ensures emails are within size limits
3. **Tracking**: Optional tracking ID generation for analytics
4. **Error Handling**: Comprehensive error messages

### Using the Email Tool

```python
from src.core.agent.tools.email.email import EmailTool

# Initialize the tool
email_tool = EmailTool()

# Send an email
response = email_tool.forward(
    to_email="recipient@example.com",
    subject="Hello from Autobus",
    body="This is a test email",
    user_id="user123",
    is_html=False
)

# Response contains tracking ID and confirmation
print(response)
```

### For HTML Emails

```python
html_body = """
<html>
  <body>
    <h1>Hello!</h1>
    <p>This is an HTML email</p>
  </body>
</html>
"""

response = email_tool.forward(
    to_email="recipient@example.com",
    subject="HTML Email Test",
    body=html_body,
    user_id="user123",
    is_html=True
)
```

## Features

### Automatic Features
✅ TLS/SSL support (port 587 and 465)
✅ Rate limiting per user
✅ Email size validation (max 100KB)
✅ Optional email tracking with unique IDs
✅ Redis caching for sender configuration
✅ Comprehensive error handling

### Sender Configuration
- Default sender: `noreply@greenbraintech.com`
- Sender name: `Greenbrain Tech`
- Customizable via database (when user configuration is implemented)

## Troubleshooting

### Connection Errors
- **Issue**: "SMTP connection refused"
- **Solution**: Verify ZEPTOMAIL_SMTP_HOST and ZEPTOMAIL_SMTP_PORT are correct

### Authentication Errors
- **Issue**: "Authentication failed"
- **Solution**: Verify ZEPTOMAIL_SMTP_USERNAME and ZEPTOMAIL_SMTP_PASSWORD are correct

### TLS/SSL Errors
- **Issue**: "SSL certificate verification failed"
- **Solution**: Ensure you're using the correct port (587 for TLS, 465 for SSL)

### Rate Limit Exceeded
- **Issue**: "Rate limit exceeded"
- **Solution**: Wait an hour before sending more emails, or increase RATE_LIMIT_PER_USER

## Architecture

The email service uses a modular provider system:

```
EmailTool (main class)
├── _send_via_zeptomail()      ← Zoho Zeptomail (PRIMARY)
├── _send_via_sendgrid()       ← SendGrid (alternative)
└── _send_via_smtp()           ← Generic SMTP (fallback)
```

Provider is selected based on `EMAIL_PROVIDER` environment variable.

## Testing

### Quick Test
```bash
python -c "
from src.core.agent.tools.email.email import EmailTool
tool = EmailTool()
result = tool.forward(
    to_email='cto@greenbraintech.com',
    subject='Test Email',
    body='Test message',
    user_id='test_user'
)
print(result)
"
```

### Test Port Connectivity
```bash
# Test port 587 (TLS)
python -c "import socket; s = socket.socket(); s.connect(('smtp.zeptomail.com', 587)); print('Port 587: OK')"

# Test port 465 (SSL)
python -c "import socket; s = socket.socket(); s.connect(('smtp.zeptomail.com', 465)); print('Port 465: OK')"
```

## Migration from Other Providers

If migrating from SendGrid or another provider:

1. Keep existing environment variables for backup
2. Add Zeptomail variables to `.env`
3. Set `EMAIL_PROVIDER=zeptomail`
4. Test with a sample email before full deployment
5. Monitor logs for any issues during transition

## Security Best Practices

1. **Never commit credentials** to version control
2. **Use environment variables** for all sensitive data
3. **Rotate API keys** regularly (if supported by Zeptomail)
4. **Monitor rate limits** to prevent abuse
5. **Use verified sender domains** for better deliverability
6. **Enable email tracking** for monitoring (optional)

## Additional Resources

- Zoho Zeptomail Documentation: https://www.zoho.com/zeptomail/
- SMTP Setup Guide: https://www.zoho.com/zeptomail/help/zeptomail-smtp.html
- Sender Domain Verification: https://www.zoho.com/zeptomail/help/setup/sender-domain-configuration.html

## Support

For issues or questions:
1. Check error messages for specific problems
2. Verify environment variables are set correctly
3. Review logs in Redis cache (key pattern: `email:track:*`)
4. Contact Zoho Zeptomail support if SMTP connection fails
