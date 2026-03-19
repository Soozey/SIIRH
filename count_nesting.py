
import os

file_path = "src/pages/Workers.tsx"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Modal starts at line 668 (index 667)
# Modal ends around line 1090 (index 1089)

start_index = 667
end_index = 1090 

# Adjust end index to be just before the )}
if end_index > len(lines):
    end_index = len(lines)

open_divs = 0
close_divs = 0

print(f"Counting divs from line {start_index+1} to {end_index}...")

for i in range(start_index, end_index):
    line = lines[i]
    open_divs += line.count("<div")
    close_divs += line.count("</div>")

print(f"Total <div: {open_divs}")
print(f"Total </div>: {close_divs}")
print(f"Balance: {open_divs - close_divs}")

if open_divs > close_divs:
    print(f"Missing {open_divs - close_divs} closing divs.")
elif close_divs > open_divs:
    print(f"Too many closing divs: {close_divs - open_divs} extra.")
else:
    print("Perfectly balanced.")
