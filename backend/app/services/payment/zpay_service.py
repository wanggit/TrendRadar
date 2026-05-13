import hashlib
import logging
from typing import Optional

import requests

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class ZPayService:
    def __init__(self, uid: str | None = None, key: str | None = None, api_url: str | None = None):
        settings = get_settings()
        self.uid = uid or settings.ZPAY_UID
        self.key = key or settings.ZPAY_KEY
        self.api_url = (api_url or settings.ZPAY_API_URL).rstrip("/")

    def generate_sign(self, params: dict) -> str:
        filtered = {k: v for k, v in params.items()
                    if k not in ["sign", "sign_type"] and v is not None and v != ""}
        sorted_params = sorted(filtered.items(), key=lambda x: x[0])
        sign_str = "&".join([f"{k}={v}" for k, v in sorted_params])
        sign_str += self.key
        return hashlib.md5(sign_str.encode("utf-8")).hexdigest()

    def create_order(
        self,
        order_no: str,
        amount: float,
        subject: str,
        notify_url: str,
        return_url: Optional[str] = None,
        payment_type: str = "alipay",
        clientip: str = "127.0.0.1",
    ) -> dict:
        endpoint = f"{self.api_url}/mapi.php"

        params = {
            "pid": self.uid,
            "type": payment_type,
            "out_trade_no": order_no,
            "notify_url": notify_url,
            "name": subject,
            "money": str(amount),
            "clientip": clientip,
            "return_url": return_url or notify_url,
        }

        sign = self.generate_sign(params)
        params["sign"] = sign
        params["sign_type"] = "MD5"

        try:
            logger.info(f"请求 Z-Pay API: {endpoint}, order_no={order_no}")
            response = requests.post(endpoint, data=params, timeout=30)
            result = response.json()
            logger.info(f"Z-Pay 返回: {result}")

            if result.get("code") == 1:
                pay_url = result.get("payurl", "") or result.get("qrcode", "")
                if not pay_url:
                    logger.error(f"Z-Pay 返回成功但缺少支付 URL: {result}")
                    return {"code": 500, "msg": "Z-Pay 返回成功但缺少支付 URL"}
                return {
                    "code": 0,
                    "msg": "success",
                    "data": {
                        "pay_url": pay_url,
                        "trade_no": result.get("trade_no", order_no),
                        "O_id": result.get("O_id", ""),
                        "img": result.get("img", ""),
                    },
                }
            else:
                logger.error(f"Z-Pay 返回失败: {result}")
                return {"code": result.get("code", 500), "msg": result.get("msg", "支付接口调用失败")}
        except Exception as e:
            logger.error(f"请求 Z-Pay API 异常: {e}")
            return {"code": 500, "msg": f"请求异常: {str(e)}"}

    def verify_callback(self, data: dict) -> bool:
        received_sign = data.get("sign", "")
        verify_params = {k: v for k, v in data.items()
                         if k not in ["sign", "sign_type"] and v is not None and v != ""}
        sorted_params = sorted(verify_params.items(), key=lambda x: x[0])
        sign_str = "&".join([f"{k}={v}" for k, v in sorted_params])
        sign_str_with_key = sign_str + self.key
        expected_sign = hashlib.md5(sign_str_with_key.encode("utf-8")).hexdigest()
        return received_sign == expected_sign

    def query_order(self, order_no: str) -> dict:
        endpoint = f"{self.api_url}/api.php"
        query_string = f"act=order&pid={self.uid}&key={self.key}&out_trade_no={order_no}"
        url = f"{endpoint}?{query_string}"

        try:
            response = requests.get(url, timeout=30)
            return response.json()
        except Exception as e:
            return {"code": 0, "msg": f"请求异常: {str(e)}"}
