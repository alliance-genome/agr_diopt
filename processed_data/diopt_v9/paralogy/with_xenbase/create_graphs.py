import pandas as pd
import matplotlib.pyplot as plt

# Load the CSV data
df = pd.read_csv("ZFIN.csv.gz")

# Split the 'predictionMethodsMatched' column into lists
df['predictionMethodsMatched'] = df['predictionMethodsMatched'].str.split(";")

# Create a new column for the number of methods
df['numMethods'] = df['predictionMethodsMatched'].str.len()

# Count the total number of times each number of methods is used
total_counts = df['numMethods'].value_counts().sort_index()

# Count the number of times isBestScore is 'Yes' for each number of methods
is_best_score_counts = df[df['isBestScore'] == 'Yes']['numMethods'].value_counts().sort_index()

methods = total_counts.index
counts = total_counts.values
best_score_counts = is_best_score_counts.reindex(methods, fill_value=0).values

# Create the figure and the axes for the first graph
fig, ax1 = plt.subplots(figsize=(10, 6))

# Create the bar chart for the number of times each number of methods is used
bars1 = ax1.bar(methods, counts, color='lightblue', log=True)

# Create the bar chart for the number of times isBestScore is 'Yes' for each number of methods
bars2 = ax1.bar(methods, best_score_counts, color='blue', log=True)

# Set the title and labels for the first graph
ax1.set_title('(ZFIN) Number of Methods (Algorithms) Called for All Gene1 to Gene2 Pairs (Log Scale) and Percentage of isBestScore')
ax1.set_xlabel('Number of Methods')
ax1.set_ylabel('Number of Times Called (Log Scale)')

# Add a legend
ax1.legend([bars1, bars2], ['Total', 'isBestScore'], loc='upper right')

# Set the x-ticks to be every integer number of methods
ax1.set_xticks(range(0, methods.max()+1))

# Save the first graph as a PNG file
plt.savefig('zfin_methods_called_shaded_legend_every_number.png')

# Show the first graph
plt.show()

# Create a new dataframe for only one method is used
df_single_method = df[df['numMethods'] == 1]

# Count the total number of times each method is used when only one method is used
total_counts_single_method = df_single_method['predictionMethodsMatched'].explode().value_counts().sort_index()

# Count the number of times isBestScore is 'Yes' for each method
is_best_score_counts_single_method = df_single_method[df_single_method['isBestScore'] == 'Yes']['predictionMethodsMatched'].explode().value_counts().reindex(total_counts_single_method.index, fill_value=0)

# Create the figure and the axes for the second graph
fig, ax1 = plt.subplots(figsize=(14, 6))

# Create the bar chart for the number of times each algorithm is used when only one algorithm is used
bars1 = ax1.bar(total_counts_single_method.index, total_counts_single_method.values, color='lightblue', log=True)

# Create the bar chart for the number of times isBestScore is 'Yes' for each algorithm
bars2 = ax1.bar(total_counts_single_method.index, is_best_score_counts_single_method.values, color='blue', log=True)

# Set the title and labels for the second graph
ax1.set_title('(ZFIN) Number of Times Each Algorithm is Used When Only One Algorithm Is Matched (Log Scale) and Percentage of isBestScore')
ax1.set_xlabel('Algorithms')
ax1.set_ylabel('Number of Times Called (Log Scale)')

# Add a legend
ax1.legend([bars1, bars2], ['Total', 'isBestScore'], loc='upper right')

# Save the second graph as a PNG file
plt.savefig('zfin_single_method_used_shaded_legend.png')

# Show the second graph
plt.show()
