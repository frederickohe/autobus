import requests
import logging
from typing import Dict, Any, Optional
from config import settings
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


class WirepickSMSException(Exception):
    """Custom exception for Wirepick SMS errors"""
    pass


class WirepickSMSService:
    """Service for sending SMS via Wirepick API"""
    
    def __init__(self):
        self.base_url = settings.WIREPICK_API_URL
        self.client_id = settings.WIREPICK_CLIENT_ID
        self.password = settings.WIREPICK_PASSWORD
        self.public_key = settings.WIREPICK_PUBLIC_KEY
        self.sender_id = settings.WIREPICK_SENDER_ID
        self.use_api_key = getattr(settings, 'USE_WIREPICK_API_KEY', False)
        
    def _send_with_client_auth(self, phone: str, message: str) -> Dict[str, Any]:
        """
        Send SMS using client ID and password authentication (legacy method)
        Documentation reference: Page 2-3
        """
        url = f"{self.base_url}/send"
        
        # Prepare parameters
        params = {
            "client": self.client_id,
            "password": self.password,
            "phone": phone,
            "text": message,
            "from": self.sender_id,
            "flash": "NO",  # Regular SMS, not flash
        }
        
        try:
            logger.info(f"Sending SMS via Wirepick (client auth) to {phone}")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            # Parse XML response (documentation page 3)
            root = ET.fromstring(response.text)
            sms_element = root.find('sms')
            
            if sms_element is not None:
                msgid = sms_element.find('msgid')
                status = sms_element.find('status')
                
                return {
                    "success": True,
                    "msgid": msgid.text if msgid is not None else None,
                    "status": status.text if status is not None else None,
                    "raw_response": response.text
                }
            else:
                return {
                    "success": False,
                    "error": "Invalid response format",
                    "raw_response": response.text
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Wirepick SMS request failed: {str(e)}")
            raise WirepickSMSException(f"SMS sending failed: {str(e)}")
        except ET.ParseError as e:
            logger.error(f"Failed to parse Wirepick response: {str(e)}")
            raise WirepickSMSException(f"Invalid response from SMS provider: {str(e)}")
    
    def _send_with_api_key(self, phone: str, message: str) -> Dict[str, Any]:
        """
        Send SMS using API key authentication (newer method)
        Documentation reference: Page 5-8
        """
        url = f"{self.base_url}/sendsms"
        
        # Headers with API key
        headers = {
            "wpkKey": self.public_key,
            "Content-Type": "application/json"
        }
        
        # Request body
        payload = {
            "phone": phone,
            "text": message,
            "from": self.sender_id,
            "flash": "N",  # N for normal SMS, Y for flash
            "dlr": "Y"     # Request delivery report
        }
        
        try:
            logger.info(f"Sending SMS via Wirepick (API key auth) to {phone}")
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Parse JSON response
            data = response.json()
            messages = data.get('messages', [])
            
            if messages:
                msg = messages[0]
                return {
                    "success": True,
                    "msgid": msg.get('msgid'),
                    "status": msg.get('status'),
                    "phone": msg.get('phone'),
                    "total_cost": msg.get('totalCost'),
                    "raw_response": data
                }
            else:
                return {
                    "success": False,
                    "error": "No message in response",
                    "raw_response": data
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Wirepick SMS request failed: {str(e)}")
            # Try to get error details from response
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    logger.error(f"Wirepick error details: {error_data}")
                except:
                    pass
            raise WirepickSMSException(f"SMS sending failed: {str(e)}")
        except ValueError as e:
            logger.error(f"Failed to parse Wirepick JSON response: {str(e)}")
            raise WirepickSMSException(f"Invalid response from SMS provider: {str(e)}")
    
    def send_sms(self, phone: str, message: str) -> Dict[str, Any]:
        """
        Send SMS via Wirepick API
        
        Args:
            phone: Recipient phone number with country code (e.g., 233240115480)
            message: SMS content
            
        Returns:
            Dict with success status and message ID or error
        """
        # Validate phone number format (should include country code)
        if not phone.startswith('+') and not phone[0].isdigit():
            # Add + if not present? Better to let the API handle it
            pass
        
        # Choose authentication method based on configuration
        if self.use_api_key and self.public_key:
            return self._send_with_api_key(phone, message)
        else:
            return self._send_with_client_auth(phone, message)
    
    def check_message_status(self, msgid: str) -> Dict[str, Any]:
        """
        Query the status of a message using its msgid
        Documentation reference: Page 3
        
        Args:
            msgid: Message ID returned from send operation
        """
        if self.use_api_key and self.public_key:
            # For API key auth, we might need to use a different endpoint
            # This is based on the documentation which shows query with client/password
            url = f"{self.base_url}/querysms"
            params = {
                "msgid": msgid
            }
            headers = {
                "wpkKey": self.public_key
            }
            
            try:
                response = requests.get(url, params=params, headers=headers, timeout=30)
                response.raise_for_status()
                
                # Parse JSON response
                data = response.json()
                return {
                    "success": True,
                    "status": data.get('status'),
                    "description": data.get('description'),
                    "raw_response": data
                }
            except Exception as e:
                logger.error(f"Failed to check message status: {str(e)}")
                return {"success": False, "error": str(e)}
        else:
            # Client/password auth
            url = f"{self.base_url}/querysms"
            params = {
                "client": self.client_id,
                "password": self.password,
                "msgid": msgid
            }
            
            try:
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                # Parse XML response
                root = ET.fromstring(response.text)
                
                return {
                    "success": True,
                    "status": root.findtext('status'),
                    "description": root.findtext('description'),
                    "phone": root.findtext('phone'),
                    "raw_response": response.text
                }
            except Exception as e:
                logger.error(f"Failed to check message status: {str(e)}")
                return {"success": False, "error": str(e)}