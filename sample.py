import pandas as pd

# Load the full CSV
df = pd.read_csv("D:\\Acads\\BTP\\MELD-FAIR-main\\csvs\\MELD_video_realignment_timestamps.csv")

# Filter for specific test dialogues (e.g., dialogues 0, 1, 2)
test_dialogues = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]  # Add the dialogue IDs you have
df_filtered = df[df['Split'] == 'test']

# Save the filtered CSV
df_filtered.to_csv("D:\\Acads\\BTP\\MELD-FAIR-main\\csvs\\MELD_video_realignment_timestamps_test.csv", index=False)