import json

# Input file containing rows of data
input_file = "ibov.list"
output_file = "ibov.json"

# Read data from the file
with open(input_file, "r") as file:
    rows = file.readlines()

# Process each row and convert to JSON
json_list = []
for row in rows:
    columns = row.strip().split(",")
    json_data = {
        "Code": columns[0],
        "Company": columns[1],
        #"Sector": columns[2]
    }
    json_list.append(json_data)

# Write the JSON output to a file
with open(output_file, "w") as file:
    json.dump(json_list, file, indent=4)

print(f"JSON data has been written to {output_file}")
