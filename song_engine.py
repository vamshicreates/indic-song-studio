#!/usr/bin/env python3
"""
Indic Song Studio — Core Generation & Mastering Engine
======================================================
End-to-end wrapper for generating studio-grade Telugu / Indic / multilingual songs
via ACE-Step v1.5 Turbo (`vocal_language='te'`) and mastering them with FFmpeg SoxR
varispeed vocal timbre sculpting (12-year-old boy vocal master) + EBU R128 (-14 LUFS).

Can be run as a CLI tool or imported by `server.py`.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

from gradio_client import Client

BASE_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = BASE_DIR / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
LIBRARY_JSON = OUTPUTS_DIR / "library.json"

# Default presets for quick brief generation
PRESET_BRIEFS: Dict[str, dict] = {
    "ganesh_chaturthi_telugu_12yo": {
        "title": "రావయ్య గణపయ్యా మా ఇంటికి (Raavayya Ganapayya Maa Intiki)",
        "brief_text": "Generate a Telugu devotional song on Lord Ganesha for Ganesh Chaturthi — inviting Lord Ganesha to our house, sung by a 12-year-old kid out of love, with 100% Telugu lyrics, proper devotion, and a festive beat.",
        "vocal_language": "te",
        "bpm": 108,
        "key_scale": "D major",
        "time_signature": "4",
        "duration": 60,
        "semitone_shift": 1.0,
        "vocal_preset": "12yo_boy",
        "style_prompt": (
            "Indian devotional song, Telugu Ganesh Chaturthi festival anthem, "
            "young 12-year-old child solo lead vocal, sweet innocent boy voice full of love and devotion, "
            "upbeat festive South Indian dholak and mridangam percussion groove, "
            "manjira hand cymbals, temple bells, bansuri bamboo flute, sitar and veena melody, "
            "joyful, heartwarming, traditional yet studio-polished, 108 BPM, D major"
        ),
        "lyrics": """[Intro]
శ్రీ గణేశాయ నమః! గణపతి బప్పా మోరియా!
మా ఇంటికి రావయ్య గణపయ్యా
ప్రేమతో పిలిచే చిన్ని మనసు ఇదయ్యా

[Chorus]
రావయ్య గణపయ్యా మా ఇంటికి రావయ్యా
వినాయక చవితి పండుగ వేళ వేడుక తెచ్చే దేవయ్యా
బొజ్జ గణపయ్యా మా బుజ్జి గణపయ్యా
పాలవెల్లి కింద పీఠం వేసాం కొలువుదీర రావయ్యా

[Verse 1]
మామిడి తోరణాలు కట్టాము మేమంతా
ముత్యాల ముగ్గులతో వాకిలి నింపామంతా
పచ్చని గరిక పూలతో పూజిస్తాం నిన్నేగా
మమ్మల్ని దీవించ మా ఇంటికి రావయ్యా

[Chorus]
రావయ్య గణపయ్యా మా ఇంటికి రావయ్యా
బొజ్జ గణపయ్యా మా బుజ్జి గణపయ్యా

[Verse 2]
వేడి వేడి ఉండ్రాళ్ళు కుడుములు తెచ్చామయ్యా
బెల్లం పాయసము నైవేద్యం పెట్టామయ్యా
చిన్ని మూషిక వాహనమెక్కి చిరునవ్వుతో రావయ్యా
చదువుల తండ్రివి నీవే మా తోడుగా ఉండవయ్యా

