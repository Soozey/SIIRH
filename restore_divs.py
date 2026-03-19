
import os

file_path = "src/pages/Workers.tsx"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# We expect to find:
# 1085:                   </div> (Gap)
# 1086:                 </div> (Footer)
# 1087:               </div> (Form Inner?)
# 1088:             </div> (Form Body?)
# 1089:       )}

# But currently we have:
# 1085:                   </div>
# 1086:                 </div>
# 1087:               </div>
# 1088:             </div>
# 1089:       )}

# Wait, I need 6 closing divs total from the GAP.
# Gap is 1085.
# Footer 1086.
# Form Inner 1087.
# Form Body 1088.
# Panel 1089.
# Overlay 1090.
# )} 1091.

# Current state (from output 4557 check):
# Line 1085:                   </div>
# Line 1086:                 </div>
# Line 1087:               </div>
# Line 1088:             </div>
# Line 1089: ignored (was deleted)
# Line 1090: ignored (was deleted)
# Line 1091:       )}

# So currently I have 4 closing divs (1085, 1086, 1087, 1088).
# I need 2 more.

# I need to insert 2 divs before the line containing ")}"
for i, line in enumerate(lines):
    if ")}" in line and i > 1085 and i < 1100:
        print(f"Found ')}}' at line {i+1}")
        # Insert 2 divs
        # Indentation should decrease: 10, 8
        lines.insert(i, "          </div>\n")
        lines.insert(i+1, "        </div>\n")
        break

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(lines)
print("Restored 2 divs.")
