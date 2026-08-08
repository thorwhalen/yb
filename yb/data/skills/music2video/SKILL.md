---
name: music2video
description: >
  Turn songs (.wav/.mp3) into publishable YouTube music videos with the `yb`
  package: render a still-cover, Ken Burns, or audio-reactive video, derive the
  thumbnail, loudness-normalize a whole album, verify the result against what
  YouTube actually accepts, and publish. Use when the user wants to publish a
  song or album to YouTube, make a music video or visualizer from an audio
  file, add cover art to a track for upload, or check a rendered music video
  before shipping it.
---

# music2video

You have audio; YouTube needs a video. **`muvid.visualize`** builds the asset
(canvas, visuals, loudness, encode, verify); **`yb.music`** is the publish-facing
facade that renders through it and uploads via `yb.youtube`.

Needs `pip install 'yb[music]'` (pulls `muvid`) + **ffmpeg** on the PATH.
Uploading also needs `yb[youtube]`. Rendering-only? Use `muvid.visualize`
directly (see the **`muvid-visualize`** skill in the `muvid` repo).

## Do it

```python
from yb.music import prepare_music_video, publish_music, prepare_folder, publish_folder

mv = prepare_music_video("song.wav", image="cover.png")  # render only
mv.video, mv.thumbnail, mv.content.title

publish_music("song.wav", image="cover.png", privacy_status="unlisted")
```

**A folder → an album** (the main workflow). Drop `(song.wav, song.jpeg)` pairs
in a folder — **filename = title**, covers match by stem — and each song renders
with the next visual in a rotation (`waves → cqt → spectrum → bars → scope` by
default), a consistent teal accent, one loudness target:

```python
publish_folder("~/album", limit=1)  # test the FIRST song, unlisted
publish_folder("~/album", playlist="My Album")  # then the whole set
prepare_folder("~/album", limit=1)  # render only, no upload, to review
publish_folder("~/album", cycle=["cqt"], privacy_status="unlisted")  # one look for all
```

`prepare_*` renders for inspection; `publish_*` renders *and* uploads (pass
`prepared=[...]` to upload already-reviewed videos). **Always `limit=1` first** —
render/publish one song, eyeball it, then do the rest.

## Choose a visual

`visual=` takes a name, `"auto"` (still if there's an image, else `cqt`), or any
callable. Timings are ×realtime on a 2-core box — divide by your core count.

| `visual` | Look | Cost | Notes |
|---|---|---|---|
| `still` *(default with an image)* | Cover held on a 16:9 canvas | **0.4×** | Loop-copy fast path: one segment encoded, then stream-copied. Use this unless asked otherwise. |
| `cqt` *(default without one)* | Constant-Q bars, pitch-aligned | 2.5× | The most *musical* reactive look — bars line up with notes, not FFT bins. |
| `bars` | Classic EQ bars (`showfreqs`) | 2.1× | |
| `spectrum` | Scrolling spectrogram | 2.2× | |
| `waves` | Waveform | 2.5× | Largest files (lots of fine motion). |
| `scope` | Stereo Lissajous | 1.7× | Only interesting on wide-stereo material. |
| `ken_burns` | Slow pan/zoom over the cover | **6.5×** | Frames render in Python (Pillow) — by far the slowest. Pans the *composed canvas* by default, so portrait art still fills 16:9 (`options={"source": "image"}` to pan the raw art). |

Reactive visuals composite automatically: a **muted, dark** blurred cover fills
the frame, the visualization (a consistent **teal** accent) is screened over it,
the sharp cover sits centred on top. Tune with `options={"cover_fraction": 0.7,
"cover_alpha": 0.7, "tint": "colorchannelmixer=...", "bg_saturation": 0.3}`.

`publish_folder` **rotates** the visual across a set (so it varies yet coheres);
for a single-visual set pass `visual=` / `cycle=["cqt"]`.

## Verify before publishing

Rendering can succeed and still be wrong. Check it — do not eyeball it:

```python
from muvid.visualize import verify_video, report, failures

checks = verify_video(
    "song.mp4", audio="song.wav", thumbnail="song.thumb.jpg", check_loudness=True
)  # check_loudness decodes the track
print(report(checks))
assert not failures(checks)
```

Covers: h264/aac, `yuv420p`, 16:9, ≥720p, 48 kHz stereo, video-vs-audio duration
match, integrated loudness vs target, and thumbnail size/ratio/bytes.

## What is baked in, and why

These are defaults, not decoration. Change them only with a reason.

- **16:9, never pillarboxed.** Square/portrait art is composed onto 1920×1080
  filled with a blurred, darkened copy of itself. The *same* composition is the
  thumbnail (`CoverLayout` → canvas → video *and* `.thumb.jpg`), so they match.
- **Loudness −14 LUFS**, two-pass EBU R128 (`normalize=True` by default). The
  single biggest lever for an album feeling cohesive.
- **The video is exactly as long as the song** (±0.12 s for stills, which are cut
  on a GOP boundary).
- **H.264 High / yuv420p / closed GOP / 2 B-frames, AAC-LC 48 kHz stereo,
  `+faststart`** — YouTube's own recommended upload encoding.
- **Music category** (`CATEGORY_MUSIC`, id 10) on upload.
- **Prefer the WAV.** YouTube re-encodes regardless; give it the cleanest input.

## Gotchas

**ffmpeg traps** (all reproduced on ffmpeg 6.1.1 — `muvid.visualize` already handles each):

- **`-shortest` does not bound an infinitely looping stream.** `-stream_loop -1
  -i seg.mp4 ... -shortest` runs forever and *fills the disk* (this cost us 16 GB).
  `muvid` uses a finite loop count **and** a hard `-t`. If you hand-roll ffmpeg, do
  the same.
- **`-fflags +shortest` truncates the end of your song** (~59 ms measured). It is
  widely copy-pasted advice. Do not use it on music.
- **`loudnorm` silently resamples to 192 kHz** (it upsamples internally for
  true-peak detection) unless you pin `-ar 48000`.
- **Bare `-af loudnorm` targets −24 LUFS**, the broadcast default — 10 LU quieter
  than YouTube. Always set `I`/`TP`/`LRA` explicitly.
- **Single-pass loudnorm compresses your master.** Only the two-pass form (measure,
  then apply with `measured_*`) applies a *linear* gain.
- **`yuv420p` cannot encode odd dimensions** — and album art is routinely an odd
  square (1401×1401). `muvid` raises a clear error; raw libx264 says "width not
  divisible by 2".
- **Pin the reactive filter's frame rate** (`showcqt=...:r=24` *and* an `fps` filter
  before encode) or you get rates like 30.62 fps.
