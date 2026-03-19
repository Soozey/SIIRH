
import os

file_path = "src/pages/Workers.tsx"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# We need to add one </div> before )}
# Find the line with )}
for i, line in enumerate(lines):
    if ")}" in line and i > 1000 and i < 1100:
        print(f"Found ')}}' at line {i+1}")
        # Insert 1 div
        lines.insert(i, "        </div>\n")
        break

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(lines)
print("Added 1 missing div.")
