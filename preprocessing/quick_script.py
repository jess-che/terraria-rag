import re
import json

# File paths
input_file = 'preprocessing/terraria_preprocessed_chunks_drops.json'
output_file = 'terraria_preprocessed_chunks_drops.json'

# Load the JSON data from the input file
with open(input_file, 'r', encoding='utf-8') as file:
    json_data = json.load(file)

# Function to clean the text as described
def clean_treasure_bag_and_tree(data):
    updated_data = []
    
    for entry in data:
        text = entry.get("text", "")
        
        # Remove the first occurrence of 'Treasure Bag (something) (something else)'
        updated_text = re.sub(r'Treasure Bag\s*\(.*?\)\s*\(.*?\)\s*', '', text, count=1)
        
        # Regex to remove only the second occurrence of 'something tree', in this case, 'Mahogany tree'
        tree_occurrences = list(re.finditer(r'\b(\w+ tree)\b', updated_text))
        if len(tree_occurrences) > 1:
            second_tree_match = tree_occurrences[1]  # Get the second occurrence
            updated_text = updated_text[:second_tree_match.start()] + updated_text[second_tree_match.end():]
        
        # Update the entry with the cleaned text
        updated_entry = entry.copy()
        updated_entry["text"] = updated_text
        updated_data.append(updated_entry)
    
    return updated_data

# Clean the JSON data
cleaned_data = clean_treasure_bag_and_tree(json_data)

# Save the cleaned JSON data to the output file
with open(output_file, 'w', encoding='utf-8') as file:
    json.dump(cleaned_data, file, ensure_ascii=False, indent=4)
