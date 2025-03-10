from futu import *

quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)  # 创建行情对象
ret_sub, err_message = quote_ctx.subscribe(['HK.00700'], [SubType.RT_DATA], subscribe_push=False)
# 先订阅分时数据类型。订阅成功后 OpenD 将持续收到服务器的推送，False 代表暂时不需要推送给脚本
if ret_sub == RET_OK:   # 订阅成功
    ret, data = quote_ctx.get_rt_data('HK.00700')   # 获取一次分时数据
    if ret == RET_OK:
        print(data)
        price_arr = data['cur_price']
        if (len(price_arr) > 0):
            print(price_arr[len(price_arr)-1])
        else:
            print(price_arr)
    else:
        print('error:', data)
else:
    print('subscription failed', err_message)
quote_ctx.close() # 关闭对象，防止连接条数用尽
