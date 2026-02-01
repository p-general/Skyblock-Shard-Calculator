import pandas as pd
import json

# Step 1: Read CSV 
df = pd.read_csv("data.csv")

# Clean up the IDs column
df["IDs"] = df["IDs"].str.strip()

# Step 2: Determine base fusion eligibility 
# A shard is eligible if it has fusion results (not empty or dash)
df["base_fusion_elig"] = df["Fusions to get current shard"].apply(
    lambda x: False if pd.isna(x) or str(x).strip() == "---" else True
)

# Strip whitespace from Families column first
df["Families"] = df["Families"].str.strip()

# Replace empty strings or N/A with "Unknown"
df["Families"] = df["Families"].replace(["", "N/A", "n/a", None], "Unknown")

# Step 3: Parse Fusion Results into lists
def parse_fusion_results(cell):
    if pd.isna(cell) or str(cell).strip() == "-":
        return []
    # Split by comma
    return [s.strip() for s in str(cell).split(",")]

df["next_base_fusions"] = df["Current Shard Uses for Fusion"].apply(parse_fusion_results)

# Step 4: Build the JSON dictionary 
shard_dict = {}
for _, row in df.iterrows():
    shard_dict[row["IDs"]] = {
        "name": row["Current Shard"],
        "family": row["Families"],
        "category": row["Category"],
        "rarity": row["Rarity"],
        "fusion_count": int(row["Fus"]),
        "base_fusion_elig": row["base_fusion_elig"],
        "next_base_fusions": row["next_base_fusions"]
    }

# Step 5: Save JSON 
with open("shard_data_ready.json", "w") as f:
    json.dump(shard_dict, f, indent=4)

print("JSON file created successfully!")
