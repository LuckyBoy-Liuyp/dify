"""
企业 Ticket SSO 认证控制器

提供基于企业内部票务系统的单点登录接口
"""

import base64
import logging

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from flask import make_response, request
from flask_restx import Resource

from configs import dify_config
from controllers.console import console_ns
from controllers.console.wraps import setup_required
from extensions.ext_database import db
from libs.token import (
    set_access_token_to_cookie,
    set_csrf_token_to_cookie,
    set_refresh_token_to_cookie,
)
from models.account import Account, AccountStatus
from services.account_service import AccountService
from services.enterprise.ticket_sso_service import TicketSSOService, TicketUserInfo
from services.errors.account import AccountRegisterError

logger = logging.getLogger(__name__)


def aes_decrypt(cliper_text: str, secret_key: str) -> str:
    """AES 解密 (ECB 模式)"""
    if not secret_key:
        raise ValueError("secretKey can not be null !")

    # 转 16 进制字节
    key = secret_key.encode('utf-8')[:16]  # 取前 16 位
    cipher_text = base64.b64decode(cliper_text)

    # ECB 模式解密
    cipher = AES.new(key, AES.MODE_ECB)
    decrypted = unpad(cipher.decrypt(cipher_text), AES.block_size)

    return decrypted.decode('utf-8')


def aes_encrypt(plain_text: str, secret_key: str) -> str:
    """AES 加密 (ECB 模式)"""
    if not secret_key:
        raise ValueError("secretKey can not be null !")

    key = secret_key.encode('utf-8')[:16]
    cipher = AES.new(key, AES.MODE_ECB)
    encrypted = cipher.encrypt(pad(plain_text.encode('utf-8'), AES.block_size))
    return base64.b64encode(encrypted).decode('utf-8')


def _get_or_create_account(user_info: TicketUserInfo) -> Account:
    """
    根据 ticket 用户信息获取或创建本地账户

    Args:
        user_info: 已验证的用户信息

    Returns:
        Account: 账户对象

    Raises:
        AccountRegisterError: 账户创建失败
    """
    # 1. 尝试通过 mobile 查找现有账户
    encrypted_mobile = user_info.mobile
    # 创建加密器（使用 TICKET_SECRET_KEY）
    # 解密手机号
    try:
        mobile = aes_decrypt(cliper_text=encrypted_mobile, secret_key=dify_config.ENTERPRISE_TICKET_SECRET_KEY)
        mobile = base64.b64encode(mobile.encode('utf-8')).decode('utf-8')
    except Exception:
        # 解密失败处理
        mobile = encrypted_mobile
    account = db.session.query(Account).filter_by(mobile=mobile).first()

    if account:
        # 检查账户状态
        if account.status == AccountStatus.BANNED:
            raise ValueError("Account is banned")

        logger.info("Found existing account: %s", account.mobile)
        return account

    return account


@console_ns.route("/sso/ticket/login")
class TicketSSOLogin(Resource):
    """Ticket SSO 登录入口"""

    @setup_required
    def post(self):
        """
        接收企业 Ticket 系统的回调并登录

        Request Body (JSON):
            - ticket: 企业票务系统颁发的 ticket
            - state: 原始跳转地址（可选）
        """
        # 直接从 JSON body 获取参数
        data = request.get_json() or {}
        ticket = data.get("ticket")
        state = data.get("state")
        redirect_uri = state or dify_config.CONSOLE_WEB_URL

        try:
            # 1. 验证 ticket 并获取用户信息
            logger.info("Validating ticket: %s...", ticket[:8])
            sso_service = TicketSSOService()
            user_info = sso_service.get_user_info(ticket)

            logger.info("Ticket validated for user: %s", user_info.mobile)

            # 2. 获取或创建本地账户
            account = _get_or_create_account(user_info)

            # 3. 登录账户
            token_pair = AccountService.login(
                account=account,
                ip_address=request.remote_addr
            )

            # 4. 设置 cookie
            response = make_response({"result": "success"})
            # response = make_response(redirect(redirect_uri))

            set_access_token_to_cookie(request, response, token_pair.access_token)
            set_refresh_token_to_cookie(request, response, token_pair.refresh_token)
            set_csrf_token_to_cookie(request, response, token_pair.csrf_token)

            logger.info("Ticket SSO login successful: %s", account.name)
            return response

        except ValueError as e:
            logger.exception("Ticket validation failed")
            return {"result": "error", "message": "Invalid ticket"}, 401

        except AccountRegisterError as e:
            logger.exception("Account registration failed")
            return {"result": "error", "message": str(e.description)}, 400

        except Exception as e:
            logger.exception(str(e.description))
            return {"result": "error", "message": "Login failed"}, 500
