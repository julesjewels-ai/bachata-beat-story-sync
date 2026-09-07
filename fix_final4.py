with open("src/core/audio_analyzer.py", "r") as f:
    c = f.read()
c = c.replace('boundaries_raw = np.where(beats_df["energy_ratio"] > 1.8)[0].tolist()\n        boundaries: list[int] = [int(str(x)) for x in boundaries_raw]', 'boundaries_raw = np.where(beats_df["energy_ratio"] > 1.8)[0].tolist()\n        boundaries = []\n        for x in boundaries_raw:\n            boundaries.append(int(str(x)))')
with open("src/core/audio_analyzer.py", "w") as f:
    f.write(c)
