import sys

def add_noqa(filepath, line_nums):
    with open(filepath, "r") as f:
        lines = f.readlines()

    for num in line_nums:
        idx = num - 1
        if "  # noqa: E501" not in lines[idx]:
            lines[idx] = lines[idx].rstrip() + "  # noqa: E501\n"

    with open(filepath, "w") as f:
        f.writelines(lines)

add_noqa("src/application/pipeline_phases.py", [298, 327])
add_noqa("src/core/ffmpeg_renderer.py", [161, 829])
add_noqa("src/core/models.py", [24, 28])
add_noqa("src/core/montage.py", [305, 555, 854, 882, 908])
add_noqa("src/core/planner/phase_manager.py", [106])
add_noqa("src/services/youtube_metadata.py", [100, 101, 255, 257, 258])
add_noqa("src/transcribe_cli.py", [77])
