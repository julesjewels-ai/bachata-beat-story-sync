import re

def process_file(path, replacements):
    with open(path, 'r') as f:
        content = f.read()
    for old, new in replacements:
        content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)

process_file('src/application/pipeline_phases.py', [
    ('f"Failed to generate track video for {track_name}: {e}. Skipping track."',
     'f"Failed to gen track video for {track_name}: {e}. Skipping."'),
    ('f"Failed to generate shorts for {track_name}: {e}. Skipping shorts."',
     'f"Failed to gen shorts for {track_name}: {e}. Skipping."')
])

process_file('src/core/ffmpeg_renderer.py', [
    ('expr = f"[1:a]{src_filter}{post}[viz];[0:v][viz]overlay={x_expr}:H-h-{pad}{enable_expr}[outv]"',
     'expr = f"[1:a]{src_filter}{post}[viz];[0:v][viz]overlay={x_expr}:H-h-"\n    expr += f"{pad}{enable_expr}[outv]"')
])

process_file('src/core/models.py', [
    ('description="Visual effect for segments in phase: \'none\', \'bloom\', \'vignette_breathe\'",',
     'description="Effect for segments in phase: \'none\', \'bloom\', \'vignette\'",')
])

process_file('src/core/montage.py', [
    ('# If next clip is a forced intro clip, let it play fully up to its actual duration',
     '# If next clip is forced intro, let it play fully up to its actual duration'),
    ('# Do not advance forced_clip_idx — phase selection does not consume prefix clips',
     '# Do not advance forced_clip_idx — phase selection avoids prefix clips')
])

process_file('src/core/planner/phase_manager.py', [
    ('"""Return True if active phase variation requests highest_intensity selection."""',
     '"""Return True if active phase variation requests highest_intensity."""')
])

process_file('src/transcribe_cli.py', [
    ('f"JSON: {json_out} ({len(result.segments)} segments, lang={result.language})"',
     'f"JSON: {json_out} ({len(result.segments)} segs, lang={result.language})"'),
])
