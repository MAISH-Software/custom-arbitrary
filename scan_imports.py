import os
import ast

third_party = set()

stdlib_modules = {
    'os', 'sys', 'math', 'json', 'time', 'datetime', 'logging', 're', 'subprocess', 'threading',
    'multiprocessing', 'itertools', 'functools', 'collections', 'random', 'shutil', 'pathlib',
    'http', 'urllib', 'unittest', 'pprint', 'decimal', 'inspect', 'types'
}

def find_imports(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        node = ast.parse(f.read(), filename=filepath)
    for n in ast.walk(node):
        if isinstance(n, ast.Import):
            for name in n.names:
                mod = name.name.split('.')[0]
                if mod not in stdlib_modules:
                    third_party.add(mod)
        elif isinstance(n, ast.ImportFrom):
            mod = (n.module or '').split('.')[0]
            if mod and mod not in stdlib_modules:
                third_party.add(mod)

for root, dirs, files in os.walk('src'):
    for file in files:
        if file.endswith('.py'):
            find_imports(os.path.join(root, file))

print("\nThird-party packages detected:")
for pkg in sorted(third_party):
    print(pkg)
