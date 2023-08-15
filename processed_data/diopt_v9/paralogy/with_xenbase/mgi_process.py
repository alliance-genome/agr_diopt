import pandas as pd

# Load the CSV data
df = pd.read_csv("xbxt.csv.gz")  # Replace "file_path" with the path to your file

# Split the 'predictionMethodsMatched' column into lists
df['predictionMethodsMatched'] = df['predictionMethodsMatched'].str.split(";")

# Create a new column for the number of methods
df['numMethods'] = df['predictionMethodsMatched'].str.len()

# Count the total number of times each number of methods is used
total_counts = df['numMethods'].value_counts().sort_index()

# Count the number of times isBestScore is 'Yes' for each number of methods
is_best_score_counts = df[df['isBestScore'] == 'Yes']['numMethods'].value_counts().sort_index()

# Calculate the percentages
is_best_score_percentages = (is_best_score_counts / total_counts) * 100

print("Number of Methods Called and Percentage of isBestScore 'Yes':")
print(is_best_score_percentages)

# Create a dataframe for the methods used when only one method is used
df_one_method = df[df['numMethods'] == 1]

# Count the total number of times each method is used when only one method is used
total_counts_one_method = df_one_method['predictionMethodsMatched'].apply(lambda x: x[0]).value_counts()

# Count the number of times isBestScore is 'Yes' for each method when only one method is used
is_best_score_counts_one_method = df_one_method[df_one_method['isBestScore'] == 'Yes']['predictionMethodsMatched'].apply(lambda x: x[0]).value_counts()

# Calculate the percentages
is_best_score_percentages_one_method = (is_best_score_counts_one_method / total_counts_one_method) * 100

print("\nNumber of Times Each Method is Used When Only One Method is Used and Percentage of isBestScore 'Yes':")
print(is_best_score_percentages_one_method)
