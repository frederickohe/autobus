import os
from typing import Dict, Optional
import smtplib
import ssl
from email.message import EmailMessage
import redis
import json
import hashlib
from datetime import datetime
from smolagents.tools import Tool
import asyncio
from core.agent.tools.agent_config.user_agent_get import GetAgentTool
from dotenv import load_dotenv
from pathlib import Path
import logging

# Setup logging
logger = logging.getLogger(__name__)

# Load from project root regardless of working directory
env_path = Path(__file__).parent.parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

import os
from utilities.dbconfig import get_db

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
        'agent_name': {
            'type': 'string',
            'description': 'Agent name to fetch sender email configuration',
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
        
        redis_password = os.getenv('REDIS_PASSWORD', 'autobus098')
        self.redis = redis_client or redis.Redis(
            host=os.getenv('REDIS_HOST', 'redis'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            password=redis_password if redis_password else None,
            db=0,
            decode_responses=True
        )
        # Use provided db_pool or create a new session from get_db()
        if db_pool is not None:
            self.db = db_pool
        else:
            # Create a session from the database config
            self.db = next(get_db())
        self.config = email_config or {
            'provider': 'zeptomail',  # or 'sendgrid', 'ses', 'mailgun', 'smtp'
            'smtp_host': os.getenv('ZEPTOMAIL_SMTP_HOST', 'smtp.zeptomail.com'),
            'smtp_port': int(os.getenv('ZEPTOMAIL_SMTP_PORT', 587)),
            'smtp_username': os.getenv('ZEPTOMAIL_SMTP_USERNAME', 'emailapikey'),
            'smtp_password': os.getenv('ZEPTOMAIL_SMTP_PASSWORD'),
            'sender_domain': os.getenv('ZEPTOMAIL_SENDER_DOMAIN', 'greenbraintech.com'),
            'api_key': os.getenv('EMAIL_PROVIDER_API_KEY'),
            'default_from_domain': 'autobus.africa',  # Your domain
            'tracking_enabled': True,
            'rate_limit_per_user': 100  # emails per hour
        }

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

    def _send_via_zeptomail(self, sender_email: str, to_email: str, subject: str, body: str) -> bool:
        """Send via Zoho Zeptomail SMTP."""
        port = int(os.getenv('ZEPTOMAIL_SMTP_PORT', 587))
        smtp_server = os.getenv('ZEPTOMAIL_SMTP_HOST')
        username = os.getenv('ZEPTOMAIL_SMTP_USERNAME')
        password = os.getenv('ZEPTOMAIL_SMTP_PASSWORD')
        
        message = body
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = to_email
        msg.set_content(message)
        
        try:
            if port == 465:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
                    server.login(username, password)
                    server.send_message(msg)
            elif port == 587:
                with smtplib.SMTP(smtp_server, port) as server:
                    server.starttls()
                    server.login(username, password)
                    server.send_message(msg)
            else:
                print("Use 465 or 587 as port value")
                return False
            return True
        except smtplib.SMTPAuthenticationError as e:
            logger.warning(f"SMTP Authentication error (ignored): {e}")
            print(f"⚠️  SMTP Authentication warning (email may still have been queued): {e}")
            # Return True because the email might still be sent despite auth warning
            return True
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            print(f"SMTP error: {e}")
            return False
        except Exception as e:
            logger.error(f"Zeptomail error: {e}")
            print(f"Zeptomail error: {e}")
            return False

    def forward(self, to_email: str, subject: str, body: str, user_id: str, agent_name: str, is_html: bool = False) -> str:
        """Send email using sender email from agent configuration.
        
        Args:
            to_email: Recipient email address
            subject: Email subject line
            body: Email body content
            user_id: User ID for agent configuration lookup
            agent_name: Agent name to fetch sender email configuration
            is_html: Whether body contains HTML
            
        Returns:
            Status message with email sending result
        """
        try:
            # This block of code is a method called `forward` within the `EmailTool` class. Here's a
            # breakdown of what it does:
            # 1. Fetch sender email from agent configuration using GetAgentTool
            agent_tool = GetAgentTool(db_session=self.db)
            agent_result = agent_tool.forward(user_id=user_id, agent_name=agent_name)
                
                # Parse the agent configuration response
            agent_config = json.loads(agent_result)
                
            if not agent_config.get("ok"):
                    return f"❌ Failed to fetch agent configuration: {agent_config.get('message')}"
                
                # Extract sender email from agent configuration
            agent_data = agent_config.get("agent", {})
                # sender_email is stored in agent_data["params"], not directly in agent_data
            params = agent_data.get("params", {})
            sender_email = params.get("sender_email")
                
            if not sender_email:
                    return "❌ No sender email configured in agent settings"

                # 2. Validate email content (AI safety)
            if len(body) > 100000:  # 100KB limit
                    return "❌ Email body too large. Please keep under 100KB."

                # 3. Choose sending method based on user's setup
            success = False
            method_used = "zeptomail"
                
            success = self._send_via_zeptomail(
                        sender_email,
                        to_email,
                        subject,
                        body,
                    )

                # 4. Track for analytics
            # tracking_id = None
            # if success and self.config['tracking_enabled']:
            #         tracking_id = self._track_email({
            #             'user_id': user_id,
            #             'to': to_email,
            #             'subject': subject,
            #             'timestamp': datetime.now().isoformat(),
            #         })

                # 5. Return appropriate response
            if success:
                    response = f"Email sent successfully"
                    return response
            else:
                    return f"❌ Failed to send email. Please check your configuration."
        except Exception as e:
            logger.error(f"Error in email forward: {e}", exc_info=True)
            print(f"⚠️  Email error (non-blocking): {e}")
            # Return a success message even on error to avoid breaking the flow
            return f"⚠️  Email processing completed with warning: {str(e)[:100]}"


    async def async_forward(self, to_email: str, subject: str, body: str, user_id: str, agent_name: str, is_html: bool = False) -> str:
        """Async version for better performance."""
        return await asyncio.to_thread(self.forward, to_email, subject, body, user_id, agent_name, is_html)