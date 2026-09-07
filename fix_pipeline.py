import re

def process_file(path, replacements):
    with open(path, 'r') as f:
        content = f.read()
    for old, new in replacements:
        content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)

process_file('src/pipeline.py', [
    ('partial(generate_mix_video_phase, app_engine)', 'partial(generate_mix_video_phase, app_engine)  # type: ignore[arg-type]')
])
