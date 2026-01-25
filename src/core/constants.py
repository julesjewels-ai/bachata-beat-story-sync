"""
Centralized constants for the application.
"""

SUPPORTED_AUDIO_EXTENSIONS = {'.wav', '.mp3'}
SUPPORTED_VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv'}

# Security constants to prevent DoS
MAX_VIDEO_FRAMES = 100_000  # Approx 1 hour at 30 FPS
MAX_VIDEO_DURATION_SECONDS = 3600  # 1 hour

BLUR_KERNEL_SIZE = (21, 21)
NORMALIZATION_FACTOR = 100
