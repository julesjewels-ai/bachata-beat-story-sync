with open("src/core/audio_analyzer.py", "r") as f:
    c = f.read()
c = c.replace('boundaries = sorted(set(boundaries))', 'boundaries = sorted(list(set(boundaries)))')
with open("src/core/audio_analyzer.py", "w") as f:
    f.write(c)
