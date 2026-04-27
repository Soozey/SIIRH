
import os
import re

file_path = r"c:\Users\Tantely\Documents\SIIRH2\siirh-frontend\src\pages\Workers.tsx"

with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

# Pattern to find the corrupted blocks I inserted:
#             </div>
#           </div>
#         )}
# (with varying whitespace)

# We want to replace these blocks with just "        )}"
# But only if they were part of the corruption.
# Most of them were.

# Let's use a more specific regex.
corrupted_pattern = re.compile(r'\s+</div>\n\s+</div>\n\s+\)}\n', re.MULTILINE)

# Let's count matches
matches = corrupted_pattern.findall(text)
print(f"Found {len(matches)} corrupted blocks.")

# Replace them with a single "        )}\n"
fixed_text = corrupted_pattern.sub("        )}\n", text)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(fixed_text)

print("Cleanup complete.")
