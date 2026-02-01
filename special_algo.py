import json
import algo

"""
Heavily in progress algo for processing the multitude
of special shard fusions that don't follow the traditional
shard algorithm. 
"""

with open ("shard_data_fixedd.json", "r") as f:
    shard_dict = json.load(f)

with open ("special_fusions_pretty.json", "r") as f:
    fusion_dict = json.load(f)

RARITY_ORDER = ["Common", "Uncommon", "Rare", "Epic", "Legendary"]

def rarity_rank(rarity: str) -> int:
    try:
        return RARITY_ORDER.index(rarity)
    except ValueError:
        return -1  # unknown rarity


def rule_matches_family(rule, left, right):
    family = rule["family"]
    return (
        family in left["families"]
        or family in right["families"]
    )

def rule_matches_pair(rule, a, b):
    shards = (a, b)

    if rule["type"] == "family":
        return any(rule["family"] in s["families"] for s in shards)

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

    if rule["type"] == "specific_shard":
        return any(s["name"] == rule["shard"] for s in shards)

    if rule["type"] == "any_shard":
        return True

    if rule["type"] == "category_exclusive":
        return all(s["category"] == rule["category"] for s in shards)

    return False


def check_special_fusions(left_id, right_id, shard_dict, special_rules):
    left = shard_dict[left_id]
    right = shard_dict[right_id]

    outputs = []

    for output_id, rules in special_rules.items():
        # Prevent shard producing itself
        if output_id in (left_id, right_id):
            continue

        valid = True
        for rule in rules:
            if not rule_matches_pair(rule, left, right):
                valid = False
                break

        if valid:
            outputs.append(output_id)

    return outputs

# Constants
MAX_OUTPUTS = 3
RARITY_ORDER = ["Common", "Uncommon", "Rare", "Epic", "Legendary"]

def rule_matches(rule, left, right):
    """Return True if this rule is satisfied by left+right shards."""
    rtype = rule["type"]

    if rtype == "specific_shard":
        # always trigger if the rule is for a specific shard
        return True

    elif rtype == "family":
        # Trigger if either shard belongs to the family
        return rule["family"] in left.get("families", []) or rule["family"] in right.get("families", [])

    elif rtype == "rarity_plus":
        # Trigger if either shard has rarity >= required
        return RARITY_ORDER.index(left["rarity"]) >= RARITY_ORDER.index(rule["rarity"]) or \
               RARITY_ORDER.index(right["rarity"]) >= RARITY_ORDER.index(rule["rarity"])

    elif rtype == "rarity_category":
        # Trigger if either shard matches exact rarity+category
        return (left["rarity"] == rule["rarity"] and left["category"] == rule["category"]) or \
               (right["rarity"] == rule["rarity"] and right["category"] == rule["category"])

    elif rtype == "rarity_plus_category":
        # Trigger if either shard has rarity >= required AND category matches
        return (RARITY_ORDER.index(left["rarity"]) >= RARITY_ORDER.index(rule["rarity"]) and
                left["category"] == rule["category"]) or \
               (RARITY_ORDER.index(right["rarity"]) >= RARITY_ORDER.index(rule["rarity"]) and
                right["category"] == rule["category"])

    elif rtype == "category_exclusive":
        # Trigger only if either shard is in that category
        return left["category"] == rule["category"] or right["category"] == rule["category"]

    elif rtype == "any_shard":
        return True

    return False

def resolve_fusion(left_id, right_id, shard_dict, special_rules):
    """
    Resolve a fusion between left_id and right_id shards.
    Returns a list of shard IDs representing the fusion outputs.
    """
    left = shard_dict[left_id]
    right = shard_dict[right_id]

    # Base outputs
    outputs = algo.fusion_output(left_id, right_id, shard_dict)
    outputs = [o for o in outputs if o != left_id and o != right_id]  # prevent self-output

    # Special outputs
    special_outputs = []

    for special_shard_id, rules in special_rules.items():
        special_shard = shard_dict.get(special_shard_id, {})
        # Skip if the special shard is same as left or right
        if special_shard_id in [left_id, right_id]:
            continue

        for rule in rules:
            if rule_matches(rule, left, right):
                if special_shard_id not in special_outputs:
                    special_outputs.append(special_shard_id)

    # Merge outputs while respecting MAX_OUTPUTS
    for s in special_outputs:
        if s not in outputs and len(outputs) < MAX_OUTPUTS:
            outputs.append(s)

    return outputs[:MAX_OUTPUTS]






print(resolve_fusion("U39", "E4", shard_dict, fusion_dict))