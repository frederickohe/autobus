import json
import os
from pathlib import Path

import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Service for sending messages via Meta's WhatsApp Cloud API"""

    def __init__(self):
        self.api_key = os.getenv("META_API_KEY")
        self.base_url = (
            os.getenv("WHATSAPP_GRAPH_BASE_URL") or "https://graph.facebook.com/v25.0"
        ).rstrip("/")
        self.default_phone_id = (os.getenv("WHATSAPP_phone_ID") or "").strip()

    def create_registration_flow(self, phone_id: str) -> Optional[str]:
        """
        Create the registration Flow template in Meta using the local JSON definition.

        Args:
            phone_id: Meta phone number ID to associate with the Flow

        Returns:
            Optional[str]: The created flow_id, if successful
        """
        json_path = (
            Path(__file__).resolve().parent.parent
            / "templates"
            / "registration_form_flow.json"
        )

        try:
            with open(json_path, "r", encoding="utf-8") as flow_file:
                flow_definition = json.load(flow_file)
        except FileNotFoundError:
            logger.error(f"Flow definition file not found: {json_path}")
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        url = f"{self.base_url}/{phone_id}/flows"
        payload = {
            "flow": flow_definition
        }

        try:
            logger.info(f"Creating WhatsApp registration Flow for {phone_id}")
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            flow_id = data.get("id")
            logger.info(f"Registration Flow created with id: {flow_id}")
            return flow_id

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create WhatsApp registration Flow: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Response content: {e.response.text}")
            return None

    def send_message(
        self,
        phone_id: str,
        recipient_phone: str,
        message_text: str,
        preview_url: bool = False
    ) -> bool:
        """
        Send a text message via WhatsApp Cloud API

        Args:
            phone_id: The phone number ID from Meta webhook metadata
            recipient_phone: The recipient's WhatsApp ID (phone number)
            message_text: The message to send
            preview_url: Whether to show URL preview in the message

        Returns:
            bool: True if message sent successfully, False otherwise
        """
        url = f"{self.base_url}/{phone_id}/messages"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_phone,
            "type": "text",
            "text": {
                "preview_url": preview_url,
                "body": message_text
            }
        }

        try:
            logger.info(f"Sending WhatsApp text message to {recipient_phone}")
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()

            logger.info(
                f"WhatsApp message sent successfully: {response.json()}")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send WhatsApp message: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.text}")
            return False

    def send_template(
        self,
        recipient_phone: str,
        template_name: str,
        language_code: str = "en_US",
        body_parameters: Optional[list] = None,
        phone_id: Optional[str] = None,
        components: Optional[list] = None,
    ) -> tuple[bool, Optional[dict], Optional[str]]:
        """
        Send a WhatsApp Cloud API template message.

        Returns:
            (ok, response_json, error_message)
        """
        resolved_phone_id = (phone_id or self.default_phone_id or "").strip()
        if not self.api_key:
            return False, None, "META_API_KEY is not configured."
        if not resolved_phone_id:
            return False, None, "WHATSAPP_phone_ID is not configured."

        url = f"{self.base_url}/{resolved_phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        template: dict = {
            "name": template_name,
            "language": {"code": language_code},
        }

        if components is not None:
            template["components"] = components
        elif body_parameters:
            template["components"] = [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": str(p)} for p in body_parameters
                    ],
                }
            ]

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_phone,
            "type": "template",
            "template": template,
        }

        try:
            logger.info(
                "Sending WhatsApp template '%s' to %s via %s",
                template_name,
                recipient_phone,
                resolved_phone_id,
            )
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            logger.info("WhatsApp template sent successfully: %s", data)
            return True, data, None
        except requests.exceptions.RequestException as e:
            err_text = ""
            if hasattr(e, "response") and e.response is not None:
                err_text = e.response.text
                logger.error("Response content: %s", err_text)
            logger.error("Failed to send WhatsApp template: %s", e)
            return False, None, err_text or str(e)

    def send_registration_template(
        self,
        phone_id: str,
        recipient_phone: str
    ) -> bool:
        """
        Send registration template via WhatsApp Cloud API
        Args:
            phone_id: The phone number ID from Meta webhook metadata
            recipient_phone: The recipient's WhatsApp ID (phone number)
        Returns:
            bool: True if template sent successfully, False otherwise
        """
        ok, _, _ = self.send_template(
            recipient_phone=recipient_phone,
            template_name="registration",
            language_code="en",
            phone_id=phone_id,
            components=[
                {
                    "type": "button",
                    "sub_type": "flow",
                    "index": "0",
                    "parameters": [
                        {
                            "type": "action",
                            "action": {
                                "flow_token": "2002104030434872"
                            }
                        }
                    ]
                }
            ],
        )
        return ok

    def send_message_receipt(
        self,
        phone_id: str,
        recipient_phone: str,
        image_url: str,
        caption: Optional[str] = None
    ) -> bool:
        """
        Send a receipt image via WhatsApp Cloud API

        Args:
            phone_id: The phone number ID from Meta webhook metadata
            recipient_phone: The recipient's WhatsApp ID (phone number)
            image_url: The URL of the receipt image to send (must be publicly accessible)
            caption: Optional caption for the receipt

        Returns:
            bool: True if receipt sent successfully, False otherwise
        """
        url = f"{self.base_url}/{phone_id}/messages"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_phone,
            "type": "image",
            "image": {
                "link": image_url
            }
        }

        # Add caption if provided
        if caption:
            payload["image"]["caption"] = caption

        try:
            logger.info(f"Sending WhatsApp receipt to {recipient_phone}")
            logger.debug(f"Receipt URL: {image_url}")
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()

            logger.info(
                f"WhatsApp receipt sent successfully: {response.json()}")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send WhatsApp receipt: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.text}")
            return False
