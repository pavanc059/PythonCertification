import json
from webull.core.client import ApiClient
from webull.trade.trade_client import TradeClient

api_client = ApiClient("03d6ca7a1cb6d56724b3d60590a8c6ba", "9669f68b866fdfd60945e8668b2d9743", "us")
api_client.add_endpoint("us", "api.webull.com")

trade_client = TradeClient(api_client)
res = trade_client.account_v2.get_account_list()
if res.status_code == 200:
    print("Success!", json.dumps(res.json(), indent=2))
else:
    print("Error:", res.status_code, res.text)