[Outro]
రావయ్య గణపయ్యా మా ఇంటికి రావయ్యా
గౌరీ తనయా గజవదనా మమ్ము బ్రోచే నాథయ్యా
జై బోలో గణేష్ మహారాజ్ కీ జై! గణపతి బప్పా మోరియా!""",
        "h3_prompt": (
            "integrated_multimodal_description: [Shot 1] Live-action, cinematic, a warm medium-wide shot frames the "
            "traditional courtyard doorway of a South Indian Telugu home decorated for Ganesh Chaturthi with fresh "
            "green mango-leaf toranams, marigold garlands, and intricate white muggu (rangoli) on the threshold. A "
            "joyful 12-year-old boy in a festive cream silk dhoti and golden-bordered angavastram (S1) stands by a "
            "decorated wooden peetham beneath a hanging palaveli canopy studded with small clay lamps and seasonal "
            "fruits. The camera pushes in with small amplitude at slow speed as the 12-year-old boy with a bright, "
            "clear, affectionate youthful voice (S1) folds his hands in namaskaram and sings melodically: "
            "<d>[Telugu] రావయ్య గణపయ్యా మా ఇంటికి రావయ్యా, వినాయక చవితి పండుగ వేళ వేడుక తెచ్చే దేవయ్యా!</d> "
            "[Shot 2] At 00:05.000, the camera cuts to a close-up of an eco-friendly clay idol of Lord Ganesha "
            "adorned with a vermilion sindoor tilakam, fresh green garika grass, and a brass plate piled with "
            "steaming white undrallu and kudumulu. Brass oil diyas flicker warmly in the foreground as the "
            "12-year-old boy's hands place a hibiscus flower at Ganesha's feet, and the boy (S1) continues singing "
            "with heartfelt devotion: <d>[Telugu] బొజ్జ గణపయ్యా మా బుజ్జి గణపయ్యా, పాలవెల్లి కింద పీఠం వేసాం కొలువుదీర రావయ్యా!</d> "
            "[Shot 3] At 00:10.500, the camera cuts to a medium close-up of the 12-year-old boy ringing a small "
            "brass temple bell with his right hand while his eyes shine with pure love and devotion in the golden "
            "lamp light, singing: <d>[Telugu] చిన్ని మూషిక వాహనమెక్కి చిరునవ్వుతో రావయ్యా, చదువుల తండ్రివి నీవే మా తోడుగా ఉండవయ్యా!</d>\n\n"
            "overall_soundscape: A clear brass puja bell rings rhythmically alongside the gentle crackle of "
            "sesame-oil clay lamps and the soft rustle of mango leaves and flower petals in the festive living room.\n\n"
            "non_diegetic_music: Upbeat South Indian devotional ensemble at 108 BPM featuring a joyful mridangam "
            "and dholak groove, bright manjira hand cymbals, warm tanpura drone, and a melodic bamboo flute and "
            "veena accompaniment that swells warmly around the child's vocal melody."
        ),
    }
}


@dataclass
class SongBrief:
    title: str = "రావయ్య గణపయ్యా మా ఇంటికి (Raavayya Ganapayya Maa Intiki)"
    brief_text: str = ""
    vocal_language: str = "te"
    style_prompt: str = PRESET_BRIEFS["ganesh_chaturthi_telugu_12yo"]["style_prompt"]
    lyrics: str = PRESET_BRIEFS["ganesh_chaturthi_telugu_12yo"]["lyrics"]
    bpm: int = 108
    key_scale: str = "D major"
    time_signature: str = "4"
    duration: int = 60
    inference_steps: int = 8
    guidance_scale: float = 7.0
    seed: str = "-1"
    semitone_shift: float = 1.0
    vocal_preset: str = "12yo_boy"
    space_preference: str = "auto"
    hf_token: str = ""
    h3_prompt: str = PRESET_BRIEFS["ganesh_chaturthi_telugu_12yo"]["h3_prompt"]


def build_brief_from_instruction(instruction: str) -> dict:
    """
    Synthesizes a complete SongProductionBrief from a user's natural-language instruction.
    Detects language, singer age/persona, tempo, key, and instruments.
    """
    text_low = (instruction or "").lower()

    # Default to the Ganesh Chaturthi Telugu template if Ganesha/Chaturthi/Vinayaka is mentioned or empty
    if not text_low or any(k in text_low for k in ["ganesh", "ganapathi", "ganapayya", "vinayaka", "chaturthi", "గణప"]):
        base = dict(PRESET_BRIEFS["ganesh_chaturthi_telugu_12yo"])
        if instruction.strip():
            base["brief_text"] = instruction.strip()
        # Adjust semitone shift if age is mentioned
        if "2 year" in text_low or "toddler" in text_low or "8 year" in text_low:
            base["semitone_shift"] = 1.5
            base["vocal_preset"] = "young_child"
        elif "adult" in text_low or "original" in text_low:
            base["semitone_shift"] = 0.0
            base["vocal_preset"] = "original"
        else:
            base["semitone_shift"] = 1.0
            base["vocal_preset"] = "12yo_boy"
        return base

    # Generic custom brief synthesis
    lang = "te"
    lang_name = "Telugu"
    for code, names in [
        ("te", ["telugu", "తెలుగు"]),
        ("hi", ["hindi", "हिंदी"]),
        ("ta", ["tamil", "தமிழ்"]),
        ("sa", ["sanskrit", "संस्कृत"]),
        ("en", ["english"]),
    ]:
        if any(n in text_low for n in names):
            lang = code
            lang_name = names[0].capitalize()
            break

    semitone = 1.0 if any(w in text_low for w in ["12", "kid", "child", "boy", "girl", "young"]) else 0.0
    preset = "12yo_boy" if semitone > 0 else "original"
    bpm = 108
    for token in text_low.split():
        if token.isdigit() and 60 <= int(token) <= 180:
            bpm = int(token)
            break

    style = (
        f"Indian {lang_name} studio song, {instruction.strip()}, "
        f"{'young 12-year-old child solo lead vocal, sweet affectionate voice, ' if semitone > 0 else 'expressive studio lead vocal, '}"
        f"festive South Indian mridangam and dholak percussion groove, manjira bells, bansuri flute, veena, "
        f"studio-polished, {bpm} BPM, D major"
    )

    return {
        "title": f"{lang_name} Custom Song — {instruction.strip()[:42]}",
        "brief_text": instruction.strip(),
        "vocal_language": lang,
        "bpm": bpm,
        "key_scale": "D major",
        "time_signature": "4",
        "duration": 60,
        "semitone_shift": semitone,
        "vocal_preset": preset,
        "style_prompt": style,
        "lyrics": PRESET_BRIEFS["ganesh_chaturthi_telugu_12yo"]["lyrics"],
        "h3_prompt": PRESET_BRIEFS["ganesh_chaturthi_telugu_12yo"]["h3_prompt"],
    }


def master_audio_tracks(
    raw_mp3: Path,
    slug: str,
    semitone_shift: float = 1.0,
) -> Dict[str, Path]:
    """
    Runs the two-stage FFmpeg SoxR + EBU R128 (-14 LUFS, -1.0 dBTP) mastering chain:
    1. Primary Master (with SoxR varispeed semitone shift for 12-year-old vocal timbre if semitone_shift != 0)
    2. Original Pitch Studio Master (0 semitone shift, warm D-major studio master)
    3. Lossless 48 kHz 24-bit PCM WAV of the Primary Master
    """
    eq_loudnorm = (
        "highpass=f=30,"
        "equalizer=f=95:t=q:w=1.2:g=2.0,"
        "equalizer=f=3200:t=q:w=1.0:g=1.5,"
        "highshelf=f=10500:g=2.0,"
        "loudnorm=I=-14:TP=-1.0:LRA=9"
    )

    orig_mp3 = OUTPUTS_DIR / f"{slug}_Original_Pitch_Master.mp3"
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(raw_mp3),
            "-af", eq_loudnorm,
            "-ar", "48000", "-ac", "2", "-b:a", "320k",
            str(orig_mp3),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    primary_mp3 = OUTPUTS_DIR / f"{slug}_12yo_Master.mp3"
    if abs(semitone_shift) > 0.01:
        ratio = 2.0 ** (float(semitone_shift) / 12.0)
        af_chain = f"asetrate=48000*{ratio:.6f},aresample=48000:resampler=soxr,{eq_loudnorm}"
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(raw_mp3),
                "-af", af_chain,
                "-ar", "48000", "-ac", "2", "-b:a", "320k",
                str(primary_mp3),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        shutil.copy2(orig_mp3, primary_mp3)

    wav_master = OUTPUTS_DIR / f"{slug}_Master.wav"
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(primary_mp3),
            "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le",
            str(wav_master),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    return {
        "primary_mp3": primary_mp3,
        "original_pitch_mp3": orig_mp3,
        "wav_master": wav_master,
    }


def _find_recent_gradio_mp3(since_ts: float) -> Optional[Path]:
    """Fallback scan of Gradio temp directory if generator yields UI update dict at final step."""
    import tempfile
    tmp_root = Path(tempfile.gettempdir()) / "gradio"
    if not tmp_root.exists():
        return None
    candidates = []
    for p in tmp_root.rglob("*.mp3"):
        try:
            mtime = p.stat().st_mtime
            if mtime >= since_ts - 5:
                candidates.append((mtime, p))
        except OSError:
            pass
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]
    return None


def generate_song(
    brief: SongBrief,
    progress_cb: Optional[Callable[[str, float], None]] = None,
) -> dict:
    """
    Runs end-to-end song generation on ACE-Step v1.5 Turbo and masters the output.
    """
    def report(msg: str, pct: float):
        print(f"[{int(pct * 100):3d}%] {msg}", flush=True)
        if progress_cb:
            progress_cb(msg, pct)

    take_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:4]
    slug = f"Song_{take_id}"
    t0 = time.time()

    spaces_order = []
    if brief.space_preference == "acestep_official":
        spaces_order = ["ACE-Step/Ace-Step-v1.5", "OnyxMunk/Ace-Step-Munk"]
    else:
        spaces_order = ["OnyxMunk/Ace-Step-Munk", "ACE-Step/Ace-Step-v1.5"]

    raw_audio_path: Optional[Path] = None
    last_error = None
    hf_tok = (brief.hf_token or os.environ.get("HF_TOKEN") or "").strip() or None

    for space_id in spaces_order:
        try:
            report(f"Connecting to {space_id} (ACE-Step v1.5 Turbo, lang='{brief.vocal_language}')...", 0.08)
            client = Client(space_id, token=hf_tok, verbose=False)

            if space_id == "OnyxMunk/Ace-Step-Munk":
                job = client.submit(
                    brief.style_prompt,
                    brief.lyrics,
                    float(brief.bpm),
                    brief.key_scale,
                    str(brief.time_signature),
                    brief.vocal_language,
                    float(brief.inference_steps),
                    float(brief.guidance_scale),
                    str(brief.seed).strip() in ("-1", "", "random"),
                    str(brief.seed),
                    None,
                    float(brief.duration),
                    1,
                    None,
                    "",
                    0.0,
                    -1,
                    "Fill the audio semantic mask based on the given conditions:",
                    1.0,
                    0.0,
                    "text2music",
                    False,
                    0.0,
                    1.0,
                    3.0,
                    "ode",
                    "",
                    "mp3",
                    0.85,
                    False,
                    2.0,
                    0,
                    0.9,
                    "NO USER INPUT",
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    0.5,
                    8,
                    "vocals",
                    [],
                    True,
                    -1.0,
                    0.0,
                    1.0,
                    False,
                    api_name="/generation_wrapper",
                )
            else:
                job = client.submit(
                    "acestep-v15-turbo",
                    "custom",
                    "",
                    brief.vocal_language,
                    brief.style_prompt,
                    brief.lyrics,
                    float(brief.bpm),
                    brief.key_scale,
                    str(brief.time_signature),
                    brief.vocal_language,
                    float(brief.inference_steps),
                    float(brief.guidance_scale),
                    str(brief.seed).strip() in ("-1", "", "random"),
                    str(brief.seed),
                    None,
                    float(brief.duration),
                    1,
                    None,
                    "",
                    0.0,
                    -1,
                    "Fill the audio semantic mask based on the given conditions:",
                    1.0,
                    "text2music",
                    False,
                    0.0,
                    1.0,
                    3.0,
                    "ode",
                    "",
                    "mp3",
                    0.85,
                    False,
                    2.0,
                    0,
                    0.9,
                    "NO USER INPUT",
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    0.5,
                    8,
                    "vocals",
                    [],
                    False,
                    api_name="/generation_wrapper",
                )

            report(f"Diffusion job submitted to {space_id}. Synthesizing vocals & instrumentation...", 0.18)
            while not job.done():
                st = job.status()
                elapsed = int(time.time() - t0)
                pct = min(0.82, 0.18 + (elapsed / 340.0) * 0.62)
                desc = f"Synthesizing on {space_id} ({elapsed}s elapsed)"
                if st.rank is not None and st.queue_size is not None:
                    desc += f" · Queue {st.rank + 1}/{st.queue_size}"
                report(desc, pct)
                time.sleep(4)

            # Check outputs
            res = job.result()
            if res and isinstance(res[0], str) and Path(res[0]).exists():
                raw_audio_path = Path(res[0])
            else:
                raw_audio_path = _find_recent_gradio_mp3(t0)

            if raw_audio_path and raw_audio_path.exists():
                break
        except Exception as exc:
            last_error = str(exc)
            report(f"Notice: {space_id} returned '{last_error[:90]}' — trying next backend...", 0.15)

    if not raw_audio_path or not raw_audio_path.exists():
        raise RuntimeError(f"All generation backends failed. Last error: {last_error}")

    raw_saved = OUTPUTS_DIR / f"{slug}_Raw.mp3"
    shutil.copy2(raw_audio_path, raw_saved)

    report("Mastering audio (SoxR 12yo Vocal Timbre Varispeed + EBU R128 -14 LUFS)...", 0.88)
    masters = master_audio_tracks(raw_saved, slug, semitone_shift=brief.semitone_shift)

    # Save Markdown production brief
    brief_md_path = OUTPUTS_DIR / f"{slug}_Production_Brief.md"
    brief_md_content = format_brief_markdown(brief, slug, masters)
    brief_md_path.write_text(brief_md_content, encoding="utf-8")

    entry = {
        "id": take_id,
        "slug": slug,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "title": brief.title,
        "brief_text": brief.brief_text,
        "vocal_language": brief.vocal_language,
        "bpm": brief.bpm,
        "key_scale": brief.key_scale,
        "duration": brief.duration,
        "semitone_shift": brief.semitone_shift,
        "vocal_preset": brief.vocal_preset,
        "style_prompt": brief.style_prompt,
        "lyrics": brief.lyrics,
        "h3_prompt": brief.h3_prompt,
        "files": {
            "primary_mp3": f"/outputs/{masters['primary_mp3'].name}",
            "original_pitch_mp3": f"/outputs/{masters['original_pitch_mp3'].name}",
            "wav_master": f"/outputs/{masters['wav_master'].name}",
            "brief_md": f"/outputs/{brief_md_path.name}",
            "primary_mp3_abs": str(masters["primary_mp3"]),
            "original_pitch_mp3_abs": str(masters["original_pitch_mp3"]),
            "wav_master_abs": str(masters["wav_master"]),
        },
    }
    save_to_library(entry)
    report("Studio master complete! Ready for playback & download.", 1.0)
    return entry


def format_brief_markdown(brief: SongBrief, slug: str, masters: Dict[str, Path]) -> str:
    return f"""# {brief.title}
**Take ID:** `{slug}`  
**Language:** `{brief.vocal_language}`  
**Tempo & Key:** `{brief.bpm} BPM` · `{brief.key_scale}` · `{brief.time_signature}/4`  
**Vocal Timbre Mastering:** `{brief.vocal_preset}` (`{brief.semitone_shift:+.1f} semitones` SoxR Varispeed + EBU R128 `-14.0 LUFS`)

---

## 1. Style & Instrumentation Prompt
```text
{brief.style_prompt}
```

## 2. Complete Lyrics
```text
{brief.lyrics}
```

## 3. MiniMax-H3 Multimodal Video Prompt
```text
{brief.h3_prompt}
```

## 4. Exported Master Files
- **Primary Studio Master (MP3, 320 kbps):** `{masters['primary_mp3']}`
- **Original Pitch Studio Master (MP3, 320 kbps):** `{masters['original_pitch_mp3']}`
- **Lossless Studio Master (WAV, 48 kHz 24-bit):** `{masters['wav_master']}`
"""


def load_library() -> List[dict]:
    if not LIBRARY_JSON.exists():
        return []
    try:
        return json.loads(LIBRARY_JSON.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_to_library(entry: dict) -> None:
    items = load_library()
    items.insert(0, entry)
    LIBRARY_JSON.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Indic Song Studio CLI — Generate & Master Studio AI Songs")
    parser.add_argument("--brief", type=str, default="", help="Natural language song brief")
    parser.add_argument("--title", type=str, default="", help="Song title")
    parser.add_argument("--lang", type=str, default="te", help="Vocal language code (e.g., te, hi, ta, sa, en)")
    parser.add_argument("--style", type=str, default="", help="Style and instrumentation prompt")
    parser.add_argument("--lyrics-file", type=str, default="", help="Path to text file containing lyrics")
    parser.add_argument("--bpm", type=int, default=108, help="Tempo in BPM")
    parser.add_argument("--key", type=str, default="D major", help="Musical key/scale")
    parser.add_argument("--duration", type=int, default=60, help="Duration in seconds")
    parser.add_argument("--semitones", type=float, default=1.0, help="SoxR varispeed semitone shift (+1.0 = 12yo boy)")
    parser.add_argument("--hf-token", type=str, default="", help="Optional Hugging Face token")
    args = parser.parse_args()

    preset = build_brief_from_instruction(args.brief)
    lyrics = preset["lyrics"]
    if args.lyrics_file and Path(args.lyrics_file).exists():
        lyrics = Path(args.lyrics_file).read_text(encoding="utf-8")

    brief = SongBrief(
        title=args.title or preset["title"],
        brief_text=args.brief or preset["brief_text"],
        vocal_language=args.lang or preset["vocal_language"],
        style_prompt=args.style or preset["style_prompt"],
        lyrics=lyrics,
        bpm=args.bpm or preset["bpm"],
        key_scale=args.key or preset["key_scale"],
        duration=args.duration,
        semitone_shift=args.semitones,
        hf_token=args.hf_token,
        h3_prompt=preset["h3_prompt"],
    )
    entry = generate_song(brief)
    print("\n=== GENERATION COMPLETE ===")
    print(json.dumps(entry["files"], indent=2))


if __name__ == "__main__":
    main()
