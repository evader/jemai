import os

gitignore_path = r'C:\JEMAI_HUB\.gitignore'

# Read current lines if .gitignore exists, else create new list
if os.path.exists(gitignore_path):
    with open(gitignore_path, 'r') as f:
        lines = [line.rstrip('\n') for line in f]
else:
    lines = []

# Add 'terra/' if not present
if 'terra/' not in lines:
    lines.append('terra/')

# Write back .gitignore
with open(gitignore_path, 'w') as f:
    for line in lines:
        f.write(line + '\n')

print('[JEMAI AGI] .gitignore updated: terra/ will be excluded from git.')
