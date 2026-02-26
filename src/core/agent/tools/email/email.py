# Enhanced EmailTool with proper infrastructure

import os
from typing import Dict, List, Optional, Any
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import redis
import json
import hashlib
from datetime import datetime, timedelta
from smolagents.tools import Tool
import aiosmtplib
import asyncio
import requests

class EmailTool(Tool):
    name = "email_tool"
    description = """Send emails using user's configured sender identity.
    Requires user to have setup sender email in their profile."""
    
    inputs = {
        'to_email': {
            'type': 'string',
            'description': 'Recipient email address',
            'required': True
        },
        'subject': {
            'type': 'string',
            'description': 'Email subject line',
            'required': True
        },
        'body': {
            'type': 'string',
            'description': 'Email body content',
            'required': True
        },
        'user_id': {
            'type': 'string',
            'description': 'User ID to lookup sender configuration',
            'required': True
        },
        'is_html': {
            'type': 'boolean',
            'description': 'Whether body contains HTML',
            'default': False,
            'nullable': True
        }
    }
    output_type = "string"

    def __init__(self, redis_client=None, db_pool=None, email_config=None):
        super().__init__()
        self.redis = redis_client or redis.Redis(host='redis', port=6379, db=0)
        self.db = db_pool  # PostgreSQL connection pool
        self.config = email_config or {
            'provider': 'sendgrid',  # or 'ses', 'mailgun', 'smtp'
            'api_key': os.getenv('EMAIL_PROVIDER_API_KEY'),
            'default_from_domain': 'autobus.africa',  # Your domain
            'tracking_enabled': True,
            'rate_limit_per_user': 100  # emails per hour
        }

    def _get_user_sender_config(self, user_id: str) -> Optional[Dict]:
        """Retrieve user's configured sender email from database."""
        # Cache in Redis first
        cache_key = f"user:email_config:{user_id}"
        cached = self.redis.get(cache_key)
        
        if cached:
            return json.loads(cached)
        
        # Query PostgreSQL
        # async with self.db.acquire() as conn:
        #     result = await conn.fetchrow(
        #         "SELECT sender_email, sender_name, smtp_config FROM user_email_settings WHERE user_id = $1",
        #         user_id
        #     )
        #     if result:
        #         config = dict(result)
        #         self.redis.setex(cache_key, 300, json.dumps(config))  # Cache 5 mins
        #         return config
        
        # Simulated for now
        return {
            'sender_email': 'business@userdomain.com',
            'sender_name': 'Business Name',
            'smtp_config': {
                'host': 'smtp.sendgrid.net',
                'port': 587,
                'username': 'apikey',
                'password': os.getenv('SENDGRID_API_KEY')
            }
        }

    def _check_rate_limit(self, user_id: str) -> bool:
        """Enforce rate limiting per user."""
        key = f"rate:email:{user_id}:{datetime.now().strftime('%Y%m%d%H')}"
        current = self.redis.incr(key)
        if current == 1:
            self.redis.expire(key, 3600)  # Expire in 1 hour
        return current <= self.config['rate_limit_per_user']

    def _track_email(self, email_data: Dict):
        """Store email metadata for analytics and audit."""
        tracking_id = hashlib.md5(
            f"{email_data['to']}:{email_data['timestamp']}".encode()
        ).hexdigest()
        
        # Store in Redis with expiration for real-time tracking
        self.redis.setex(
            f"email:track:{tracking_id}", 
            86400 * 7,  # 7 days
            json.dumps({
                **email_data,
                'status': 'sent',
                'opens': 0,
                'clicks': 0
            })
        )
        
        # Also store permanently in PostgreSQL
        # async with self.db.acquire() as conn:
        #     await conn.execute(
        #         "INSERT INTO email_logs (tracking_id, user_id, to_email, subject, status) VALUES ($1, $2, $3, $4, $5)",
        #         tracking_id, email_data['user_id'], email_data['to'], email_data['subject'], 'sent'
        #     )
        
        return tracking_id

    def _send_via_sendgrid(self, from_email: str, to_email: str, subject: str, body: str, is_html: bool = False) -> bool:
        """Send via SendGrid API (recommended for MVP)."""
        import sendgrid
        from sendgrid.helpers.mail import Mail, Email, To, Content
        
        sg = sendgrid.SendGridAPIClient(api_key=self.config['api_key'])
        
        mail = Mail(
            from_email=Email(from_email),
            to_emails=To(to_email),
            subject=subject,
            plain_text_content=Content("text/plain", body) if not is_html else None,
            html_content=Content("text/html", body) if is_html else None
        )
        
        response = sg.send(mail)
        return response.status_code in [200, 202]

    def _send_via_smtp(self, from_email: str, to_email: str, subject: str, body: str, smtp_config: Dict, is_html: bool = False) -> bool:
        """Send via custom SMTP (for advanced users)."""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = to_email
        
        if is_html:
            part = MIMEText(body, 'html')
        else:
            part = MIMEText(body, 'plain')
        msg.attach(part)
        
        try:
            with smtplib.SMTP(smtp_config['host'], smtp_config['port']) as server:
                server.starttls()
                server.login(smtp_config['username'], smtp_config['password'])
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"SMTP error: {e}")
            return False

    def forward(self, to_email: str, subject: str, body: str, user_id: str, is_html: bool = False) -> str:
        """Send email using user's configured sender."""
        try:
            # 1. Check rate limit
            if not self._check_rate_limit(user_id):
                return "❌ Rate limit exceeded. Please wait before sending more emails."

            # 2. Get user's sender configuration
            sender_config = self._get_user_sender_config(user_id)
            if not sender_config:
                return "❌ No sender email configured. Please set up your sender email first."

            # 3. Validate email content (AI safety)
            if len(body) > 100000:  # 100KB limit
                return "❌ Email body too large. Please keep under 100KB."

            # 4. Choose sending method based on user's setup
            success = False
            method_used = "unknown"
            
            if self.config['provider'] == 'sendgrid':
                success = self._send_via_sendgrid(
                    sender_config['sender_email'],
                    to_email,
                    subject,
                    body,
                    is_html
                )
                method_used = "SendGrid"
            else:
                success = self._send_via_smtp(
                    sender_config['sender_email'],
                    to_email,
                    subject,
                    body,
                    sender_config.get('smtp_config', {}),
                    is_html
                )
                method_used = "SMTP"

            # 5. Track for analytics
            tracking_id = None
            if success and self.config['tracking_enabled']:
                tracking_id = self._track_email({
                    'user_id': user_id,
                    'to': to_email,
                    'subject': subject,
                    'timestamp': datetime.now().isoformat(),
                    'method': method_used
                })

            # 6. Return appropriate response
            if success:
                response = f"✅ Email sent successfully via {method_used}\n"
                response += f"📧 To: {to_email}\n"
                response += f"📝 Subject: {subject}\n"
                if tracking_id:
                    response += f"🔍 Tracking ID: {tracking_id}\n"
                    response += f"📊 Track opens: https://analytics.autobus.africa/email/{tracking_id}"
                return response
            else:
                return f"❌ Failed to send email. Please check your configuration."

        except Exception as e:
            return f"❌ Error sending email: {str(e)}"

    async def async_forward(self, to_email: str, subject: str, body: str, user_id: str, is_html: bool = False) -> str:
        """Async version for better performance."""
        return await asyncio.to_thread(self.forward, to_email, subject, body, user_id, is_html)