- **ffmpeg writes an edit list (`elst`) by default**, to declare AAC priming delay
  — and YouTube's spec says *"No Edit Lists (or the video might not get processed
  correctly)"*. `-movflags +faststart` does **not** remove it; `-use_editlist 0
  -movflags +faststart+negative_cts_offsets` does. `verify_video` checks for this.
- **`-b:a 384k` does not deliver 384 kbps** with ffmpeg's native AAC encoder — it
  saturates around 336 kbps regardless. Harmless (YouTube re-encodes), but do not
  believe the number. `libfdk_aac` would actually hit it.
- **`-keyint_min` is silently ignored** — x264 clamps it to `keyint/2+1`.

**YouTube traps:**

- **`videos.insert` will not accept a still image.** It takes `video/*` only and
  synthesizes nothing — which is the whole reason this module exists. (Art Tracks,
  the auto-generated art+audio videos, are distributor/DDEX-only; you cannot make
  one yourself.)
- **`thumbnails.set` caps at 2 MB** — 25× stricter than the web UI's 50 MB, and it
  rejects GIF. `muvid` steps JPEG quality down until it fits.
- **YouTube only turns loud audio *down*, never quiet audio up.** A track mastered
  10 LU below target just plays quiet forever.
- **Content ID may claim your own video.** If the song is distributed through
  DistroKid/TuneCore/CD Baby with Content ID on, whitelist your channel *before*
  uploading, or your own release will claim your upload.
- **Upload quota is ~100 videos/day.** Since December 2025 `videos.insert` costs
  1 unit and draws on its **own** bucket (default 100 calls/day), not the shared
  10,000-unit pool. Older advice ("1600 units, ~6 uploads/day") is out of date.
- **AI disclosure** is `status.containsSyntheticMedia` (set it via
  `VideoMetadata(contains_synthetic_media=True)`). The trigger is *realism*, not
  "was AI involved": it applies to content a viewer could mistake for a real
  person/place/event. Stylised AI artwork or a visualizer does **not** require it.
- Until your Google Cloud project passes YouTube's API audit, uploads may be
  forced to **private** whatever you request.

## Extending: your own visual

A visual is a callable from a `VisualContext` to a `VisualPlan` — ffmpeg input
groups plus filter chains producing one video stream. Input 0 is always the
audio; set `uses_audio=True` and consume `[aviz]` to react to it. It lives in
`muvid.visualize` (rendering is muvid's job); pass the callable as `visual=`.

```python
from muvid.visualize import register_visual, VisualPlan


@register_visual("pulse")
def pulse(ctx):
    w, h = ctx.size
    return VisualPlan(
        filters=[f"[aviz]showvolume=w={w}:h={h}[vbg]"], video="vbg", uses_audio=True
    )
```

The escape hatch: **return a path instead of a plan** and the renderer muxes your
silent video with the audio. That is how a non-ffmpeg backend plugs in —
numpy/Pillow frames piped to ffmpeg, a moderngl/EGL shader, a projectM render.

If asked for something richer than the built-ins, the ranked options are:
**numpy frames piped to ffmpeg** (light, fully headless, most control) or
**ffmpeg `sendcmd` driven by a precomputed numpy envelope** (animate `overlay`,
`scale`, `hue` per frame — highest quality per dependency); then **moderngl +
EGL** for GLSL shaders (MIT, verified headless, ~15 MB); then **gst-projectm** in
a container for Milkdrop looks. Avoid as dependencies: `aubio` and `madmom`
(abandoned; GPL-3 / non-commercial), `essentia` (AGPL), `pedalboard` (GPL-3,
wrong tool), Remotion (paid licence for teams of 4+), ShaderFlow (AGPL). MoviePy
buys an API, not a capability, when you already require ffmpeg.

## Facts verified 2026-07-14

Checked against YouTube's docs and reproduced locally. Re-verify if much time has
passed. Note one claim we **refuted**: cover art does *not* need to be ≥3000×3000
for a YouTube thumbnail — that is the DistroKid/Spotify *release cover* spec (1:1).
YouTube thumbnails are 16:9, minimum width 640, recommended 1280×720, ≤2 MB.
