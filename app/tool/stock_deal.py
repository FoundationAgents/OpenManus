import asyncio
from typing import List
from futu import *

from app.logger import logger  # Assuming a logger is set up in your app
from app.tool.base import BaseTool


class StockDeal(BaseTool):
    name: str = "stock_deal"
    description: str = """Perform a stock deal manager that can buy or sell the stocks.
Use this tool when you want to buy or sell a detail stock.
The tool always returns the realtime price of the stock.
"""
    parameters: dict = {
        "type": "object",
        "properties": {
            "stock": {
                "type": "string",
                "description": "(required) The HK stock number,eg HK stock tecent number is:HK.00700",
            },
            "action": {
                "type": "string",
                "enum": [
                    "buy",
                    "sell",
                    "get"
                ],
                "description": "The stock information get/sell/buy",
            },
            "price": {
                "type": "float",
                "description": "(optional) the price to buy or sell, if the action=get, then price can be optional",
                "default": 0.0,
            },
        },
        "required": ["stock", "action", "price"],
    }

    async def execute(self, stock: str, action: str, price: float = 0) -> List[str]:
        """
        Execute a futu api to get the stock price.

        Args:
            stock (str): The search query to submit to Google.
            action (str): enum of buy/sell/get
            price (float, optional): The price of stock.

        Returns:
            List[str]: price of stock
        """
        # Run the search in a thread pool to prevent blocking
        logger.info(f"tips futu stock input deal:{stock}, action:{action}, price:{price}")

        if action == 'get':
            quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)  # 创建行情对象
            ret_sub, err_message = quote_ctx.subscribe([stock], [SubType.RT_DATA], subscribe_push=False)
            # 先订阅分时数据类型。订阅成功后 OpenD 将持续收到服务器的推送，False 代表暂时不需要推送给脚本
            price = 0.0
            if ret_sub == RET_OK:   # 订阅成功
                ret, data = quote_ctx.get_rt_data(stock)   # 获取一次分时数据
                if ret == RET_OK:
                    print(data)
                    price_arr = data['cur_price']
                    if (len(price_arr) > 0):
                        price = price_arr[len(price_arr)-1]
                    else:
                        logger.error(f"futu api error, ret:{ret}, msg:{price_arr}")
                else:
                    logger.error(f"futu api error, ret:{ret}, msg:{data}")
            else:
                logger.error(f"futu api error, ret:{ret_sub}, msg:{err_message}")
            quote_ctx.close() # 关闭对象，防止连接条数用尽
            logger.info(f"tips futu stock result:{stock}, ret:{ret}, price:{price}")
        
        if action == 'buy':
            trd_ctx = OpenSecTradeContext(host='127.0.0.1', port=11111)  # 创建交易对象
            ret, data = trd_ctx.place_order(price=price, qty=100, code=stock, trd_side=TrdSide.BUY, trd_env=TrdEnv.SIMULATE)  # 模拟交易，下单（如果是真实环境交易，在此之前需要先解锁交易密码）
            logger.info(f"action:{action}, order id:{data['order_id']}, order_status:{data['order_status']}")
            trd_ctx.close()  # 关闭对象，防止连接条数用尽
        
        if action == 'sell':
            trd_ctx = OpenSecTradeContext(host='127.0.0.1', port=11111)  # 创建交易对象
            ret, data = trd_ctx.place_order(price=price, qty=100, code=stock, trd_side=TrdSide.SELL, trd_env=TrdEnv.SIMULATE)  # 模拟交易，下单（如果是真实环境交易，在此之前需要先解锁交易密码）
            logger.info(f"action:{action}, order id:{data['order_id']}, order_status:{data['order_status']}")
            trd_ctx.close()  # 关闭对象，防止连接条数用尽
        return price
