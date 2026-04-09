import sys
try:
    with open('src/ui/theme.py', 'r') as f:
        content = f.read()
    # Try to execute just the tokens and the THEME_CSS part
    exec(content)
    print("Success: theme.py is valid.")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
