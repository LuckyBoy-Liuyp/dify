"""
企业内部 Ticket SSO 认证服务

用于与企业内部票务系统进行单点登录集成
"""

import hashlib
import hmac as hmac_lib
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import httpx

from configs import dify_config
from libs.passport import PassportService

logger = logging.getLogger(__name__)


@dataclass
class TicketUserInfo:
    """Ticket 用户信息数据结构"""

    user_id: str
    username: str
    email: str
    display_name: str
    department: str | None = None
    roles: list[str] | None = None
    appkey: str | None = None

    # 扩展字段（根据实际响应添加）
    user_code: str | None = None  # 用户编码
    true_name: str | None = None  # 真实姓名（加密）
    login_name: str | None = None  # 登录名
    mobile: str | None = None  # 手机号（加密）
    adcd: str | None = None  # 行政区划代码
    ad_name: str | None = None  # 行政区划名称
    original: str | None = None  # 原始标识
    visitor: str | None = None  # 访客标识
    emp_code: str | None = None  # 员工编码

    @classmethod
    def from_dict(cls, data: dict) -> "TicketUserInfo":
        """从字典创建对象"""
        return cls(
            user_id=data.get("userCode", "") or data.get("user_id", ""),
            username=data.get("loginName", "") or data.get("username", ""),
            email=data.get("mobile", "") or data.get("email", ""),  # 如果没有邮箱，用手机号代替
            display_name=data.get("trueName", "") or data.get("displayName", ""),
            department=data.get("adName"),
            roles=[data.get("adcd")] if data.get("adcd") else None,
            appkey=data.get("appkey"),
            # 扩展字段
            user_code=data.get("userCode"),
            true_name=data.get("trueName"),
            login_name=data.get("loginName"),
            mobile=data.get("mobile"),
            adcd=data.get("adcd"),
            ad_name=data.get("adName"),
            original=data.get("original"),
            visitor=data.get("visitor"),
            emp_code=data.get("empCode")
        )


