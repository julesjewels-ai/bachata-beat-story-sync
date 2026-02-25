import sys
import json
import subprocess
import os

def main():
    # Run radon
    result = subprocess.run(["radon", "cc", "src", "-j"], capture_output=True, text=True)
    if result.returncode != 0:
        print("Error running radon")
        sys.exit(1)

    try:
        complexity_data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("Error decoding radon output")
        print(result.stdout)
        sys.exit(1)

    processed_functions = set()
    if os.path.exists("refactor_progress.txt"):
        with open("refactor_progress.txt", "r") as f:
            for line in f:
                processed_functions.add(line.strip())

    candidates = []
    for filepath, blocks in complexity_data.items():
        for block in blocks:
            if block["type"] == "function" or block["type"] == "method":
                func_name = block["name"]
                complexity = block["complexity"]
                full_name = f"{filepath}:{func_name}"

                if full_name not in processed_functions:
                    candidates.append({
                        "file": filepath,
                        "name": func_name,
                        "complexity": complexity,
                        "full_name": full_name
                    })

    if not candidates:
        print("No candidates found.")
        return

    # Sort by complexity descending
    candidates.sort(key=lambda x: x["complexity"], reverse=True)

    top_candidate = candidates[0]

    if top_candidate["complexity"] < 8:
        print("<promise>NO_ACTION_REQUIRED</promise>")
    else:
        print(f"Target: {top_candidate['name']}")
        print(f"File: {top_candidate['file']}")
        print(f"Complexity: {top_candidate['complexity']}")
        print(f"Full Name: {top_candidate['full_name']}")

if __name__ == "__main__":
    main()
