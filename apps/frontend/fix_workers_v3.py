
import os

file_path = r"c:\Users\Tantely\Documents\SIIRH2\siirh-frontend\src\pages\Workers.tsx"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# 1. Remove redundant divs at 848-850
# Line 845: </div>
# Line 846: </div>
# Line 847: (empty)
# Line 848: </div>
# Line 849: </div>
# Line 850: </div>

# Let's check the indices (0-indexed)
# 847 is index 846.
# 848 is index 847.
# 849 is index 848.
# 850 is index 849.

# We only keep 845 and 846 (indices 844, 845) because they close the innermost blocks.
# We remove 848, 849, 850.
# We'll just replace the whole range with something clean.

# 2. Fix the openModal closure at 1089.
# We need to make sure we close all 4 divs opened by:
# 669, 670, 694, 695.
# Currently at line 1085-1090 we have:
# 1085: </div> (buttons)
# 1086: </div> (footer)
# 1087: </div>
# 1088: </div>
# Then line 1089 is:
# 1089: )}

# We need TWO MORE </div> before )} if we want to close 669/670/694/695.
# Total 4 divs after 1086.

# Let's do it.

# Part 1: Fix indices 847-849 (Lines 848-850)
# We'll just empty these lines or remove them from the list.
indices_to_remove = [847, 848, 849]
# Part 2: Fix lines near 1089.
# We'll find line 1089 and add two divs before it.

new_lines = []
for i, line in enumerate(lines):
    if i in indices_to_remove:
        continue # Skip the extra divs at mid-file
    
    if ")} " in line or ")}" in line:
        if i > 1000 and i < 1100:
            # This is the end of openModal
            # Add the missing divs
            new_lines.append("            </div>\n")
            new_lines.append("          </div>\n")
            new_lines.append("        )}\n")
            continue
    
    new_lines.append(line)

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Final structural fix applied.")
