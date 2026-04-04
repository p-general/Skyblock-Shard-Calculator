import itertools
import pandas as pd
import base_fusion_algo
import bazaar_api_integration


def scan_two_hop_fusions(shard_dict, bazaar):
    """
    Scan all two-hop fusion paths:
      Hop 1: A + B -> C  (crafted)
      Hop 2: C + D -> E  (final output, sold)
    Profit = sell(E) - cost(A+B inputs) - cost(D input)
    C is crafted from hop 1, not bought.
    """
    results = []
    shard_ids = list(shard_dict.keys())

    # Precompute: output_id -> list of (left_id, right_id) that produce it
    fusion_map = base_fusion_algo.build_fusion_map(shard_dict)

    # For each intermediate shard C that can be crafted
    for intermediate_id, hop1_pairs in fusion_map.items():

        # Find all (C, D) pairs where C is the crafted intermediate
        for d_id in shard_ids:
            if d_id == intermediate_id:
                continue

            hop2_outputs = base_fusion_algo.fusion_output(intermediate_id, d_id, shard_dict)
            if not hop2_outputs:
                continue

            # Cost of buying D
            d_shard = shard_dict[d_id]
            d_key = bazaar_api_integration.shard_to_bazaar_key(d_shard["name"])
            d_status = bazaar.get(d_key)
            if not d_status:
                continue
            d_quick = d_status["quick_status"]
            if not d_quick:
                continue
            if d_quick["sellVolume"] < d_shard["fusion_count"]:
                continue
            if d_quick["buyOrders"] > d_quick["sellOrders"] * 5:
                continue
            if d_quick["sellOrders"] == 0:
                continue
            d_cost = d_quick["buyPrice"] * d_shard["fusion_count"] * 0.9875

            for final_id in hop2_outputs:
                final_shard = shard_dict.get(final_id)
                if not final_shard:
                    continue

                final_status = bazaar_api_integration.get_quick_status(final_shard["name"], bazaar)
                if not final_status:
                    continue
                if final_status["buyVolume"] > final_status["sellVolume"] * 1.5:
                    continue
                if final_status["buyOrders"] > final_status["sellOrders"] * 5:
                    continue
                if final_status["buyOrders"] == 0:
                    continue

                effective_sell = final_status["sellPrice"] * 0.97

                # Find the cheapest hop 1 path to C
                best_hop1 = None
                for a_id, b_id in hop1_pairs:
                    hop1_cost = base_fusion_algo.fusion_cost(a_id, b_id, shard_dict, bazaar)
                    if hop1_cost is None:
                        continue
                    if best_hop1 is None or hop1_cost < best_hop1["cost"]:
                        best_hop1 = {"a": a_id, "b": b_id, "cost": hop1_cost}

                if best_hop1 is None:
                    continue

                # Hop 1 must be repeated fusion_count times to supply enough intermediates
                intermediate_fusion_count = shard_dict[intermediate_id]["fusion_count"]
                total_cost = (best_hop1["cost"] * intermediate_fusion_count) + d_cost
                profit = effective_sell - total_cost
                margin = (profit / total_cost * 100) if total_cost > 0 else 0

                results.append({
                    "hop1_left": best_hop1["a"],
                    "hop1_right": best_hop1["b"],
                    "intermediate": intermediate_id,
                    "hop2_right": d_id,
                    "output": final_id,
                    "hop1_cost": best_hop1["cost"] * intermediate_fusion_count,
                    "hop2_d_cost": d_cost,
                    "total_cost": total_cost,
                    "value": effective_sell,
                    "profit": profit,
                    "margin": margin
                })

    df = pd.DataFrame(results)
    if df.empty:
        return df

    df = df.sort_values(by="profit", ascending=False)
    df = df.drop_duplicates(subset="output", keep="first").reset_index(drop=True)
    return df


if __name__ == "__main__":
    results = scan_two_hop_fusions(base_fusion_algo.shard_dict, bazaar_api_integration.bazaar_prods)
    print(f"Total profitable two-hop fusions: {len(results)}")
    print(results.head(10))
