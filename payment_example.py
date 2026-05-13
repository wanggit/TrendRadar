"""
支付服务 - 对接 Z-Pay 支付接口
文档参考：https://z-pay.cn/doc.html#d3
"""
import hashlib
import json
import requests
from typing import Optional
from flask import current_app


class PaymentService:
    """Z-Pay 支付服务（易支付）"""

    def __init__(self, uid: str, key: str, api_url: str = "https://zpayz.cn"):
        self.uid = uid  # 商户 ID (pid)
        self.key = key  # 商户密钥
        self.api_url = api_url.rstrip('/')

    def generate_sign(self, params: dict) -> str:
        """
        生成签名（按文档 #d8 MD5 签名算法）

        签名算法：
        1. 将所有参数按参数名 ASCII 码从小到大排序（a-z）
        2. sign、sign_type、空值不参与签名
        3. 拼接成 URL 键值对格式：a=b&c=d&e=f
        4. 在最后直接加上密钥（不是&key={密钥}，而是直接拼接密钥字符串）
        5. 对整个字符串进行 MD5 加密（小写）

        公式：sign = md5( a=b&c=d&e=f + KEY )
        """
        # 过滤掉 sign、sign_type 和空值
        filtered = {k: v for k, v in params.items()
                   if k not in ['sign', 'sign_type'] and v is not None and v != ''}

        # 按参数名 ASCII 码排序
        sorted_params = sorted(filtered.items(), key=lambda x: x[0])

        # 拼接成 key=value 格式
        sign_str = '&'.join([f"{k}={v}" for k, v in sorted_params])

        # 直接加上密钥字符串（文档 #d8: sign = md5( a=b&c=d&e=f + KEY )）
        sign_str += self.key

        # MD5 加密（小写）
        return hashlib.md5(sign_str.encode('utf-8')).hexdigest()

    def create_order(self, order_no: str, amount: float, subject: str,
                     notify_url: str, return_url: Optional[str] = None,
                     clientip: str = "127.0.0.1") -> dict:
        """
        创建支付订单（API 接口支付模式）

        文档：https://z-pay.cn/doc.html#d3

        参数:
            order_no: 商户订单号
            amount: 订单金额（元）
            subject: 商品名称
            notify_url: 服务器异步通知地址
            return_url: 页面跳转通知地址
            clientip: 用户 IP 地址

        返回:
            {
                'code': 0,  # 0 表示成功
                'msg': 'success',
                'data': {
                    'pay_url': 'https://zpayz.cn/pay/... 二维码链接',
                    'trade_no': 'ZPAY 订单号'
                }
            }
        """
        # API 接口地址
        endpoint = f"{self.api_url}/mapi.php"

        # 构建请求参数（按文档要求）
        params = {
            'pid': self.uid,
            'type': 'alipay',  # 支付宝：alipay 微信支付：wxpay
            'out_trade_no': order_no,
            'notify_url': notify_url,
            'name': subject,
            'money': str(amount),
            'clientip': clientip,
            'return_url': return_url or notify_url,
        }

        # 生成签名
        sign = self.generate_sign(params)
        params['sign'] = sign
        params['sign_type'] = 'MD5'

        # POST 请求（form-data）
        try:
            current_app.logger.info(f"请求 Z-Pay API: {endpoint}")
            current_app.logger.info(f"请求参数：{params}")

            response = requests.post(endpoint, data=params, timeout=30)
            result = response.json()

            current_app.logger.info(f"Z-Pay 返回：{result}")

            # Z-Pay 返回：code=1 表示成功，code="error"或其它值表示失败
            if result.get('code') == 1:
                # 成功返回
                pay_url = result.get('payurl', '') or result.get('qrcode', '')
                if not pay_url:
                    current_app.logger.error(f"Z-Pay 返回成功但未提供支付 URL: {result}")
                    return {
                        'code': 500,
                        'msg': 'Z-Pay 返回成功但缺少支付 URL'
                    }
                return {
                    'code': 0,
                    'msg': 'success',
                    'data': {
                        'pay_url': pay_url,
                        'trade_no': result.get('trade_no', order_no),
                        'O_id': result.get('O_id', ''),
                        'img': result.get('img', '')  # 二维码图片地址（如果有）
                    }
                }
            else:
                current_app.logger.error(f"Z-Pay 返回失败：{result}")
                return {
                    'code': result.get('code', 500),
                    'msg': result.get('msg', '支付接口调用失败')
                }

        except Exception as e:
            current_app.logger.error(f"请求 Z-Pay API 异常：{e}")
            return {
                'code': 500,
                'msg': f'请求异常：{str(e)}'
            }

    def verify_callback(self, data: dict) -> bool:
        """
        验证支付回调签名（文档 #d7）

        回调参数：
            pid: 商户 ID
            trade_no: 易支付订单号
            out_trade_no: 商户订单号
            type: 支付方式 (alipay/wxpay)
            name: 商品名称
            money: 订单金额
            param: 业务扩展参数
            trade_status: 支付状态 (TRADE_SUCCESS=成功)
            sign: 签名
            sign_type: 签名类型

        签名算法（文档 #d8）：
        1. 所有参数按 ASCII 码从小到大排序（a-z）
        2. sign、sign_type、空值不参与签名
        3. 拼接成 key=value 格式
        4. 直接加上密钥字符串（不是&key={密钥}，而是直接拼接）
        5. MD5 加密（小写）

        公式：sign = md5( a=b&c=d&e=f + KEY )
        """
        received_sign = data.get('sign', '')

        current_app.logger.info(f"回调原始数据：{data}")
        current_app.logger.info(f"收到的签名：{received_sign}")

        # 过滤掉 sign、sign_type 和空值
        verify_params = {k: v for k, v in data.items()
                        if k not in ['sign', 'sign_type'] and v is not None and v != ''}

        # 按参数名 ASCII 码排序
        sorted_params = sorted(verify_params.items(), key=lambda x: x[0])

        current_app.logger.info(f"排序后的参数：{sorted_params}")

        # 拼接成 key=value 格式
        sign_str = '&'.join([f"{k}={v}" for k, v in sorted_params])

        current_app.logger.info(f"拼接后的字符串：{sign_str}")

        # 直接加上密钥字符串（文档 #d8: sign = md5( a=b&c=d&e=f + KEY )）
        sign_str_with_key = sign_str + self.key

        current_app.logger.info(f"带密钥的字符串：{sign_str_with_key}")

        # MD5 加密（小写）
        expected_sign = hashlib.md5(sign_str_with_key.encode('utf-8')).hexdigest()

        current_app.logger.info(f"计算得到的签名：{expected_sign}")
        current_app.logger.info(f"签名是否匹配：{received_sign == expected_sign}")

        return received_sign == expected_sign

    def query_order(self, order_no: str) -> dict:
        """
        查询订单状态（文档 #d5）

        请求 URL：https://zpayz.cn/api.php?act=order&pid={商户 ID}&key={商户密钥}&out_trade_no={商户订单号}

        参数:
            order_no: 商户订单号

        返回:
            {
                'code': 1,  # 1 为成功，其它为失败
                'msg': '查询订单号成功！',
                'trade_no': '易支付订单号',
                'out_trade_no': '商户订单号',
                'status': 1/0,  # 1 为支付成功，0 为未支付
                ...
            }

        注意：查询接口不需要签名，直接传递 pid 和 key
        """
        endpoint = f"{self.api_url}/api.php"

        # 查询接口参数（文档 #d5）
        params = {
            'act': 'order',  # 查询订单
            'pid': self.uid,
            'key': self.key,
            'out_trade_no': order_no
        }

        query_string = f"act=order&pid={self.uid}&key={self.key}&out_trade_no={order_no}"
        url = f"{endpoint}?{query_string}"

        try:
            response = requests.get(url, timeout=30)
            return response.json()
        except Exception as e:
            return {
                'code': 0,  # 0 为失败
                'msg': f'请求异常：{str(e)}'
            }
