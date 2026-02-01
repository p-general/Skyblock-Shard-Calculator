import requests
import json

url = "https://api.hypixel.net/v2/skyblock/bazaar"

response = requests.get(url)
response.raise_for_status

bazaar_prods = response.json()["products"]

bazaar_lookup = {
    k.replace("SHARD_", ""): v["quick_status"]
    for k, v in bazaar_prods.items()
}


def get_quick_status(shard_name: str, bazaar_products: dict):
    key = shard_to_bazaar_key(shard_name)
    product = bazaar_products.get(key)

    if not product:
        return None
    
    return product["quick_status"]

def shard_to_bazaar_key(shard_name: str):
    return "SHARD_" + shard_name.upper().replace(" ", "_")


with open ("shard_data_fixedd.json", "r") as f:
    shard_dict = json.load(f)


def get_shard_sell_price(shard_name: str, bazaar_data: dict):
    """
    Returns the current sell price of a shard from bazaar data.
    shard_name: the in-game name of the shard
    bazaar_data: the dictionary returned from the Hypixel Bazaar API
    """
    # Convert the shard name to the bazaar key
    bazaar_key = shard_to_bazaar_key(shard_name)
    product = bazaar_data.get(bazaar_key)

    if not product or not product.get("quick_status"):
        raise ValueError(f"No bazaar data available for {shard_name}")

    return product["quick_status"]["sellPrice"]  # weighted average of top 2% sell orders







    