class TicketSSOService:
    """企业 Ticket SSO 认证服务类"""

    def __init__(self):
        self.ticket_server_url = dify_config.ENTERPRISE_TICKET_SERVER_URL
        self.ticket_server_validate_url = dify_config.ENTERPRISE_TICKET_SERVER_VALIDATE_URL
        self.ticket_secret_key = dify_config.ENTERPRISE_TICKET_SECRET_KEY
        self.timeout = dify_config.ENTERPRISE_TICKET_TIMEOUT or 30

    def _generate_signature(self, params: dict[str, Any]) -> str:
        """
        生成请求签名（使用 HmacSHA256）

        签名算法（与 Postman 脚本一致）：
        1. 拼接固定格式字符串：appsecret={appSecret}&nonce={nonce}&ticket={ticket}&timestamp={timestamp}
        2. 使用 HmacSHA256 加密，密钥为 appsecret
        3. 转为十六进制字符串（小写）

        Args:
            params: 请求参数字典

        Returns:
            str: 签名结果（64 位小写十六进制）
        """
        # 提取关键参数
        appsecret = params.get("appsecret")
        nonce = params.get("nonce", "")
        ticket = params.get("ticket", "")
        timestamp = params.get("timestamp", "")

        # 拼接待签名字符串（固定顺序）
        sign_str = f"appsecret={appsecret}&nonce={nonce}&ticket={ticket}&timestamp={timestamp}"

        logger.debug("待签名字符串：%s", sign_str)

        try:
            # 使用 HmacSHA256 加密
            signature = hmac_lib.new(
                appsecret.encode('utf-8'),
                sign_str.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

            logger.debug("生成的签名值：%s", signature)
            return signature

        except Exception as e:
            logger.exception("HmacSHA256 加密计算失败")
            raise ValueError(f"签名计算失败：{str(e)}")

    def _build_validate_request_body(self, ticket: str) -> dict[str, Any]:
        """
        构建验证 Ticket 的请求体

        Args:
            ticket: 企业票务系统颁发的 ticket

        Returns:
            dict: 包含签名的请求体
        """
        # 生成时间戳（毫秒级）
        timestamp = str(int(time.time() * 1000))

        # 生成随机数
        import secrets
        nonce = str(secrets.randbelow(90000000) + 10000000)

        # 使用环境变量中的 appkey/appsecret，如果没有则使用默认值
        appsecret = self.ticket_secret_key or ""

        # 构建基础参数
        params = {
            "appsecret": appsecret,  # 注意：这里需要 appsecret 用于签名生成
            "nonce": nonce,
            "ticket": ticket,
            "timestamp": timestamp
        }

        # 生成签名（签名计算会使用 appsecret）
        sign = self._generate_signature(params)

        # 构建最终请求体（移除明文 appsecret，只保留签名）
        request_body = {
            "nonce": nonce,
            "sign": sign,
            "timestamp": timestamp,
            "ticket": ticket
        }

        logger.info("Built validate request with ticket: %s..., nonce: %s, timestamp: %s", ticket[:8], nonce, timestamp)
        logger.debug("Request body: %s", request_body)

        return request_body

    async def validate_ticket(self, ticket: str) -> TicketUserInfo:
        """
        验证 ticket 并获取用户信息

        Args:
            ticket: 企业票务系统颁发的 ticket

        Returns:
            TicketUserInfo: 用户信息对象

        Raises:
            ValueError: ticket 无效或过期
            httpx.RequestError: 网络请求失败
        """
        url = f"{self.ticket_server_url + self.ticket_server_validate_url}"
        logger.info("Ticket validation url : %s", url)
        # 构建带签名的请求体
        request_body = self._build_validate_request_body(ticket)

        headers = {
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                json=request_body,
                headers=headers
            )

            logger.info("Ticket validation response status: %s", response.status_code)
            logger.info("Response body: %s", response.text)

            if response.status_code != 200:
                logger.error("Ticket validation failed: %s - %s", response.status_code, response.text)
                raise ValueError(f"Invalid ticket: HTTP {response.status_code}")

            data = response.json()

            logger.debug("Ticket validation response: %s", data)

            # 检查响应中的成功标识（status: 0 表示成功）
            if data.get("status") != 0:
                status_value = data.get('status')
                error_msg = data.get("errmsg") or data.get("message", f"Validation failed with status {status_value}")
                if isinstance(error_msg, dict):
                    error_msg = f"Validation failed with status {status_value}"
                raise ValueError(error_msg)

            # 提取用户信息（message 字段包含用户数据）
            user_info_data = data.get("message", {})

            # 如果没有返回用户信息但验证成功，尝试从 ticket 解析
            if not user_info_data and data.get("status") == 0:
                # 至少返回 ticket 对应的用户 ID
                user_info_data = {
                    "userCode": ticket.split('_')[-1] if '_' in ticket else ticket,
                    "trueName": f"User_{ticket[:8]}",
                    "loginName": f"user_{ticket[:8]}@sso.local",
                    "adcd": "33",
                    "adName": "Default"
                }

            return TicketUserInfo.from_dict(user_info_data)

    def validate_ticket_sync(self, ticket: str) -> TicketUserInfo:
        """
        同步方式验证 ticket (用于 Flask 视图)

        Args:
            ticket: 企业票务系统颁发的 ticket

        Returns:
            TicketUserInfo: 用户信息对象
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.validate_ticket(ticket))

    def get_user_info(self, ticket: str) -> TicketUserInfo:
        """
        获取用户信息（包含验证）

        Args:
            ticket: 企业票务系统颁发的 ticket

        Returns:
            TicketUserInfo: 用户信息对象
        """
        return self.validate_ticket_sync(ticket)

    def logout(self, ticket: str) -> bool:
        """
        通知票务系统用户登出

        Args:
            ticket: 用户 ticket

        Returns:
            bool: 是否成功
        """
        url = f"{self.ticket_server_url}/api/v1/ticket/logout"

        # 构建带签名的请求体
        request_body = self._build_validate_request_body(ticket)

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    url,
                    json=request_body,
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("success") or result.get("valid", False):
                        logger.info("Ticket logout successful for ticket: %s...", ticket[:8])
                        return True
                    else:
                        logger.warning("Ticket logout failed: %s", result.get("message", "Unknown error"))
                        return False
                else:
                    logger.warning("Ticket logout failed: %s", response.status_code)
                    return False

        except Exception as e:
            logger.exception("Ticket logout error")
            return False


class TicketPassportService:
    """Ticket Passport 服务 - 用于生成和验证 Dify 内部的 JWT token"""

    @staticmethod
    def create_passport(user_info: TicketUserInfo) -> str:
        """
        为已验证的用户创建 passport token

        Args:
            user_info: 已验证的用户信息

        Returns:
            str: JWT token
        """
        exp_dt = datetime.now() + timedelta(
            minutes=dify_config.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        exp = int(exp_dt.timestamp())

        payload = {
            "iss": "enterprise_ticket_sso",
            "sub": "Ticket SSO Passport",
            "user_id": user_info.user_id,
            "email": user_info.email,
            "username": user_info.username,
            "display_name": user_info.display_name,
            "department": user_info.department,
            "roles": user_info.roles,
            "token_source": "ticket_sso",
            "auth_type": "external",
            "exp": exp,
            "iat": int(datetime.now().timestamp()),
        }

        token = PassportService().issue(payload)
        logger.info("Created ticket passport for user: %s", user_info.email)

        return token

    @staticmethod
    def verify_passport(token: str) -> dict[str, Any]:
        """
        验证 passport token

        Args:
            token: JWT token

        Returns:
            dict: 解码后的 payload

        Raises:
            Unauthorized: token 无效或过期
        """
        from werkzeug.exceptions import Unauthorized

        try:
            decoded = PassportService().verify(token)

            # 验证 token 来源
            if decoded.get("token_source") != "ticket_sso":
                raise Unauthorized("Invalid token source. Expected 'ticket_sso'.")

            return decoded

        except Exception as e:
            logger.exception("Passport verification failed")
            raise Unauthorized(f"Invalid passport: {str(e)}")
