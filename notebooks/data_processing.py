#!/usr/bin/env python
# coding: utf-8

# # This is a sample Jupyter Notebook
# 
# Below is an example of a code cell. 
# Put your cursor into the cell and press Shift+Enter to execute it and select the next one, or click 'Run Cell' button.
# 
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
# 
# To learn more about Jupyter Notebooks in PyCharm, see [help](https://www.jetbrains.com/help/pycharm/ipython-notebook-support.html).
# For an overview of PyCharm, go to Help -> Learn IDE features or refer to [our documentation](https://www.jetbrains.com/help/pycharm/getting-started.html).

# In[77]:


import pandas as pd
import numpy as np


# In[78]:


df = pd.read_csv("data/smartprix_laptop.csv", encoding="latin1")
print(f"Original shape: {df.shape}")


# In[79]:


# Drop columns we don't need for the MVP
columns_to_drop = ['os', 'warranty', 'disk_type', 'has_touchScreen', 'screen_pixels', 'screen_size']
df_clean = df.drop(columns=[col for col in columns_to_drop if col in df.columns])


# In[80]:


# 1. Ensure Price is a clean number
df_clean['price'] = pd.to_numeric(df_clean['price'], errors='coerce')


# In[81]:


df_clean['ram_gb'] = df_clean['ram'].str.extract('(\d+)').astype(float)


# In[82]:


def parse_storage(storage_str):
    if pd.isna(storage_str): return 0
    storage_str = str(storage_str).upper()
    try:
        val = float(''.join(filter(str.isdigit, storage_str)))
        if 'TB' in storage_str:
            return val * 1024 # Convert TB to GB
        return val
    except:
        return 0

df_clean['storage_gb'] = df_clean['storage'].apply(parse_storage)


# In[83]:


unique_cpus = df_clean['processor'].dropna().unique()
unique_gpus = df_clean['graphics_card'].dropna().unique()

print(f"\nCleaned dataset shape: {df_clean.shape}")
print(f"Number of unique Processors: {len(unique_cpus)}")
print(f"Number of unique GPUs: {len(unique_gpus)}")


# In[84]:


cpu_benchmarks = {
    "Apple M3 Max": 24000, "Apple M3 Pro": 15000, "Apple M3": 12000,
    "Apple M2 Max": 14000, "Apple M2": 10000, "Apple M1": 8000,
    "Core Ultra 9": 16000, "Core Ultra 7": 13000, "Core Ultra 5": 10000,
    "Ryzen 9": 17000, "Ryzen 7": 13000, "Ryzen 5": 9500, "Ryzen 3": 5500,
    "i9": 18000, "i7": 14000, "i5": 10000, "i3": 6000,
}

gpu_benchmarks = {
    "RTX 4090": 25000, "RTX 4080": 19000, "RTX 4070": 15000, "RTX 4060": 11000,
    "RTX 4050": 8000, "RTX 3080": 15000, "RTX 3070": 12000,
    "RTX 3060": 9000, "RTX 3050": 6000,
    "RX 7600": 10000, "RX 6600": 8000,
    "Apple": 5000
}


# In[85]:


def map_cpu_score(text):
    text = str(text).lower()


    match = re.search(r'i[3579][-\s]?(\d{4,5})', text)

    if match:
        num = int(match.group(1))

        if num >= 13000:
            return 20000
        elif num >= 11000:
            return 16000
        elif num >= 8000:
            return 12000


    for key in sorted(cpu_benchmarks.keys(), key=len, reverse=True):
        if key.lower() in text:
            return cpu_benchmarks[key]

    return 5000


# In[86]:


def map_gpu_score(text):
    text = str(text).lower()

    if text == 'nan' or 'integrated' in text:
        return 2000

    for key in sorted(gpu_benchmarks.keys(), key=len, reverse=True):
        if key.lower() in text:
            base = gpu_benchmarks[key]

            # VRAM boost
            if '6 gb' in text or '8 gb' in text:
                base *= 1.1

            return base

    return 3000


# In[87]:


import re

df_clean['CPU_Score'] = df_clean['processor'].apply(map_cpu_score)
df_clean['GPU_Score'] = df_clean['graphics_card'].apply(map_gpu_score)


# In[88]:


df_clean['Raw_Performance'] = (
    df_clean['CPU_Score'] * 0.7 +
    df_clean['GPU_Score'] * 0.3
)


# In[89]:


df_clean[['CPU_Score', 'GPU_Score', 'Raw_Performance']].head()


# In[90]:


min_perf = df_clean['Raw_Performance'].min()
max_perf = df_clean['Raw_Performance'].max()

if max_perf == min_perf:
    df_clean['Performance_1_to_10'] = 5
else:
    df_clean['Performance_1_to_10'] = 1 + 9 * (
        (df_clean['Raw_Performance'] - min_perf) /
        (max_perf - min_perf)
    )


# In[91]:


df_clean[['Raw_Performance', 'Performance_1_to_10']].head()


# In[92]:


