import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# File names
files = ["FlyBase.csv.gz", "Human.csv.gz", "MGI.csv.gz", "RGD.csv.gz", "SGD.csv.gz", "WormBase.csv.gz", "XBXT.csv.gz", "ZFIN.csv.gz"]

# Loop over each file
for file in files:

    print(f"Processing {file}...")

    # Load the data
    df = pd.read_csv(file, compression='gzip')

    print("  Loaded data.")

    # Split the 'predictionMethodsMatched' column into lists
    df['predictionMethodsMatched'] = df['predictionMethodsMatched'].str.split(";")

    # Create a new column for the number of methods
    df['numMethods'] = df['predictionMethodsMatched'].str.len()

    # Get unique methods
    unique_methods = pd.unique(df['predictionMethodsMatched'].explode())

    print(f"  Found {len(unique_methods)} unique methods.")

    # Initialize dictionary to hold results
    results = {method: [] for method in unique_methods}

    # Loop over each unique number of methods
    for num in range(1, df['numMethods'].max() + 1):

        print(f"  Calculating percentages for {num} methods...")

        # Filter the dataframe for the current number of methods
        df_filtered = df[df['numMethods'] == num]

        # Loop over each unique method
        for method in unique_methods:

            # Calculate percentage of 'isBestScore' == 'Yes' when the current method is used
            percentage = (df_filtered[df_filtered['predictionMethodsMatched'].apply(lambda x: method in x)]['isBestScore'] == 'Yes').mean() * 100

            # Append percentage to results
            results[method].append(percentage)

    print("  Finished calculating percentages.")

    print("  Creating plot...")

    # Plot
    fig, ax = plt.subplots()
    x = np.arange(len(unique_methods))
    width = 0.1
    for i in range(df['numMethods'].max()):
        ax.bar(x - width/2 + i*width, [results[method][i] if i < len(results[method]) else 0 for method in unique_methods], width, label=f'{i+1} methods')
    ax.set_xticks(x)
    ax.set_xticklabels(unique_methods)
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')  # Place the legend outside the plot
    plt.title(file.split(".")[0])
    plt.ylabel("Percentage of 'isBestScore' == 'Yes' (%)")
    plt.xlabel("Methods")
    plt.xticks(rotation=90)
    plt.tight_layout()

    print("  Finished creating plot.")

    print(f"  Saving plot to {file.split('.')[0]}.png...")

    # Save the figure to a PNG file
    plt.savefig(f"{file.split('.')[0]}.png")

    # Clear the figure
    plt.clf()

    print(f"  Finished processing {file}.")
