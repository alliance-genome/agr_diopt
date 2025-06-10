import pandas as pd
import matplotlib.pyplot as plt

# Manually insert the provided results into the DataFrame
df_combined = pd.DataFrame({
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
    },
    "Xenbase": {
        "Ensembl Compara": 37.00,
        "InParanoid": 7.68,
        "OMA": 8.33,
        "OrthoFinder": 21.19,
        "OrthoInspector": 13.54,
        "PANTHER": 18.16,
        "PhylomeDB": 12.19,
        "SonicParanoid": 5.96
    }
})

# Create a bar plot
ax = df_combined.plot(kind='bar', figsize=(15, 7), colormap='tab20')

# Set the title and labels
ax.set_title('Percentage of isBestScore "Yes" for Each Method When Only One Method is Used Across All Datasets')
ax.set_xlabel('Method')
ax.set_ylabel('Percentage')

# Save the plot as a PNG file
plt.savefig('output.png')

# Show the plot
plt.show()

