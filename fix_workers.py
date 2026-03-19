
import os

file_path = "src/pages/Workers.tsx"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Verify content before replacing to be safe
print(f"Index 1089 (Line 1090): {lines[1089].rstrip()}")
print(f"Index 1090 (Line 1091): {lines[1090].rstrip()}")
print(f"Index 1091 (Line 1092): {lines[1091].rstrip()}")

if "</div>" in lines[1089] and ")" in lines[1090] and "}" in lines[1091]:
    print("Pattern matched. Replacing...")
    # Replace lines 1090, 1091, 1092 (indices 1089, 1090, 1091)
    # We want to keep 1090 (div) and add )}
    # And delete 1091, 1092
    
    # We replace slice [1089:1092] with correct lines
    # Note: slice 1089:1092 covers indices 1089, 1090, 1091
    lines[1089:1092] = ["        </div>\n", "      )}\n"]
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print("Success.")
else:
    print("Pattern NOT matched. Aborting to avoid damage.")
