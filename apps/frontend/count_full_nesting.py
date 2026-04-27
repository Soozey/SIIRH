
import os

file_path = r"c:\Users\Tantely\Documents\SIIRH2\siirh-frontend\src\pages\Workers.tsx"

with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

open_braces = text.count("{")
close_braces = text.count("}")
open_parens = text.count("(")
close_parens = text.count(")")

print(f"Braces: {open_braces} open, {close_braces} close. Balance: {open_braces - close_braces}")
print(f"Parens: {open_parens} open, {close_parens} close. Balance: {open_parens - close_parens}")

# Count divs too
open_divs = text.count("<div")
close_divs = text.count("</div>")
print(f"Divs: {open_divs} open, {close_divs} close. Balance: {open_divs - close_divs}")

# Let's check the very end of the file
lines = text.splitlines()
print("--- End of file (last 10 lines) ---")
for i in range(max(0, len(lines)-10), len(lines)):
    print(f"{i+1}: {lines[i]}")
