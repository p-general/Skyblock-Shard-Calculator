import json
import bazaar_stuff
import requests
import pandas as pd
import itertools

url = "https://api.hypixel.net/v2/skyblock/bazaar"

response = requests.get(url)
response.raise_for_status

bazaar_prods = response.json()["products"]

bazaar_lookup = {
    k.replace("SHARD_", ""): v["quick_status"]
    for k, v in bazaar_prods.items()
}


with open("shard_data_fixedd.json", "r") as f:
    shard_dict = json.load(f)


def fusion_output(left_id, right_id, shard_dict):
    left = shard_dict[left_id]
    right = shard_dict[right_id]
    
    outputs = []

    # Helper to get valid next base fusion
    def valid_next(shard):
        next_fusions = shard.get("next_base_fusions", [])
        if next_fusions and next_fusions != ["---"]:
            return next_fusions[0]
        return None

    if left["category"] == right["category"]:
        # Rule 1: direct override
        if right_id in left["next_base_fusions"]:
            winner = right
        elif left_id in right["next_base_fusions"]:
            winner = left

        # Rule 2: priority
        elif left["priority"] > right["priority"]:
            winner = left
        elif right["priority"] > left["priority"]:
            winner = right

        # Rule 3: right bias
        else:
            winner = right

        next_shard = valid_next(winner)
        if next_shard:
            outputs.append(next_shard)

    else:
        # Different category → both contribute
        for shard in (left, right):
            next_shard = valid_next(shard)
            if next_shard:
                outputs.append(next_shard)


    # Remove duplicates and limit to 3 outputs
    return list({o for o in outputs})[:3]



def fusion_cost(left_shard: str, right_shard: str, directory: dict, bazaar: dict):
    cost = 0

    for shard_id in [left_shard, right_shard]:
        shard = directory[shard_id]
        shard_name = shard["name"]
        fusion_count = shard["fusion_count"]

        bazaar_key = bazaar_stuff.shard_to_bazaar_key(shard_name)
        shard_status = bazaar.get(bazaar_key)
        
        if shard_status is None:
            raise ValueError(f"No bazaar data found for {shard_name}")
        
        quick = shard_status["quick_status"]
        if quick is None:
            raise ValueError(f"No quick status found for {shard_name}")
        elif quick["buyVolume"] < fusion_count:
            return None
        elif quick["sellVolume"] < 1:
            return None
        
        buy_price = quick["buyPrice"]
        cost += (buy_price * fusion_count) * 0.9875

    return cost


# THE REAL TEST METHOD
def evaluate_fusion(left_id, right_id, directory, bazaar):
    outputs = fusion_output(left_id, right_id, directory)
    if not outputs:
        return None

    best_result = None

    for output_id in outputs:
        shard = directory[output_id]
        sName = shard["name"]
        status = bazaar_stuff.get_quick_status(sName, bazaar_prods)
        if not status:
            continue

        sVolume = status["sellVolume"]
        bVolume = status["buyVolume"]
        sOrders = status["sellOrders"]
        bOrders = status["buyOrders"]

        # liquidity checks
        if bVolume > sVolume * 1.5:
            continue
        if bOrders > sOrders * 5:
            continue

        # effective sell price
        effective_sell = status["sellPrice"] * 0.97
        cost = fusion_cost(left_id, right_id, directory, bazaar)
        profit = effective_sell - cost
        margin = (profit / cost * 100) if cost > 0 else 0

        # pick the output with the highest profit
        if not best_result or profit > best_result["profit"]:
            best_result = {
                "left": left_id,
                "right": right_id,
                "output": output_id,
                "cost": cost,
                "value": effective_sell,
                "profit": profit,
                "margin": margin
            }

    return best_result


def scan_all_fusions(shard_dict, bazaar_data, profit_calculator):
    """
    Scan all possible shard pairs and calculate fusion profits.

    Parameters:
        shard_dict (dict): Your JSON shard data keyed by shard ID
        bazaar_data (dict): Bazaar quick_status keyed by shard name
        profit_calculator (func): Function: (left_id, right_id, shard_dict, bazaar_data) -> profit info

    Returns:
        pd.DataFrame: DataFrame with all profitable fusions, sorted by profit
    """
    results = []

    shard_ids = list(shard_dict.keys())

    # All combinations with replacement (includes same shard twice)
    for left_id, right_id in itertools.combinations_with_replacement(shard_ids, 2):
        try:
            # profit_calculator returns a dict
            fusion_info = profit_calculator(left_id, right_id, shard_dict, bazaar_data)
            
            # Add shard IDs for reference
            fusion_info["left_shard"] = left_id
            fusion_info["right_shard"] = right_id
            
            results.append(fusion_info)
        except Exception as e:
            # Skip invalid fusions (e.g., None output, missing bazaar data)
            continue

    # Convert to DataFrame for easy sorting/filtering
    df = pd.DataFrame(results)
    
    # Sort by profit descending
    df = df.sort_values(by="profit", ascending=False).reset_index(drop=True)
    
    return df



# Show top 10 most profitable fusions

if __name__ == "__main__":
    current_data = scan_all_fusions(shard_dict, bazaar_prods, evaluate_fusion)
    print(current_data.head(10))    