with open("src/core/audio_analyzer.py", "r") as f:
    c = f.read()
c = c.replace('change_points = list(np.where(gradient >= change_threshold)[0] + 1)', 'change_points = [int(x) for x in (np.where(gradient >= change_threshold)[0] + 1).tolist()]')
c = c.replace('boundaries: list[int] = [0] + change_points + [len(curve)]', 'boundaries: list[int] = [0] + change_points + [len(curve)]')
with open("src/core/audio_analyzer.py", "w") as f:
    f.write(c)
