
import os

file_path = "src/pages/Workers.tsx"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Line 1089 (Index 1088)
print(f"Index 1088: {lines[1088]}")
print(f"Index 1089: {lines[1089]}")
print(f"Index 1090: {lines[1090]}")

if "</div>" in lines[1088]:
    print("Deleting index 1088...")
    del lines[1088]
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print("Success.")
else:
    print("Line 1088 is not a div. Abort.")