def estimate_battery(row):
    cpu = str(row['processor']).upper()
    gpu = str(row['graphics_card']).upper()

    if 'APPLE' in cpu:
        return 9.5

    if 'RTX' in gpu or 'RX' in gpu:
        return 4.0

    if 'U' in cpu:
        return 8.0

    if 'H' in cpu or 'HX' in cpu:
        return 5.5

    return 6.5

df_clean['Battery_Proxy'] = df_clean.apply(estimate_battery, axis=1)


# In[93]:


df_clean[['processor', 'graphics_card', 'Battery_Proxy']].head()


# In[94]:


df_fixed = df_clean[['processor', 'graphics_card', 'Battery_Proxy']].head()

def fill_missing_column(df, column_name, fill_value):
    df[column_name] = df[column_name].fillna(fill_value)


most_frequent_value = df_fixed['graphics_card'].mode()[0]
fill_missing_column(df_fixed, 'graphics_card', most_frequent_value)
df_fixed


# In[95]:


df_clean[['processor', 'graphics_card', 'Battery_Proxy']].head()


# In[96]:


if 'price_INR' not in df_clean.columns:
    df_clean['price_INR'] = df_clean['price']

if 'weight' not in df_clean.columns:
    df_clean['weight'] = np.nan

final_columns = [
    'name',
    'price_INR',
    'Performance_1_to_10',
    'ram_gb',
    'storage_gb',
    'Battery_Proxy',
    'weight'
]

df_final = df_clean[final_columns]


# In[97]:


df_final.head(10)


# In[98]:


df_fixed = df_final.head(10)
import numpy as np


def calculate_iqr_bounds(series):
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    return lower_bound, upper_bound


df_fixed['weight'] = df_fixed['weight'].fillna(np.nan)


price_lower, price_upper = calculate_iqr_bounds(df_fixed['price_INR'])
df_fixed['price_INR'] = df_fixed['price_INR'].clip(lower=price_lower, upper=price_upper)


performance_lower, performance_upper = calculate_iqr_bounds(df_fixed['Performance_1_to_10'])
df_fixed['Performance_1_to_10'] = df_fixed['Performance_1_to_10'].clip(lower=performance_lower, upper=performance_upper)

ram_lower, ram_upper = calculate_iqr_bounds(df_fixed['ram_gb'])
df_fixed['ram_gb'] = df_fixed['ram_gb'].clip(lower=ram_lower, upper=ram_upper)


storage_lower, storage_upper = calculate_iqr_bounds(df_fixed['storage_gb'])
df_fixed['storage_gb'] = df_fixed['storage_gb'].clip(lower=storage_lower, upper=storage_upper)
df_fixed


# In[99]:


df_fixed = df_fixed
def fix_constant_column(df, column, new_value):
    """
    If a column has only one unique value (including NaN), it replaces the entire column with the given new value.
    """
    unique_values = df[column].dropna().unique()
    if len(unique_values) <= 1:  # Handles cases where the column has just one unique value or is entirely NaN
        df[column] = df[column].fillna(new_value)

# Fix the column 'weight' with 10 None values and replace it with a reasonable placeholder value.
# Assuming an average laptop weight of 1.5 kg for demonstration purposes.
# Replace it with a domain-specific value if provided or calculated beforehand.
df_fixed['weight'] = df_fixed['weight'].fillna(1.5)

# Fix the constant value issues in 'ram_gb' and 'storage_gb'
fix_constant_column(df_fixed, 'ram_gb', 16.0)  # Retain 16.0 as the value for RAM
fix_constant_column(df_fixed, 'storage_gb', 512.0)  # Retain 512.0 as the value for storage
df_fixed


# In[100]:


df_final.head(10)


# In[102]:


final_columns = ['name', 'price', 'Performance_1_to_10', 'ram_gb', 'Battery_Proxy']
print(df_clean[final_columns].head(10))


# In[103]:


def estimate_weight(row):
    batt = row['Battery_Proxy']
    perf = row['Performance_1_to_10']

    # If it has terrible battery and high performance, it's a heavy gaming rig
    if batt <= 5.0:
        return 2.4 + (np.random.rand() * 0.4) # ~2.4kg - 2.8kg
    # If it has amazing battery, it's usually a thin-and-light
    elif batt >= 8.5:
        return 1.2 + (np.random.rand() * 0.2) # ~1.2kg - 1.4kg
    # Standard office laptops
    else:
        return 1.6 + (np.random.rand() * 0.3) # ~1.6kg - 1.9kg

df_clean['Weight_Proxy'] = df_clean.apply(estimate_weight, axis=1)

# --- STEP 9: Final Clean and Export ---
final_ml_columns = [
    'name',
    'price',
    'Performance_1_to_10',
    'Weight_Proxy',
    'Battery_Proxy',
    'processor',
    'ram',
    'storage',
    'graphics_card',
    'img'
]

lapmatch_df = df_clean[final_ml_columns].copy()

# Drop any accidental missing values
lapmatch_df = lapmatch_df.dropna()

# Save the pristine dataset for our Streamlit app!
lapmatch_df.to_csv('data/lapmatch_clean_data.csv', index=False)

print("Data cleaning complete. Ready for ML!")
print(lapmatch_df.head())


# In[3]:





# In[ ]:




