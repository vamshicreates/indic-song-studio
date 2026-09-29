#!/usr/bin/env python3
"""
Indic Song Studio + Voice Studio — Local Web Application Server
===============================================================
Serves the interactive Song Brief, Voice Studio (16+ Singer Personas & Custom Voice
Cloning), and Mastering Web UI on http://127.0.0.1:7865.
"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
import shutil
import subprocess
import threading
import uuid
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from song_engine import (
    BASE_DIR,
    LIBRARY_JSON,
    OUTPUTS_DIR,
    PRESET_BRIEFS,
    SongBrief,
    build_brief_from_instruction,
    convert_singing_voice_seedvc,
    format_brief_markdown,
    generate_song,
    load_library,
    save_to_library,
)
from voice_studio import (
    CUSTOM_VOICES_DIR,
    VOICE_REFS_DIR,
    analyze_and_register_custom_voice,
    build_ffmpeg_voice_filter,
    ensure_voice_reference_audio,
    get_voice_catalog_list,
    get_voice_profile,
)

STATIC_DIR = BASE_DIR / "static"
JOBS = {}
JOBS_LOCK = threading.Lock()


def bootstrap_initial_take():
    """Ensures the reference takes are preloaded in the Studio Library."""
    lib = load_library()
    if lib:
        return

    src_dir = BASE_DIR.parent / "ganesh_chaturthi_telugu_song"
    raw_src = src_dir / "acestep_v15_telugu_take1.mp3"
    m12_src = src_dir / "Raavayya_Ganapayya_Telugu_Song.mp3"
    orig_src = src_dir / "Raavayya_Ganapayya_Original_Pitch_Master.mp3"
    wav_src = src_dir / "Raavayya_Ganapayya_Telugu_Song.wav"

    slug = "Raavayya_Ganapayya_Reference"
    raw_dst = OUTPUTS_DIR / f"{slug}_Raw.mp3"
    m12_dst = OUTPUTS_DIR / f"{slug}_12yo_Master.mp3"
    orig_dst = OUTPUTS_DIR / f"{slug}_Original_Pitch_Master.mp3"
    wav_dst = OUTPUTS_DIR / f"{slug}_Master.wav"

    if m12_src.exists() and not m12_dst.exists():
        shutil.copy2(m12_src, m12_dst)
    if orig_src.exists() and not orig_dst.exists():
        shutil.copy2(orig_src, orig_dst)
    if raw_src.exists() and not raw_dst.exists():
        shutil.copy2(raw_src, raw_dst)
    elif orig_dst.exists() and not raw_dst.exists():
        shutil.copy2(orig_dst, raw_dst)
    if wav_src.exists() and not wav_dst.exists():
        shutil.copy2(wav_src, wav_dst)

    if m12_dst.exists():
        preset = PRESET_BRIEFS["ganesh_chaturthi_telugu_12yo"]
        brief = SongBrief(**{k: v for k, v in preset.items() if k in SongBrief.__dataclass_fields__})
        profile = get_voice_profile("12yo_boy")
        brief_md = OUTPUTS_DIR / f"{slug}_Production_Brief.md"
        brief_md.write_text(
            format_brief_markdown(
                brief,
                profile,
                slug,
                {
                    "primary_mp3": m12_dst,
                    "original_pitch_mp3": orig_dst if orig_dst.exists() else m12_dst,
                    "wav_master": wav_dst if wav_dst.exists() else m12_dst,
                },
            ),
            encoding="utf-8",
        )
        entry = {
            "id": "reference_12yo_take",
            "slug": slug,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "title": preset["title"],
            "brief_text": preset["brief_text"],
            "vocal_language": "te",
            "bpm": 108,
            "key_scale": "D major",
            "duration": 57,
            "voice_id": "12yo_boy",
            "voice_name": profile["name"],
            "semitone_shift": 1.0,
            "vocal_preset": profile["name"],
            "style_prompt": preset["style_prompt"],
            "lyrics": preset["lyrics"],
            "h3_prompt": preset["h3_prompt"],
            "files": {
                "raw_mp3": f"/outputs/{raw_dst.name}" if raw_dst.exists() else f"/outputs/{orig_dst.name}",
                "primary_mp3": f"/outputs/{m12_dst.name}",
                "original_pitch_mp3": f"/outputs/{orig_dst.name}" if orig_dst.exists() else f"/outputs/{m12_dst.name}",
                "wav_master": f"/outputs/{wav_dst.name}" if wav_dst.exists() else f"/outputs/{m12_dst.name}",
                "brief_md": f"/outputs/{brief_md.name}",
                "primary_mp3_abs": str(m12_dst),
                "original_pitch_mp3_abs": str(orig_dst),
                "wav_master_abs": str(wav_dst),
            },
        }
        save_to_library(entry)


class StudioRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass

    def _send_json(self, data: dict, status: int = 200):
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _serve_file(self, file_path: Path):
        if not file_path.exists() or not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return

        ctype, _ = mimetypes.guess_type(str(file_path))
        if not ctype:
            ctype = "application/octet-stream"
        if file_path.suffix == ".md":
            ctype = "text/markdown; charset=utf-8"

        file_size = file_path.stat().st_size
        range_header = self.headers.get("Range")

        if range_header:
            m = re.match(r"bytes=(\d+)-(\d*)", range_header)
            if m:
                start = int(m.group(1))
                end = int(m.group(2)) if m.group(2) else file_size - 1
                end = min(end, file_size - 1)
                if start <= end:
                    length = end - start + 1
                    self.send_response(HTTPStatus.PARTIAL_CONTENT)
                    self.send_header("Content-Type", ctype)
                    self.send_header("Accept-Ranges", "bytes")
                    self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                    self.send_header("Content-Length", str(length))
                    self.end_headers()
                    with file_path.open("rb") as f:
                        f.seek(start)
                        self.wfile.write(f.read(length))
                    return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(file_size))
        self.end_headers()
        with file_path.open("rb") as f:
            shutil.copyfileobj(f, self.wfile)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path in ("/", "/index.html"):
            self._serve_file(STATIC_DIR / "index.html")
            return

        if path == "/api/library":
            self._send_json(
                {
                    "takes": load_library(),
                    "presets": PRESET_BRIEFS,
                    "voices": get_voice_catalog_list(),
                }
            )
            return

        if path == "/api/voices":
            self._send_json({"voices": get_voice_catalog_list()})
            return

        if path.startswith("/api/jobs/"):
            job_id = path.split("/api/jobs/", 1)[1]
            with JOBS_LOCK:
                job = JOBS.get(job_id)
            if not job:
                self._send_json({"error": "Job not found"}, status=404)
                return
            self._send_json(job)
            return

        if path.startswith("/outputs/voice_refs/"):
            fname = Path(path.split("/outputs/voice_refs/", 1)[1]).name
            self._serve_file(VOICE_REFS_DIR / fname)
            return

        if path.startswith("/outputs/custom_voices/"):
            fname = Path(path.split("/outputs/custom_voices/", 1)[1]).name
            self._serve_file(CUSTOM_VOICES_DIR / fname)
            return

        if path.startswith("/outputs/"):
            fname = Path(path.split("/outputs/", 1)[1]).name
            self._serve_file(OUTPUTS_DIR / fname)
            return

        if path.startswith("/static/"):
            fname = Path(path.split("/static/", 1)[1]).name
            self._serve_file(STATIC_DIR / fname)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        length = int(self.headers.get("Content-Length", "0"))
        body_raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            payload = json.loads(body_raw)
        except Exception:
            payload = {}

        if path == "/api/brief":
            instruction = payload.get("instruction", "")
            explicit_voice = payload.get("voice_id", "")
            brief_dict = build_brief_from_instruction(instruction, explicit_voice_id=explicit_voice)
            self._send_json({"brief": brief_dict, "voice": get_voice_profile(brief_dict["voice_id"])})
            return

        if path == "/api/voice-preview":
            try:
                voice_id = payload.get("voice_id", "12yo_boy")
                lang = payload.get("lang", "te")
                text = payload.get("text", "")
                ref_path = ensure_voice_reference_audio(voice_id, lang=lang, custom_text=text)
                rel_url = (
                    f"/outputs/custom_voices/{ref_path.name}"
                    if ref_path.parent == CUSTOM_VOICES_DIR
                    else f"/outputs/voice_refs/{ref_path.name}"
                )
                self._send_json({"status": "ok", "audio_url": rel_url, "voice": get_voice_profile(voice_id)})
            except Exception as e:
                self._send_json({"status": "error", "error": str(e)}, status=500)
            return

        if path == "/api/voice-upload":
            try:
                filename = payload.get("filename", "custom_voice.wav")
                voice_name = payload.get("voice_name", "Custom Singer")
                gender_hint = payload.get("gender_hint", "auto")
                b64 = payload.get("audio_base64", "")
                if "," in b64:
                    b64 = b64.split(",", 1)[1]
                audio_bytes = base64.b64decode(b64)
                profile = analyze_and_register_custom_voice(audio_bytes, filename, voice_name, gender_hint=gender_hint)
                self._send_json({"status": "ok", "voice": profile, "voices": get_voice_catalog_list()})
            except Exception as e:
                self._send_json({"status": "error", "error": str(e)}, status=500)
            return

        if path == "/api/remaster":
            try:
                take_slug = payload.get("slug", "Raavayya_Ganapayya_Reference")
                voice_id = payload.get("voice_id", "12yo_boy")
                profile = get_voice_profile(voice_id)
                semitones = float(payload.get("semitone_shift", profile["semitones"]))
                bass_boost = float(payload.get("bass_db", profile["bass_db"]))
                presence_boost = float(payload.get("presence_db", profile["presence_3k_db"]))
                air_boost = float(payload.get("air_db", profile["air_10k_db"]))
                target_lufs = float(payload.get("target_lufs", -14.0))
                use_seedvc = bool(payload.get("use_seedvc", False))

                raw_candidate = OUTPUTS_DIR / f"{take_slug}_Raw.mp3"
                if not raw_candidate.exists():
                    raw_candidate = OUTPUTS_DIR / f"{take_slug}_Original_Pitch_Master.mp3"
                if not raw_candidate.exists():
                    candidates = list(OUTPUTS_DIR.glob("*_Raw.mp3")) or list(OUTPUTS_DIR.glob("*_Original_Pitch_Master.mp3"))
                    if not candidates:
                        raise FileNotFoundError("No base audio found to transform.")
                    raw_candidate = candidates[0]

                remaster_id = datetime.now().strftime("%H%M%S")
                new_slug = f"VoiceStudio_{voice_id}_{remaster_id}"
                source_for_master = raw_candidate

                # Optional Seed-VC zero-shot neural singing voice conversion
                if use_seedvc:
                    ref_audio = ensure_voice_reference_audio(voice_id, payload.get("vocal_language", "te"))
                    svc_tmp = OUTPUTS_DIR / f"{new_slug}_SeedVC.mp3"
                    converted = convert_singing_voice_seedvc(raw_candidate, ref_audio, svc_tmp, semitones)
                    if converted and converted.exists():
                        source_for_master = converted

                out_mp3 = OUTPUTS_DIR / f"{new_slug}_Master.mp3"
                out_wav = OUTPUTS_DIR / f"{new_slug}_Master.wav"

                af_chain = build_ffmpeg_voice_filter(
                    profile,
                    semitone_override=semitones,
                    bass_override=bass_boost,
                    presence_override=presence_boost,
                    air_override=air_boost,
                    target_lufs=target_lufs,
                )

                subprocess.run(
                    [
                        "ffmpeg", "-y", "-i", str(source_for_master),
                        "-af", af_chain,
                        "-ar", "48000", "-ac", "2", "-b:a", "320k",
                        str(out_mp3),
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                subprocess.run(
                    [
                        "ffmpeg", "-y", "-i", str(out_mp3),
                        "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le",
                        str(out_wav),
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

                shutil.copy2(raw_candidate, OUTPUTS_DIR / f"{new_slug}_Raw.mp3")
                orig_cand = OUTPUTS_DIR / f"{take_slug}_Original_Pitch_Master.mp3"
                orig_url = f"/outputs/{orig_cand.name}" if orig_cand.exists() else f"/outputs/{out_mp3.name}"

                short_voice = profile["name"].split("(")[0].strip()
                base_title = payload.get("title", "రావయ్య గణపయ్యా మా ఇంటికి").split("(")[0].strip()
                entry = {
                    "id": new_slug,
                    "slug": new_slug,
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "title": f"{base_title} ({short_voice} · {semitones:+.1f}st)",
                    "brief_text": payload.get("brief_text", f"Sung by {profile['name']} ({semitones:+.1f} st)"),
                    "vocal_language": payload.get("vocal_language", "te"),
                    "bpm": int(payload.get("bpm", 108)),
                    "key_scale": payload.get("key_scale", "D major"),
                    "duration": 57,
                    "voice_id": voice_id,
                    "voice_name": profile["name"],
                    "semitone_shift": semitones,
                    "vocal_preset": profile["name"],
                    "style_prompt": payload.get("style_prompt", ""),
                    "lyrics": payload.get("lyrics", ""),
                    "h3_prompt": payload.get("h3_prompt", ""),
                    "files": {
                        "primary_mp3": f"/outputs/{out_mp3.name}",
                        "original_pitch_mp3": orig_url,
                        "wav_master": f"/outputs/{out_wav.name}",
                        "brief_md": "/outputs/Raavayya_Ganapayya_Reference_Production_Brief.md",
                        "primary_mp3_abs": str(out_mp3),
                        "original_pitch_mp3_abs": str(orig_cand if orig_cand.exists() else out_mp3),
                        "wav_master_abs": str(out_wav),
                    },
                }
                save_to_library(entry)
                self._send_json({"status": "done", "take": entry})
            except Exception as e:
                self._send_json({"status": "error", "error": str(e)}, status=500)
            return

        if path == "/api/generate":
            job_id = uuid.uuid4().hex[:10]
            voice_id = payload.get("voice_id") or "12yo_boy"
            profile = get_voice_profile(voice_id)
            brief = SongBrief(
                title=payload.get("title") or "రావయ్య గణపయ్యా మా ఇంటికి",
                brief_text=payload.get("brief_text", ""),
                vocal_language=payload.get("vocal_language", "te"),
                style_prompt=payload.get("style_prompt", PRESET_BRIEFS["ganesh_chaturthi_telugu_12yo"]["style_prompt"]),
                lyrics=payload.get("lyrics", PRESET_BRIEFS["ganesh_chaturthi_telugu_12yo"]["lyrics"]),
                bpm=int(payload.get("bpm", 108)),
                key_scale=payload.get("key_scale", "D major"),
                time_signature=str(payload.get("time_signature", "4")),
                duration=int(payload.get("duration", 60)),
                inference_steps=int(payload.get("inference_steps", 8)),
                guidance_scale=float(payload.get("guidance_scale", 7.0)),
                seed=str(payload.get("seed", "-1")),
                voice_id=voice_id,
                semitone_shift=float(payload.get("semitone_shift", profile["semitones"])),
                vocal_preset=profile["name"],
                use_voice_ref=bool(payload.get("use_voice_ref", True)),
                use_seedvc=bool(payload.get("use_seedvc", False)),
                space_preference=payload.get("space_preference", "auto"),
                hf_token=payload.get("hf_token", ""),
                h3_prompt=payload.get("h3_prompt", PRESET_BRIEFS["ganesh_chaturthi_telugu_12yo"]["h3_prompt"]),
            )

            with JOBS_LOCK:
                JOBS[job_id] = {
                    "job_id": job_id,
                    "status": "running",
                    "progress": 0.02,
                    "message": f"Initializing ACE-Step v1.5 Turbo + Voice Studio ({profile['name']})...",
                    "take": None,
                    "error": None,
                }

            def worker():
                def on_progress(msg: str, pct: float):
                    with JOBS_LOCK:
                        JOBS[job_id]["message"] = msg
                        JOBS[job_id]["progress"] = round(pct, 3)

                try:
                    entry = generate_song(brief, progress_cb=on_progress)
                    with JOBS_LOCK:
                        JOBS[job_id]["status"] = "done"
                        JOBS[job_id]["progress"] = 1.0
                        JOBS[job_id]["message"] = f"Studio master complete! Sung by {profile['name']}."
                        JOBS[job_id]["take"] = entry
                except Exception as exc:
                    with JOBS_LOCK:
                        JOBS[job_id]["status"] = "error"
                        JOBS[job_id]["error"] = str(exc)
                        JOBS[job_id]["message"] = f"Error: {exc}"

            t = threading.Thread(target=worker, daemon=True)
            t.start()
            self._send_json({"job_id": job_id})
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Endpoint not found")


def run_server(host: str = "127.0.0.1", port: int = 7865):
    bootstrap_initial_take()
    server = ThreadingHTTPServer((host, port), StudioRequestHandler)
    print(f"✨ Indic Song Studio + Voice Studio running at http://{host}:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "7865"))
    run_server(port=port)
