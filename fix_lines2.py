with open("src/core/ffmpeg_renderer.py", "r") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "If seg.phase_pacing_effects is a list" in line:
        lines[i] = "    If seg.phase_pacing_effects is a list (even empty), only those named effects are\n    active.\n"

with open("src/core/ffmpeg_renderer.py", "w") as f:
    f.writelines(lines)

with open("src/services/youtube_metadata.py", "r") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "🔎 Palabras clave:" in line:
        lines[i] = "        \"🔎 Palabras clave: música para recordar, canciones de amor, \"\n        \"bachata romántica, \"\n"

with open("src/services/youtube_metadata.py", "w") as f:
    f.writelines(lines)
