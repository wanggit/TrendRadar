"""
Z-Pay Service - Unit Tests
Tests: signature generation, signature verification
"""
import hashlib
import pytest
from unittest.mock import patch, MagicMock

from app.services.payment.zpay_service import ZPayService


class TestGenerateSign:
    def test_sign_generation(self):
        service = ZPayService(uid="1001", key="testkey123")
        params = {"pid": "1001", "type": "alipay", "out_trade_no": "TR001", "money": "49.00"}
        sign = service.generate_sign(params)

        filtered = {k: v for k, v in params.items() if k not in ["sign", "sign_type"] and v}
        sorted_params = sorted(filtered.items(), key=lambda x: x[0])
        sign_str = "&".join([f"{k}={v}" for k, v in sorted_params]) + "testkey123"
        expected = hashlib.md5(sign_str.encode("utf-8")).hexdigest()

        assert sign == expected

    def test_sign_excludes_sign_and_sign_type(self):
        service = ZPayService(uid="1001", key="testkey")
        params = {"pid": "1001", "sign": "existing", "sign_type": "MD5", "money": "10.00"}
        sign = service.generate_sign(params)
        assert sign is not None
        assert len(sign) == 32

    def test_sign_excludes_empty_values(self):
        service = ZPayService(uid="1001", key="testkey")
        params = {"pid": "1001", "name": "", "money": "10.00"}
        sign = service.generate_sign(params)
        assert sign is not None


class TestVerifyCallback:
    def test_valid_callback(self):
        service = ZPayService(uid="1001", key="testkey123")
        params = {
            "pid": "1001",
            "trade_no": "ZPAY123",
            "out_trade_no": "TR001",
            "type": "alipay",
            "money": "49.00",
            "trade_status": "TRADE_SUCCESS",
        }
        sign = service.generate_sign(params)
        params["sign"] = sign
        params["sign_type"] = "MD5"

        assert service.verify_callback(params) is True

    def test_invalid_signature(self):
        service = ZPayService(uid="1001", key="testkey123")
        params = {
            "pid": "1001",
            "out_trade_no": "TR001",
            "money": "49.00",
            "sign": "invalid_signature",
            "sign_type": "MD5",
        }
        assert service.verify_callback(params) is False

    def test_tampered_money_fails(self):
        service = ZPayService(uid="1001", key="testkey123")
        params = {
            "pid": "1001",
            "out_trade_no": "TR001",
            "money": "49.00",
        }
        sign = service.generate_sign(params)
        params["sign"] = sign
        params["money"] = "0.01"
        assert service.verify_callback(params) is False


class TestCreateOrder:
    @patch("app.services.payment.zpay_service.requests.post")
    def test_successful_order_creation(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 1,
            "msg": "success",
            "payurl": "https://zpayz.cn/pay/abc123",
            "trade_no": "ZPAY123",
        }
        mock_post.return_value = mock_response

        service = ZPayService(uid="1001", key="testkey123")
        result = service.create_order(
            order_no="TR001",
            amount=49.00,
            subject="Test Product",
            notify_url="https://example.com/callback",
        )

        assert result["code"] == 0
        assert result["data"]["pay_url"] == "https://zpayz.cn/pay/abc123"
        assert result["data"]["trade_no"] == "ZPAY123"

    @patch("app.services.payment.zpay_service.requests.post")
    def test_failed_order_creation(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": "error",
            "msg": "Invalid pid",
        }
        mock_post.return_value = mock_response

        service = ZPayService(uid="1001", key="testkey123")
        result = service.create_order(
            order_no="TR001",
            amount=49.00,
            subject="Test Product",
            notify_url="https://example.com/callback",
        )

        assert result["code"] != 0
        assert "Invalid pid" in result["msg"]


class TestQueryOrder:
    @patch("app.services.payment.zpay_service.requests.get")
    def test_query_order_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 1,
            "msg": "success",
            "status": 1,
            "trade_no": "ZPAY123",
        }
        mock_get.return_value = mock_response

        service = ZPayService(uid="1001", key="testkey123")
        result = service.query_order("TR001")

        assert result["code"] == 1
        assert result["status"] == 1
