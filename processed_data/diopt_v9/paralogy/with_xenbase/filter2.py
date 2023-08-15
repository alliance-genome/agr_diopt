import pandas as pd
import numpy as np

# Your data
data = {
    "Human": {
        "Ensembl Compara": 98.21,
        "InParanoid": 0.42,
        "OMA": 9.84,
        "OrthoFinder": 18.46,
        "OrthoInspector": 10.71,
        "PANTHER": 2.47,
        "PhylomeDB": 2.32,
        "SonicParanoid": 0.77
    },
    "FlyBase": {
        "Ensembl Compara": 41.84,
        "InParanoid": 0.56,
        "OMA": 33.33,
        "OrthoFinder": 32.35,
        "OrthoInspector": 24.24,
        "PANTHER": 9.52,
        "PhylomeDB": 7.72,
        "SonicParanoid": 2.03
    },
    "ZFIN": {
        "Ensembl Compara": 10.94,
        "InParanoid": 0.48,
        "OMA": 1.28,
        "OrthoFinder": 4.66,
        "OrthoInspector": 2.78,
        "PANTHER": 2.80,
        "PhylomeDB": 3.20,
        "SonicParanoid": 2.54
    },
    "WormBase": {
        "Ensembl Compara": 10.89,
        "InParanoid": 0.71,
        "OMA": 39.00,
        "OrthoFinder": 29.69,
        "OrthoInspector": 12.50,
        "PANTHER": 8.66,
        "PhylomeDB": 3.90,
        "SonicParanoid": 5.57
    },
    "SGD": {
        "Ensembl Compara": 19.47,
        "InParanoid": 4.55,
        "OMA": 20.00,
        "OrthoFinder": 11.42,
        "OrthoInspector": 33.33,
        "PANTHER": 29.65,
        "PhylomeDB": 16.57,
        "SGD": 90.48,
        "SonicParanoid": float('nan')
    },
    "RGD": {
        "Ensembl Compara": 3.37,
        "InParanoid": float('nan'),
        "OMA": 25.00,
        "OrthoFinder": 8.98,
        "OrthoInspector": 8.33,
        "PANTHER": 1.31,
        "PhylomeDB": 3.76,
        "SonicParanoid": 0.11
    },
    "MGI": {
        "Ensembl Compara": 86.33,
        "HGNC": 72.88,
        "InParanoid": float('nan'),
        "OMA": 5.26,
        "OrthoFinder": 13.94,
        "OrthoInspector": 19.44,
        "PANTHER": 1.39,
        "PhylomeDB": 3.11,
        "SonicParanoid": 0.22
    }
}

# Convert the data to a DataFrame
df = pd.DataFrame(data).transpose()

# Calculate the 75th and 50th percentiles for each dataset
strict_thresholds = df.quantile(0.75, axis=1)
moderate_thresholds = df.quantile(0.50, axis=1)

# Initialize lists to store the names of the methods for the strict and moderate filters
strict_filter_methods = []
moderate_filter_methods = []

# For each dataset, get the names of the methods that pass the strict and moderate filters
for dataset in df.index:
    strict_filter_methods.append(df.columns[df.loc[dataset] >= strict_thresholds[dataset]].tolist())
    moderate_filter_methods.append(df.columns[df.loc[dataset] >= moderate_thresholds[dataset]].tolist())

# Create a DataFrame to display the names of the methods for the strict and moderate filters
filter_methods_df = pd.DataFrame({
    'Dataset': df.index,
    'Strict Filter Methods': strict_filter_methods,
    'Moderate Filter Methods': moderate_filter_methods
})

print(filter_methods_df)
