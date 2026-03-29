import requests

"""
Pulling the bazaar data using Hypixel's public API for Hypixel Skyblock
"""

url = "https://api.hypixel.net/v2/skyblock/bazaar"

response = requests.get(url)
response.raise_for_status()

bazaar_prods = response.json()["products"]


def shard_to_bazaar_key(shard_name: str):
    return "SHARD_" + shard_name.upper().replace(" ", "_")


def get_quick_status(shard_name: str, bazaar_products: dict):
    key = shard_to_bazaar_key(shard_name)
    product = bazaar_products.get(key)

    if not product:
        return None

    return product["quick_status"]
