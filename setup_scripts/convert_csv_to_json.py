#!/usr/bin/env python3
"""Convert the CSV to JSON format"""
import pandas as pd
import json

# Read the CSV
df = pd.read_csv('uk_lotto_real_data_oct2015_onwards.csv')

# Convert to JSON
# Option 1: Array of objects (best for most uses)
json_data = df.to_dict('records')
with open('uk_lotto_data.json', 'w') as f:
    json.dump(json_data, f, indent=2)

print(f"✓ Created uk_lotto_data.json with {len(json_data)} draws")

# Option 2: Grouped by year (alternative format)
df['year'] = pd.to_datetime(df['date']).dt.year
grouped = df.groupby('year').apply(lambda x: x.drop('year', axis=1).to_dict('records')).to_dict()
with open('uk_lotto_data_by_year.json', 'w') as f:
    json.dump(grouped, f, indent=2)

print("✓ Created uk_lotto_data_by_year.json (grouped by year)")
