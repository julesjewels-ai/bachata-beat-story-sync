# Fonts

Place font files here for video text overlays (FEAT-045).

## Recommended: Noto Sans

Noto Sans covers all Spanish characters (á é í ó ú ñ ü ¿ ¡) and is free.

Download from https://fonts.google.com/noto/specimen/Noto+Sans:
- `NotoSans-Bold.ttf`
- `NotoSans-Regular.ttf`

Or install via the Makefile:

```bash
make install-fonts
```

## Fallback behaviour

If no fonts are found here, the system searches:
- macOS: `/Library/Fonts`, `/System/Library/Fonts/Supplemental`
- Linux: `/usr/share/fonts/truetype/noto`, `/usr/share/fonts/truetype`

Arial and Helvetica are used as last-resort fallbacks (both cover Latin Extended).
