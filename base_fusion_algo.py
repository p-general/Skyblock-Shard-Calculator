import json
import bazaar_api_integration
import pandas as pd
import itertools

RARITY_ORDER = ["Common", "Uncommon", "Rare", "Epic", "Legendary"]

with open("shard_data.json", "r") as f:
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

        # Rule 2: higher rarity wins
        elif RARITY_ORDER.index(left["rarity"]) > RARITY_ORDER.index(right["rarity"]):
            winner = left
        elif RARITY_ORDER.index(right["rarity"]) > RARITY_ORDER.index(left["rarity"]):
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



def build_fusion_map(shard_dict):
    """
    Precompute a reverse map: output_id -> list of (left_id, right_id) pairs
    that produce it via base fusion rules.
    """
    fusion_map = {}
    shard_ids = list(shard_dict.keys())

    for left_id, right_id in itertools.combinations(shard_ids, 2):
        outputs = fusion_output(left_id, right_id, shard_dict)
        for output_id in outputs:
            if output_id not in fusion_map:
                fusion_map[output_id] = []
            fusion_map[output_id].append((left_id, right_id))

    return fusion_map


def fusion_cost(left_shard: str, right_shard: str, directory: dict, bazaar: dict):
    cost = 0

    for shard_id in [left_shard, right_shard]:
        shard = directory[shard_id]
        shard_name = shard["name"]
        fusion_count = shard["fusion_count"]

        bazaar_key = bazaar_api_integration.shard_to_bazaar_key(shard_name)
        shard_status = bazaar.get(bazaar_key)
        
        if shard_status is None:
            return None

        quick = shard_status["quick_status"]
        if quick is None:
            return None
        elif quick["sellVolume"] < fusion_count:
            return None
        elif quick["buyOrders"] > quick["sellOrders"] * 5:
            return None
        elif quick["sellOrders"] == 0:
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
        status = bazaar_api_integration.get_quick_status(sName, bazaar_api_integration.bazaar_prods)
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
        if bOrders == 0:
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
    for left_id, right_id in itertools.combinations(shard_ids, 2):
        try:
            # profit_calculator returns a dict
            fusion_info = profit_calculator(left_id, right_id, shard_dict, bazaar_data)
            if fusion_info is None:
                continue

            fusion_info["left_shard"] = left_id
            fusion_info["right_shard"] = right_id

            results.append(fusion_info)
        except Exception:
            continue

    # Convert to DataFrame for easy sorting/filtering
    df = pd.DataFrame(results)
    
    # Sort by throughput_profit if available, otherwise by profit
    sort_col = "throughput_profit" if "throughput_profit" in df.columns else "profit"
    df = df.sort_values(by=sort_col, ascending=False)
    df = df.drop_duplicates(subset="output", keep="first").reset_index(drop=True)
    
    return df



# Show top 10 most profitable fusions

if __name__ == "__main__":
    results = scan_all_fusions(shard_dict, bazaar_api_integration.bazaar_prods, evaluate_fusion)
    print(results.head(10))