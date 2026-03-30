import json
import base_fusion_algo
import bazaar_api_integration

"""
Heavily in progress algo for processing the multitude
of special shard fusions that don't follow the traditional
shard algorithm.
"""

# Constants
MAX_OUTPUTS = 3

with open ("special_fusions.json", "r") as f:
    fusion_dict = json.load(f)


def rarity_rank(rarity: str) -> int:
    try:
        return base_fusion_algo.RARITY_ORDER.index(rarity)
    except ValueError:
        return -1  # unknown rarity


def rule_matches_family(rule, left, right):
    family = rule["family"]
    return (
        family in left["families"] or family in right["families"]
    )

def rule_matches_pair(rule, a, b):
    shards = (a, b)

    if rule["type"] == "family":
        return rule_matches_family(rule, a, b)

    if rule["type"] == "rarity_plus":
        return any(
            rarity_rank(s["rarity"]) >= rarity_rank(rule["rarity"])
            for s in shards
        )

    if rule["type"] == "rarity_category":
        return any(
            s["rarity"] == rule["rarity"] and
            s["category"] == rule["category"]
            for s in shards
        )

    if rule["type"] == "rarity_plus_category":
        return any(
            rarity_rank(s["rarity"]) >= rarity_rank(rule["rarity"]) and
            s["category"] == rule["category"]
            for s in shards
        )
    
    if rule["type"] == "rarity_plus_family":
        return any(
            rarity_rank(s["rarity"]) >= rarity_rank(rule["rarity"]) and
            rule["family"] in s["families"]
            for s in shards
        )

    if rule["type"] == "specific_shard":
        return any(s["name"] == rule["shard"] for s in shards)

    if rule["type"] == "any_shard":
        return True

    if rule["type"] == "category_exclusive":
        return all(s["category"] == rule["category"] for s in shards)

    return False



def resolve_fusion(left_id, right_id, shard_dict, special_rules):
    """
    Resolve a fusion between left_id and right_id shards.
    Returns a list of shard IDs representing the fusion outputs.
    """
    left = shard_dict[left_id]
    right = shard_dict[right_id]

    # Base outputs
    outputs = base_fusion_algo.fusion_output(left_id, right_id, shard_dict)
    outputs = [o for o in outputs if o != left_id and o != right_id]  # prevent self-output

    # Special outputs
    special_outputs = []

    for special_shard_id, rules in special_rules.items():
        special_shard = shard_dict.get(special_shard_id, {})
        # Skip if the special shard is same as left or right
        if special_shard_id in [left_id, right_id]:
            continue

        if all(rule_matches_pair(r, left, right) for r in rules):
            if special_shard_id not in special_outputs:
                special_outputs.append(special_shard_id)

    # Sort special outputs: rarity descending, then numeric ID ascending
    def sort_key(shard_id):
        shard = shard_dict.get(shard_id, {})
        rank = -rarity_rank(shard.get("rarity", "Common"))
        digits = ''.join(filter(str.isdigit, shard_id))
        num = int(digits) if digits else 0
        return (rank, num)

    special_outputs.sort(key=sort_key)

    # Merge outputs while respecting MAX_OUTPUTS
    for s in special_outputs:
        if s not in outputs and len(outputs) < MAX_OUTPUTS:
            outputs.append(s)

    return outputs[:MAX_OUTPUTS]






def evaluate_fusion(left_id, right_id, directory, bazaar):
    outputs = resolve_fusion(left_id, right_id, directory, fusion_dict)
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

        effective_sell = status["sellPrice"] * 0.97
        cost = base_fusion_algo.fusion_cost(left_id, right_id, directory, bazaar)
        if cost is None:
            continue

        profit = effective_sell - cost
        margin = (profit / cost * 100) if cost > 0 else 0

        # Volume-weighted: how many times can this fusion realistically be executed
        left_quick = bazaar.get(base_fusion_algo.bazaar_api_integration.shard_to_bazaar_key(directory[left_id]["name"]), {}).get("quick_status", {})
        right_quick = bazaar.get(base_fusion_algo.bazaar_api_integration.shard_to_bazaar_key(directory[right_id]["name"]), {}).get("quick_status", {})
        left_executions = left_quick.get("sellVolume", 0) // directory[left_id]["fusion_count"]
        right_executions = right_quick.get("sellVolume", 0) // directory[right_id]["fusion_count"]
        max_executions = min(left_executions, right_executions)
        throughput_profit = profit * max_executions

        if not best_result or profit > best_result["profit"]:
            best_result = {
                "left": left_id,
                "right": right_id,
                "output": output_id,
                "cost": cost,
                "value": effective_sell,
                "profit": profit,
                "margin": margin,
                "max_executions": max_executions,
                "throughput_profit": throughput_profit
            }

    return best_result


if __name__ == "__main__":
    results = base_fusion_algo.scan_all_fusions(base_fusion_algo.shard_dict, bazaar_api_integration.bazaar_prods, evaluate_fusion)
    print(results.head(10))