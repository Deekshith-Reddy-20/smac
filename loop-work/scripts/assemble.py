#!/usr/bin/env python3
"""Loop Work content engine: topic -> script (Gemini) -> mixed visuals -> MP4."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
JOBS = ROOT / "jobs"
OUTPUT = ROOT / "output"
LOCAL = ROOT / "assets" / "local"
PROMPT_FILE = Path(__file__).resolve().parent / "prompt.txt"

GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-flash-latest",
    "gemini-1.5-flash",
]


def load_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def log(msg: str) -> None:
    print(f"[loop-work] {msg}", flush=True)


def slugify(text: str, limit: int = 48) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return (text or "loop-work")[:limit]


def http_json(url: str, method: str = "GET", data: dict | None = None, headers: dict | None = None, timeout: int = 90) -> Any:
    body = None
    req_headers = {"User-Agent": "Mozilla/5.0 LoopWork/1.0"}
    req_headers.update(headers or {})
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def http_download(url: str, dest: Path, headers: dict | None = None, timeout: int = 180) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req_headers = {"User-Agent": "Mozilla/5.0 LoopWork/1.0"}
    req_headers.update(headers or {})
    req = urllib.request.Request(url, headers=req_headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        dest.write_bytes(resp.read())
    if dest.stat().st_size < 2000:
        raise RuntimeError(f"Download too small ({dest.stat().st_size} bytes): {url[:80]}")


def require_ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise SystemExit(
            "FFmpeg is not installed. In PowerShell run:\n"
            "  winget install Gyan.FFmpeg\n"
            "Then close and reopen the terminal."
        )
    return exe


def run_ffmpeg(args: list[str]) -> None:
    cmd = [require_ffmpeg(), "-y", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "")[-2000:]
        raise RuntimeError(f"FFmpeg failed:\n{err}")


def read_prompt() -> str:
    return PROMPT_FILE.read_text(encoding="utf-8")


def call_gemini(user_text: str) -> dict[str, Any]:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("Missing GEMINI_API_KEY. Copy loop-work/.env.example to .env and add your free key from https://aistudio.google.com/apikey")

    preferred = os.environ.get("GEMINI_MODEL", "").strip()
    models = [preferred] + [m for m in GEMINI_MODELS if m != preferred] if preferred else GEMINI_MODELS
    last_error = None
    payload = {
        "systemInstruction": {"parts": [{"text": read_prompt()}]},
        "contents": [{"role": "user", "parts": [{"text": user_text}]}],
        "generationConfig": {
            "temperature": 0.8,
            "responseMimeType": "application/json",
        },
    }
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            log(f"Writing script with {model}...")
            data = http_json(url, method="POST", data=payload, timeout=120)
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            text = re.sub(r"^```json\s*|\s*```$", "", text.strip(), flags=re.I)
            pack = json.loads(text)
            pack["_model"] = model
            return pack
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            log(f"{model} failed ({exc}). Trying next free model...")
    raise SystemExit(f"Gemini failed. Last error: {last_error}")


def local_files() -> list[Path]:
    if not LOCAL.exists():
        return []
    exts = {".mp4", ".mov", ".webm", ".jpg", ".jpeg", ".png", ".webp"}
    return [p for p in LOCAL.rglob("*") if p.is_file() and p.suffix.lower() in exts]


def pick_local(hint: str) -> Path | None:
    files = local_files()
    if not files:
        return None
    tokens = [t for t in re.split(r"[^a-z0-9]+", hint.lower()) if len(t) > 2]
    scored: list[tuple[int, Path]] = []
    for path in files:
        name = str(path).lower()
        score = sum(1 for t in tokens if t in name)
        scored.append((score, path))
    scored.sort(key=lambda x: (-x[0], random.random()))
    return scored[0][1]


def pexels_search(kind: str, query: str, portrait: bool) -> str | None:
    key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not key:
        return None
    orient = "portrait" if portrait else "landscape"
    if kind == "video":
        url = (
            "https://api.pexels.com/v1/videos/search?"
            + urllib.parse.urlencode({"query": query, "orientation": orient, "per_page": 8, "size": "medium"})
        )
    else:
        url = (
            "https://api.pexels.com/v1/search?"
            + urllib.parse.urlencode({"query": query, "orientation": orient, "per_page": 8})
        )
    try:
        data = http_json(url, headers={"Authorization": key}, timeout=40)
    except Exception as exc:  # noqa: BLE001
        log(f"Pexels error: {exc}")
        return None

    if kind == "video":
        videos = data.get("videos") or []
        random.shuffle(videos)
        for video in videos:
            files = sorted(video.get("video_files") or [], key=lambda f: abs((f.get("width") or 0) - (1080 if portrait else 1920)))
            for item in files:
                link = item.get("link")
                if link and (item.get("width") or 0) >= 640:
                    return link
        return None

    photos = data.get("photos") or []
    random.shuffle(photos)
    for photo in photos:
        src = photo.get("src") or {}
        return src.get("portrait") or src.get("large2x") or src.get("large")
    return None


def pollinations_image(prompt: str, dest: Path, portrait: bool) -> None:
    width, height = (1080, 1920) if portrait else (1920, 1080)
    full = (
        f"{prompt}, cinematic lighting, photoreal, premium tech brand, "
        "no readable text, no watermark, no logo, no subtitles"
    )
    url = (
        "https://image.pollinations.ai/prompt/"
        + urllib.parse.quote(full, safe="")
        + f"?width={width}&height={height}&model=flux&nologo=true&enhance=true&seed={random.randint(1, 999999)}"
    )
    log("Generating AI image...")
    http_download(url, dest, timeout=120)
    time.sleep(16)


def pollinations_video(prompt: str, dest: Path, portrait: bool) -> bool:
    key = os.environ.get("POLLINATIONS_KEY", "").strip()
    if not key:
        return False
    ratio = "9:16" if portrait else "16:9"
    url = (
        "https://gen.pollinations.ai/video/"
        + urllib.parse.quote(prompt, safe="")
        + f"?model=wan&duration=4&aspectRatio={ratio}"
    )
    log("Generating short AI video clip (optional, may take a while)...")
    try:
        http_download(url, dest, headers={"Authorization": f"Bearer {key}"}, timeout=240)
        return dest.stat().st_size > 20000
    except Exception as exc:  # noqa: BLE001
        log(f"AI video skipped: {exc}")
        return False


def fetch_visual(scene: dict[str, Any], dest: Path, portrait: bool) -> Path:
    visual = (scene.get("visual_type") or "ai_image").strip().lower()
    query = scene.get("pexels_query") or scene.get("local_hint") or "small business laptop"
    ai_prompt = scene.get("ai_prompt") or query
    hint = scene.get("local_hint") or query

    def from_local() -> Path | None:
        picked = pick_local(hint)
        if not picked:
            return None
        target = dest.with_suffix(picked.suffix.lower())
        shutil.copy2(picked, target)
        log(f"Using local file {picked.name}")
        return target

    if visual == "local":
        local = from_local()
        if local:
            return local

    if visual == "ai_video":
        if pollinations_video(ai_prompt, dest.with_suffix(".mp4"), portrait):
            return dest.with_suffix(".mp4")
        visual = "pexels_video"

    if visual == "pexels_video":
        link = pexels_search("video", query, portrait)
        if link:
            out = dest.with_suffix(".mp4")
            log(f"Downloading Pexels video: {query}")
            http_download(link, out, timeout=120)
            return out
        local = from_local()
        if local and local.suffix.lower() in {".mp4", ".mov", ".webm"}:
            return local
        visual = "pexels_photo"

    if visual == "pexels_photo":
        link = pexels_search("photo", query, portrait)
        if link:
            out = dest.with_suffix(".jpg")
            log(f"Downloading Pexels photo: {query}")
            http_download(link, out, timeout=60)
            return out
        local = from_local()
        if local:
            return local

    out = dest.with_suffix(".jpg")
    pollinations_image(ai_prompt, out, portrait)
    return out


async def speak(text: str, dest: Path, voice: str) -> None:
    try:
        import edge_tts
    except ImportError as exc:
        raise SystemExit("edge-tts is missing. Run: pip install -r loop-work/requirements.txt") from exc
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(dest))


def ffprobe_duration(path: Path) -> float:
    exe = shutil.which("ffprobe") or require_ffmpeg().replace("ffmpeg", "ffprobe")
    proc = subprocess.run(
        [exe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True,
        text=True,
    )
    try:
        return max(0.8, float(proc.stdout.strip()))
    except ValueError:
        return 4.0


def srt_timestamp(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, milli = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{milli:03d}"


def write_srt(scenes: list[dict[str, Any]], total: float, dest: Path) -> None:
    weights = [max(1, len((s.get("narration") or "").split())) for s in scenes]
    total_w = sum(weights) or 1
    t = 0.0
    blocks = []
    idx = 1
    for scene, weight in zip(scenes, weights):
        dur = total * (weight / total_w)
        words = (scene.get("narration") or "").strip().split()
        if not words:
            t += dur
            continue
        chunk_size = 4
        chunks = [" ".join(words[i : i + chunk_size]).upper() for i in range(0, len(words), chunk_size)]
        slice_dur = dur / len(chunks)
        for chunk in chunks:
            start, end = t, min(total, t + slice_dur)
            blocks.append(f"{idx}\n{srt_timestamp(start)} --> {srt_timestamp(end)}\n{chunk}\n")
            idx += 1
            t = end
    dest.write_text("\n".join(blocks), encoding="utf-8")


def make_scene_clip(src: Path, dest: Path, duration: float, portrait: bool) -> None:
    w, h = (1080, 1920) if portrait else (1920, 1080)
    fps = 30
    frames = max(int(duration * fps), 15)
    vf_base = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={fps}"
    if src.suffix.lower() in {".mp4", ".mov", ".webm", ".mkv"}:
        run_ffmpeg(
            [
                "-stream_loop",
                "-1",
                "-ss",
                "0.4",
                "-i",
                str(src),
                "-t",
                f"{duration:.2f}",
                "-vf",
                vf_base,
                "-an",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-preset",
                "veryfast",
                str(dest),
            ]
        )
        return
    # Ken Burns on stills so the reel does not look like a frozen slideshow.
    run_ffmpeg(
        [
            "-loop",
            "1",
            "-i",
            str(src),
            "-t",
            f"{duration:.2f}",
            "-vf",
            (
                f"scale=4000:-1,zoompan=z='min(zoom+0.0012,1.12)':"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={w}x{h}:fps={fps}"
            ),
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "veryfast",
            str(dest),
        ]
    )


def escape_ffmpeg_path(path: Path) -> str:
    text = path.as_posix().replace(":", "\\:")
    return text.replace("'", "\\'")


def assemble_video(scenes_dir: Path, voice: Path, srt: Path, out: Path, portrait: bool) -> None:
    clips = sorted(scenes_dir.glob("clip_*.mp4"))
    if not clips:
        raise RuntimeError("No scene clips were created.")
    listing = scenes_dir / "concat.txt"
    listing.write_text("".join(f"file '{p.as_posix()}'\n" for p in clips), encoding="utf-8")
    w, h = (1080, 1920) if portrait else (1920, 1080)
    font = "C\\:/Windows/Fonts/arialbd.ttf"
    if not Path("C:/Windows/Fonts/arialbd.ttf").exists():
        font = "C\\:/Windows/Fonts/arial.ttf"
    srt_esc = escape_ffmpeg_path(srt)
    vf = (
        f"subtitles='{srt_esc}':force_style='Fontname=Arial Black,Fontsize=18,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,"
        "Shadow=1,Alignment=2,MarginV=140',"
        f"drawtext=fontfile='{font}':text='LOOP WORK':x=w-text_w-40:y=48:"
        "fontsize=32:fontcolor=white:shadowcolor=black:shadowx=2:shadowy=2"
    )
    run_ffmpeg(
        [
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(listing),
            "-i",
            str(voice),
            "-vf",
            vf,
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "fast",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(out),
        ]
    )
    if out.stat().st_size < 10000:
        raise RuntimeError("Output video is empty.")
    _ = (w, h)


def write_publish(pack: dict[str, Any], dest: Path) -> None:
    hashtags = pack.get("hashtags") or []
    if isinstance(hashtags, str):
        tags = hashtags
    else:
        tags = " ".join(f"#{t.lstrip('#')}" for t in hashtags)
    text = "\n".join(
        [
            "LOOP WORK — publish kit",
            "",
            f"TITLE: {pack.get('title', '')}",
            f"HOOK: {pack.get('hook', '')}",
            "",
            "INSTAGRAM / YOUTUBE SHORTS CAPTION",
            pack.get("caption", ""),
            tags,
            "",
            "YOUTUBE DESCRIPTION",
            pack.get("youtube_description", ""),
            "",
            "SPOKEN SCRIPT",
            pack.get("script", ""),
            "",
        ]
    )
    dest.write_text(text, encoding="utf-8")


def normalize_pack(pack: dict[str, Any], fmt: str) -> dict[str, Any]:
    pack["format"] = (pack.get("format") or fmt).lower()
    scenes = pack.get("scenes") or []
    if not scenes:
        raise SystemExit("Gemini returned no scenes. Run again.")
    pack["scenes"] = scenes
    pack["script"] = pack.get("script") or " ".join(s.get("narration", "") for s in scenes)
    pack["title"] = pack.get("title") or "Loop Work"
    return pack


def build_from_pack(pack: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    require_ffmpeg()
    fmt = pack.get("format") or "reel"
    portrait = fmt != "youtube"
    scenes = pack["scenes"]
    media_dir = run_dir / "media"
    clips_dir = run_dir / "clips"
    media_dir.mkdir(parents=True, exist_ok=True)
    clips_dir.mkdir(parents=True, exist_ok=True)

    used_ai_video = False
    visual_paths: list[Path] = []
    for i, scene in enumerate(scenes, start=1):
        if (scene.get("visual_type") or "") == "ai_video" and used_ai_video:
            scene["visual_type"] = "pexels_video"
        path = fetch_visual(scene, media_dir / f"scene_{i:02d}", portrait)
        if path.suffix.lower() in {".mp4", ".mov", ".webm"} and scene.get("visual_type") == "ai_video":
            used_ai_video = True
        visual_paths.append(path)

    voice_path = run_dir / "voice.mp3"
    voice = os.environ.get("VOICE", "en-US-AndrewNeural")
    log("Generating free voiceover...")
    asyncio.run(speak(pack["script"], voice_path, voice))
    total = ffprobe_duration(voice_path)
    weights = [max(1, len((s.get("narration") or "").split())) for s in scenes]
    total_w = sum(weights) or 1
    log("Building scene clips...")
    for i, (scene, src, weight) in enumerate(zip(scenes, visual_paths, weights), start=1):
        dur = max(1.6, total * (weight / total_w))
        make_scene_clip(src, clips_dir / f"clip_{i:02d}.mp4", dur, portrait)

    srt_path = run_dir / "captions.srt"
    write_srt(scenes, total, srt_path)
    video_path = run_dir / ("reel.mp4" if portrait else "youtube.mp4")
    log("Rendering final video...")
    assemble_video(clips_dir, voice_path, srt_path, video_path, portrait)
    publish_path = run_dir / "publish.txt"
    write_publish(pack, publish_path)
    (run_dir / "pack.json").write_text(json.dumps(pack, indent=2), encoding="utf-8")
    return {
        "ok": True,
        "channel": "Loop Work",
        "title": pack.get("title"),
        "video": str(video_path),
        "publish": str(publish_path),
        "folder": str(run_dir),
        "format": fmt,
    }


def user_prompt(topic: str, fmt: str, notes: str) -> str:
    fmt_label = "YouTube Short / Instagram Reel (9:16, 40-55 seconds, 6 scenes)" if fmt == "reel" else "YouTube video (16:9, 7-10 minutes, 10 scenes)"
    extra = f"\nExtra direction from the creator: {notes}" if notes else ""
    if topic:
        return (
            f"Create one {fmt_label} for the Loop Work channel.\n"
            f"Topic: {topic}{extra}\n"
            "Return JSON only."
        )
    return (
        f"Pick the strongest topic for today and create one {fmt_label} for Loop Work.{extra}\n"
        "The topic must fit automation, website design, or digital marketing.\n"
        "Return JSON only."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Loop Work free content factory")
    parser.add_argument("--job", help="Path to an existing pack JSON from n8n")
    parser.add_argument("--topic", default="", help="Video topic. Leave empty to auto-pick.")
    parser.add_argument("--format", choices=["reel", "youtube"], default="reel")
    parser.add_argument("--notes", default="", help="Optional extra direction")
    parser.add_argument("--auto", action="store_true", help="Let Gemini pick the topic")
    return parser.parse_args()


def main() -> None:
    load_env()
    args = parse_args()
    JOBS.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    LOCAL.mkdir(parents=True, exist_ok=True)

    if args.job:
        pack = json.loads(Path(args.job).read_text(encoding="utf-8"))
        fmt = pack.get("format") or args.format
    else:
        fmt = args.format
        topic = "" if args.auto else args.topic
        pack = call_gemini(user_prompt(topic, fmt, args.notes))
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        job_path = JOBS / f"{stamp}.json"
        job_path.write_text(json.dumps(pack, indent=2), encoding="utf-8")
        log(f"Saved script JSON to {job_path}")

    pack = normalize_pack(pack, fmt)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = OUTPUT / f"{stamp}-{slugify(pack.get('title', 'loop-work'))}"
    run_dir.mkdir(parents=True, exist_ok=True)
    result = build_from_pack(pack, run_dir)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        raise
