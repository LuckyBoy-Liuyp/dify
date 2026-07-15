"""
Service for syncing app information to external knowledge platform.
"""

import hashlib
import hmac
import json
import logging
import secrets
import time

import httpx

from configs import dify_config
from models.model import App

logger = logging.getLogger(__name__)


class KnowledgePlatformSyncService:
    """
    Service to sync app/agent information to knowledge platform.
    """

    def __init__(self) -> None:
        self.base_url = dify_config.KNOWLEDGE_PLATFORM_BASE_URL
        self.enabled = dify_config.KNOWLEDGE_PLATFORM_SYNC_ENABLED
        self.app_key = dify_config.KNOWLEDGE_PLATFORM_APP_KEY or ""
        self.app_secret = dify_config.KNOWLEDGE_PLATFORM_APP_SECRET or ""
        self.sync_route = "/qaIntagtInfo/ext/saveOrUpdateQaIntagtInfo"

    def _generate_signature(self, params: dict) -> str:
        """
        Generate HMAC-SHA256 signature for request authentication.

        Args:
            params: Request parameters including appsecret

        Returns:
            str: Hex digest signature (lowercase)
        """
        appkey = params.get("appkey", "")
        appsecret = params.get("appsecret", "")
        nonce = params.get("nonce", "")
        timestamp = params.get("timestamp", "")

        # Build sign string in fixed order
        sign_str = f"appkey={appkey}&appsecret={appsecret}&nonce={nonce}&timestamp={timestamp}"

        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            appsecret.encode("utf-8"),
            sign_str.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return signature

    def _build_auth_headers(self) -> dict:
        """
        Build authentication headers with signature.

        Returns:
            dict: Headers with auth parameters
        """
        timestamp = str(int(time.time() * 1000))
        nonce = str(secrets.randbelow(90000000) + 10000000)

        # Build params for signature
        params = {
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "nonce": nonce,
            "timestamp": timestamp,
        }

        # Generate signature
        sign = self._generate_signature(params)

        # Return headers (without plaintext appsecret)
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "appkey": self.app_key,
            "nonce": nonce,
            "timestamp": timestamp,
            "sign": sign,
        }

    def sync_app_info(self, app_model: App, creator_mobile: str | None = None) -> dict:
        """
        Sync app information to knowledge platform after workflow publish.

        Args:
            app_model: The app model to sync
            creator_mobile: Creator's mobile number (optional)

        Returns:
            dict: Response from knowledge platform API
        """
        if not self.enabled:
            logger.debug("Knowledge platform sync is disabled")
            return {"success": False, "message": "Sync disabled"}

        if not self.base_url:
            logger.warning("Knowledge platform base URL is not configured")
            return {"success": False, "message": "Base URL not configured"}

        try:
            # Prepare agent data
            intagt_data = self._prepare_agent_data(app_model, creator_mobile)

            # Build API URL
            api_url = f"{self.base_url + self.sync_route}"

            # Build auth headers with signature
            headers = self._build_auth_headers()
            logger.info("Knowledge platform request for app %s: %s", app_model.id, intagt_data)
            # Send request using httpx
            with httpx.Client(timeout=60) as client:
                response = client.post(api_url, headers=headers, json=intagt_data)
            # Parse response
            result = response.json()
            logger.info("Knowledge platform response for app %s: %s", app_model.id, result)

            return result

        except httpx.RequestError as e:
            logger.exception("Connection error when syncing app %s", app_model.id)
            return {"success": False, "message": f"Connection error: {str(e)}"}

        except httpx.TimeoutException:
            logger.exception("Timeout when syncing app %s to knowledge platform", app_model.id)
            return {"success": False, "message": "Request timeout"}

        except json.JSONDecodeError:
            logger.exception("Invalid JSON response from knowledge platform for app %s", app_model.id)
            return {"success": False, "message": "Invalid response format"}

        except Exception as e:
            logger.exception("Unexpected error when syncing app %s to knowledge platform", app_model.id)
            return {"success": False, "message": f"Unexpected error: {str(e)}"}

    def _prepare_agent_data(self, app_model: App, creator_mobile: str | None = None) -> dict:
        """
        Prepare agent data from app model.

        Args:
            app_model: The app model
            creator_mobile: Creator's mobile number (optional)

        Returns:
            dict: Formatted agent data for knowledge platform
        """
        # Get description from app or prompt
        description = app_model.description
        if not description and app_model.app_model_config:
            description = app_model.app_model_config.pre_prompt or ""
            # Truncate if too long
            if len(description) > 500:
                description = description[:500] + "..."

        # Determine agent type based on mode
        intagt_type = "1"  # Default: conversation agent
        if app_model.mode == "workflow":
            intagt_type = "2"  # Workflow agent

        return {
            "intagtName": app_model.name,
            "introduction": description,
            "intagtLogoUrl": '',
            "showStatus": "1",  # Show by default
            "extId": app_model.id,  # Use app ID as external ID
            "publicStatus": "1" if app_model.is_public else "0",
            "orderId": 999,
            "intagtType": intagt_type,
            "visitorOpenStatus": "1" if app_model.enable_site else "0",
            "dataSource": "dify",
            "mobile": creator_mobile or "",
        }

    def sync_app_api_key(self, app_id: str, api_key: str, creator_mobile: str | None = None) -> dict:
        """
        Sync app API key to knowledge platform.

        Args:
            app_id: The app ID
            api_key: The API key to sync
            creator_mobile: Creator's mobile number (optional)

        Returns:
            dict: Response from knowledge platform API
        """
        if not self.enabled:
            logger.debug("Knowledge platform sync is disabled")
            return {"success": False, "message": "Sync disabled"}

        if not self.base_url:
            logger.warning("Knowledge platform base URL is not configured")
            return {"success": False, "message": "Base URL not configured"}

        try:
            api_url = f"{self.base_url + self.sync_route}"
            intagt_data = {
                "extId": app_id,
                "intagtApikey": api_key,
                "mobile": creator_mobile or "",
            }

            headers = self._build_auth_headers()
            logger.info("Knowledge platform API key sync request for app %s: %s", app_id, intagt_data)
            with httpx.Client(timeout=60) as client:
                response = client.post(api_url, headers=headers, json=intagt_data)

            result = response.json()
            logger.info("Knowledge platform API key sync response for app %s: %s", app_id, result)

            return result

        except httpx.RequestError as e:
            logger.exception("Connection error when syncing API key for app %s", app_id)
            return {"success": False, "message": f"Connection error: {str(e)}"}

        except httpx.TimeoutException:
            logger.exception("Timeout when syncing API key for app %s to knowledge platform", app_id)
            return {"success": False, "message": "Request timeout"}

        except json.JSONDecodeError:
            logger.exception("Invalid JSON response from knowledge platform for app %s API key", app_id)
            return {"success": False, "message": "Invalid response format"}

        except Exception as e:
            logger.exception("Unexpected error when syncing API key for app %s to knowledge platform", app_id)
            return {"success": False, "message": f"Unexpected error: {str(e)}"}
