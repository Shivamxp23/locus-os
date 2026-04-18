import ast, sys

files = [
    "/opt/locus/backend/services/llm.py",
    "/opt/locus/backend/services/lightrag_service.py",
    "/opt/locus/backend/routers/vault.py",
    "/opt/locus/backend/routers/wiki.py",
]

for f in files:
    try:
        ast.parse(open(f).read())
        print(f"{f}: syntax OK")
    except SyntaxError as e:
        print(f"{f}: SYNTAX ERROR - {e}")
        sys.exit(1)

print("\nAll files pass syntax check!")
