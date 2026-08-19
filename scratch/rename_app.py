import os

replacements = {
    "Type Scholar": "Type Scholar",
    "TypeScholar": "TypeScholar",
    "typescholar": "typescholar",
    "type-scholar": "type-scholar",
}

for root, dirs, files in os.walk("."):
    if ".git" in root or ".venv" in root or "dist" in root or "build" in root or "__pycache__" in root:
        continue
    for file in files:
        if file.endswith((".py", ".sh", ".md", ".toml", ".ps1", ".txt", ".plist", ".spec")):
            filepath = os.path.join(root, file)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                
            new_content = content
            for old, new in replacements.items():
                new_content = new_content.replace(old, new)
                
            if new_content != content:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"Updated {filepath}")
