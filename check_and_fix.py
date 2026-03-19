
import os

file_path = "src/pages/Workers.tsx"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Print lines around the area to be sure
# Line 1085 (Index 1084) to 1095 (Index 1094)
for i in range(1084, 1095):
    if i < len(lines):
        print(f"Line {i+1}: {lines[i].rstrip()}")

# Fix Logic:
# We expect:
# 1086: </div> (Footer)
# 1087: </div> (Panel)
# 1088: </div> (Overlay)
# 1089: )}
#
# If we see extra divs, we delete them.

# Check specific indices
# Line 1089 (index 1088)
# Line 1090 (index 1089)
# Line 1091 (index 1090)

if "</div>" in lines[1088] and "</div>" in lines[1089] and ")}" in lines[1090]:
    print("Found Pattern: div(1089), div(1090), )}(1091).")
    print("Deleting Line 1089 and 1090 (Indices 1088, 1089)...")
    
    # We want to remove lines[1088] and lines[1089]
    # Be careful with list modification logic.
    # Replacing slice [1088:1090] with [] removes them.
    del lines[1088:1090]
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print("Success. Extra divs removed.")

elif "</div>" in lines[1088] and "</div>" in lines[1089] and "</div>" in lines[1090]:
    # Maybe we have even more?
    print("Found Pattern: 3 divs at 1089, 1090, 1091.")
    # Check 1092 for )}
    if ")}" in lines[1091]:
        print("Found )} at 1092.")
        print("Removing 2 extra divs...")
        del lines[1089:1091] # Remove 1090, 1091
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
    else:
        print("Analyze output manually.")
else:
    print("Pattern match failed. Analyze output manually.")
