
import os

file_path = r"c:\Users\Tantely\Documents\SIIRH2\siirh-frontend\src\pages\Workers.tsx"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

b = 0
p = 0
d = 0

for i, line in enumerate(lines):
    old_b, old_p, old_d = b, p, d
    b += line.count("{") - line.count("}")
    p += line.count("(") - line.count(")")
    d += line.count("<div") - line.count("</div>")
    
    if i >= 660 and i < 1100:
        if b != old_b or p != old_p or d != old_d:
             print(f"Line {i+1:4}: B:{b:2} P:{p:2} D:{d:2} | {line.strip()}")

print(f"Final Balance: B:{b} P:{p} D:{d}")
