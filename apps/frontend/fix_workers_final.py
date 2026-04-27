
import os

file_path = r"c:\Users\Tantely\Documents\SIIRH2\siirh-frontend\src\pages\Workers.tsx"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Problem area: lines 1085-1092
# Current content (from view_file):
# 1085:                   </div>
# 1086:                 </div>
# 1087:               </div>
# 1088:               </div>
# 1089:         </div>
# 1090:       </div>
# 1091:   )
# 1092: }

# We want to replace this whole block with something that correctly closes the openModal block
# and allows the rest of the file to be inside the Workers component.

# Let's find the indices.
# Note: lines are 1-indexed in the editor, 0-indexed in the list.
# 1091 is index 1090.

# We need to trace the start:
# 668:       {openModal && (
# 669:         <div className="fixed inset-0 bg-black/50 ...">  (1)
# 670:           <div className="bg-white ..."> (2)
# 671:             {/* Header */}
# 672:             <div className="border-b ..."> (3)
# 689:               </button>
# 690:             </div> (Closed 3)
# 691:           </div> (Wait, check line 691 in file)

# Let's check lines 685-695 to be sure.
print("--- Lines 685-695 ---")
for i in range(684, 695):
    print(f"{i+1}: {lines[i].strip()}")

# Let's check lines 1080-1095
print("--- Lines 1080-1095 ---")
for i in range(1079, 1095):
    print(f"{i+1}: {lines[i].strip()}")

# The goal is to make sure we only close what was opened in the openModal block.
# openModal block opened: 
# 1. <div> at line 669
# 2. <div> at line 670
# (Header is closed already)
# 3. <div> at line 694 (Form)
# (Inner divs of Form are usually closed)

# Let's see where 694 (Form) starts.
# 1075: {/* Actions / Footer */}
# So Form should close before Footer.

# If 694 (Form) closes at 1074, then Header (671) is closed at 691.
# Then 669 (1) and 670 (2) are still open.
# Footer (1076) starts. It's a sibling of Form.
# Footer (1076) has:
# 1076: <div> (Footer div)
# 1086: </div> (Closed Footer div)

# So at line 1087, we only have 1 and 2 open.
# So we only need TWO </div> at the end of the openModal block.

# Currently at line 1087-1090 we have FOUR </div>.
# That's why it's closing everything and even more.
# 1087, 1088, 1089, 1090.

# If it closes 4 divs, it closes:
# - content div (maybe 536?)
# - something else?

# Wait, at line 1090 we have:
# 1087: </div>
# 1088: </div>
# 1089: </div>
# 1090: </div>
# Total 4.

# If we only need 2, let's remove the extra 2.
# And DEFINITELY remove line 1091 and 1092.

lines[1086] = "              </div>\n" # Index 1086 is line 1087
lines[1087] = "            </div>\n" # Index 1087 is line 1088
lines[1088] = "          </div>\n" # Index 1088 is line 1089
lines[1089] = "        </div>\n" # Index 1089 is line 1090

# Wait, let's just rewrite the block from 1087 to 1092.
# 1087: </div>
# 1088: </div>
# 1089:   )}
# ... and everything else remains.

new_lines = lines[:1086] # Up to line 1086 (inclusive)
new_lines.append("            </div>\n") # Close 670
new_lines.append("          </div>\n")   # Close 669
new_lines.append("        )}\n")         # Close openModal
# Then continue with the rest of the file from 1093?
# Wait, line 1091/1092 was premature closure.
# We skip line 1091 and 1092.
new_lines.extend(lines[1092:])

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)
print("Structural fix applied.")
