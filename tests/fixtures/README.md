# Test fixtures

Tiny video clips used by `tests/test_probe_integration.py` to exercise the
real `ffprobe` integration (the rest of the suite mocks `subprocess.run` and
needs no media).

## Provenance and licence

These clips are derived from original footage **copyright Salim Fadhley**
(Mind of Steele, episode 161), used here with permission. They are distributed
as part of `steele-fcpxml` under the project's **GPL-3.0-or-later** licence.

Each file is a ~1 second, 160x90 excerpt re-encoded to a specific frame rate.
They are deliberately tiny (~10 KB each) so they can be versioned in git
without bloating the repository.

## Files

| File                          | Resolution | Frame rate         |
| ----------------------------- | ---------- | ------------------ |
| `clip_160x90_24fps.mp4`       | 160x90     | 24                 |
| `clip_160x90_25fps.mp4`       | 160x90     | 25 (PAL)           |
| `clip_160x90_29_97fps.mp4`    | 160x90     | 29.97 (30000/1001) |
| `clip_160x90_30fps.mp4`       | 160x90     | 30                 |

## Regenerating

From a source video, for each desired frame rate (e.g. `25`, or `30000/1001`
for 29.97):

```bash
ffmpeg -y -ss 60 -i <source.mov> -t 1 \
  -vf "scale=160:90" -r <rate> \
  -c:v libx264 -preset veryfast -crf 35 -pix_fmt yuv420p \
  -c:a aac -b:a 32k \
  clip_160x90_<label>fps.mp4
```
