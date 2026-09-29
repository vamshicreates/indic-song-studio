#!/usr/bin/env python3
"""
Indic Song Studio — Core Generation, Voice Studio Conditioning & Mastering Engine
=================================================================================
End-to-end wrapper for generating studio-grade Telugu / Indic / multilingual songs
in ANY singer's voice (12yo boy, 10yo girl, 6yo child, female playback nightingale,
velvet male playback, Carnatic vidwan/vidushi, Janapada folk, mass teenmaar folk,
Sufi tenor, 70yo grandfather, 68yo grandmother, temple choir ensemble, or custom
uploaded voice clone) via:
  1. Voice Studio Neural Reference Conditioning (`reference_audio` into ACE-Step v1.5 Turbo)
  2. Optional Zero-Shot Singing Voice Conversion (`Seed-VC` `f0_condition=True`)
  3. FFmpeg `libsoxr` + `librubberband` Formant/Pitch Sculpting & EBU R128 (-14 LUFS) Mastering.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

from gradio_client import Client, handle_file

from voice_studio import (
    VOICE_CATALOG,
    build_ffmpeg_voice_filter,
    detect_voice_from_brief,
    ensure_voice_reference_audio,
    get_voice_catalog_list,
    get_voice_profile,
)

BASE_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = BASE_DIR / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
LIBRARY_JSON = OUTPUTS_DIR / "library.json"

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
        "voice_id": "12yo_boy",
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
            "joyful singer (S1) stands by a decorated wooden peetham beneath a hanging palaveli canopy studded with "
            "small clay lamps and seasonal fruits. The camera pushes in with small amplitude at slow speed as the "
            "singer (S1) folds hands in namaskaram and sings melodically: "
            "<d>[Telugu] రావయ్య గణపయ్యా మా ఇంటికి రావయ్యా, వినాయక చవితి పండుగ వేళ వేడుక తెచ్చే దేవయ్యా!</d> "
            "[Shot 2] At 00:05.000, the camera cuts to a close-up of an eco-friendly clay idol of Lord Ganesha "
            "adorned with a vermilion sindoor tilakam, fresh green garika grass, and a brass plate piled with "
            "steaming white undrallu and kudumulu as (S1) continues singing with heartfelt devotion: "
            "<d>[Telugu] బొజ్జ గణపయ్యా మా బుజ్జి గణపయ్యా, పాలవెల్లి కింద పీఠం వేసాం కొలువుదీర రావయ్యా!</d> "
            "[Shot 3] At 00:10.500, the camera cuts to a medium close-up of (S1) ringing a small brass temple bell "
            "while singing: <d>[Telugu] చిన్ని మూషిక వాహనమెక్కి చిరునవ్వుతో రావయ్యా, చదువుల తండ్రివి నీవే మా తోడుగా ఉండవయ్యా!</d>\n\n"
            "overall_soundscape: A clear brass puja bell rings rhythmically alongside the gentle crackle of "
            "sesame-oil clay lamps and the soft rustle of mango leaves and flower petals in the festive living room.\n\n"
            "non_diegetic_music: Upbeat South Indian devotional ensemble at 108 BPM featuring a joyful mridangam "
            "and dholak groove, bright manjira hand cymbals, warm tanpura drone, and a melodic bamboo flute and "
            "veena accompaniment."
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
    voice_id: str = "12yo_boy"
    semitone_shift: float = 1.0
    vocal_preset: str = "12yo_boy"
    use_voice_ref: bool = True
    use_seedvc: bool = False
    space_preference: str = "auto"
    hf_token: str = ""
    h3_prompt: str = PRESET_BRIEFS["ganesh_chaturthi_telugu_12yo"]["h3_prompt"]


def build_brief_from_instruction(instruction: str, explicit_voice_id: str = "") -> dict:
    """
    Synthesizes a complete SongProductionBrief from a user's natural-language instruction,
    automatically detecting WHO the user wants singing from the Voice Studio catalog.
    """
    text_low = (instruction or "").lower()
    detected_voice = get_voice_profile(explicit_voice_id) if explicit_voice_id else detect_voice_from_brief(instruction)
    voice_id = detected_voice["id"]
    vocal_tag = detected_voice["acestep_vocal_tag"]

    lang = "te"
    lang_name = "Telugu"
    for code, names in [
        ("te", ["telugu", "తెలుగు"]),
        ("hi", ["hindi", "हिंदी", "hindustani"]),
        ("ta", ["tamil", "தமிழ்"]),
        ("sa", ["sanskrit", "संस्कृत", "stotram", "shloka"]),
        ("bn", ["bengali", "বাংলা"]),
        ("pa", ["punjabi", "ਪੰਜਾਬੀ"]),
        ("en", ["english"]),
    ]:
        if any(n in text_low for n in names):
            lang = code
            lang_name = names[0].capitalize()
            break

    bpm = 108
    for token in text_low.split():
        if token.isdigit() and 55 <= int(token) <= 185:
            bpm = int(token)
            break

    if not text_low or any(k in text_low for k in ["ganesh", "ganapathi", "ganapayya", "vinayaka", "chaturthi", "గణప"]):
        base = dict(PRESET_BRIEFS["ganesh_chaturthi_telugu_12yo"])
        if instruction.strip():
            base["brief_text"] = instruction.strip()
        short_singer = detected_voice["name"].split("(")[0].strip()
        base["title"] = f"రావయ్య గణపయ్యా మా ఇంటికి (Raavayya Ganapayya · {short_singer})"
        base["voice_id"] = voice_id
        base["vocal_preset"] = voice_id
        base["semitone_shift"] = float(detected_voice["semitones"])
        base["vocal_language"] = lang
        base["style_prompt"] = (
            f"Indian devotional song, {lang_name} Ganesh Chaturthi festival anthem, "
            f"{vocal_tag}, "
            f"upbeat festive South Indian dholak and mridangam percussion groove, "
            f"manjira hand cymbals, temple bells, bansuri bamboo flute, sitar and veena melody, "
            f"joyful, heartwarming, traditional yet studio-polished, {bpm} BPM, D major"
        )
        return base

    style = (
        f"Indian {lang_name} studio song, {instruction.strip()}, "
        f"{vocal_tag}, "
        f"festive South Indian mridangam and dholak percussion groove, manjira bells, bansuri flute, veena, "
        f"studio-polished, {bpm} BPM, D major"
    )

    return {
        "title": f"{lang_name} Song — {detected_voice['name'].split('(')[0].strip()}",
        "brief_text": instruction.strip(),
        "vocal_language": lang,
        "bpm": bpm,
        "key_scale": "D major",
        "time_signature": "4",
        "duration": 60,
        "voice_id": voice_id,
        "vocal_preset": voice_id,
        "semitone_shift": float(detected_voice["semitones"]),
        "style_prompt": style,
        "lyrics": PRESET_BRIEFS["ganesh_chaturthi_telugu_12yo"]["lyrics"],
        "h3_prompt": PRESET_BRIEFS["ganesh_chaturthi_telugu_12yo"]["h3_prompt"],
    }


def convert_singing_voice_seedvc(
    source_song_mp3: Path,
    target_voice_ref: Path,
    out_mp3: Path,
    semitone_shift: float = 0.0,
) -> Optional[Path]:
    """
    Runs Zero-Shot Singing Voice Conversion (Seed-VC with `f0_condition=True`)
    across available Seed-VC spaces (`mmwmm/Seed-VC`, `Uniaff/Seed-VC`, `Plachta/Seed-VC`).
    """
    for sp, ep in [
        ("mmwmm/Seed-VC", "/predict_1"),
        ("Uniaff/Seed-VC", "/predict"),
        ("Plachta/Seed-VC", "/predict_1"),
    ]:
        try:
            c = Client(sp, verbose=False)
            res = c.predict(
                handle_file(str(source_song_mp3)),
                handle_file(str(target_voice_ref)),
                10,
                1.0,
                0.7,
                True,   # f0_condition = True for singing voice conversion!
                True,   # auto_f0_adjust
                int(round(semitone_shift)),
                api_name=ep,
            )
            full_out = res[1] if isinstance(res, (list, tuple)) and len(res) > 1 else res[0]
            if full_out and Path(full_out).exists():
                shutil.copy2(full_out, out_mp3)
                return out_mp3
        except Exception as e:
            print(f"  [Seed-VC {sp}] notice: {e}", flush=True)
    return None


def master_audio_tracks(
    raw_mp3: Path,
    slug: str,
    voice_id: str = "12yo_boy",
    semitone_shift: Optional[float] = None,
    bass_db: Optional[float] = None,
    presence_db: Optional[float] = None,
    air_db: Optional[float] = None,
) -> Dict[str, Path]:
    """
    Masters the generated song into:
    1. Selected Voice Studio Persona Master (`<slug>_<voice_id>_Master.mp3`)
    2. Original Pitch Studio Master (`<slug>_Original_Pitch_Master.mp3`)
    3. Lossless 48 kHz 24-bit PCM WAV (`<slug>_Master.wav`)
    """
    profile = get_voice_profile(voice_id)

    orig_profile = get_voice_profile("male_playback")
    orig_af = build_ffmpeg_voice_filter(orig_profile, semitone_override=0.0)
    orig_mp3 = OUTPUTS_DIR / f"{slug}_Original_Pitch_Master.mp3"
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(raw_mp3),
            "-af", orig_af,
            "-ar", "48000", "-ac", "2", "-b:a", "320k",
            str(orig_mp3),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    primary_af = build_ffmpeg_voice_filter(
        profile,
        semitone_override=semitone_shift,
        bass_override=bass_db,
        presence_override=presence_db,
        air_override=air_db,
    )
    primary_mp3 = OUTPUTS_DIR / f"{slug}_{voice_id}_Master.mp3"
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(raw_mp3),
            "-af", primary_af,
            "-ar", "48000", "-ac", "2", "-b:a", "320k",
            str(primary_mp3),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

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
    Runs end-to-end song generation conditioned on the selected Voice Studio singer persona
    and masters the output.
    """
    def report(msg: str, pct: float):
        print(f"[{int(pct * 100):3d}%] {msg}", flush=True)
        if progress_cb:
            progress_cb(msg, pct)

    profile = get_voice_profile(brief.voice_id)
    take_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:4]
    slug = f"Song_{take_id}"
    t0 = time.time()

    # Ensure the singer persona tag is present in the style prompt
    style_prompt = brief.style_prompt
    if profile["acestep_vocal_tag"] not in style_prompt:
        style_prompt = f"{profile['acestep_vocal_tag']}, {style_prompt}"

    # Synthesize or locate the Voice Studio neural reference audio for vocal timbre conditioning
    ref_audio_path: Optional[Path] = None
    if brief.use_voice_ref:
        try:
            report(f"Voice Studio: preparing reference vocal embedding for '{profile['name']}'...", 0.05)
            ref_audio_path = ensure_voice_reference_audio(brief.voice_id, brief.vocal_language)
        except Exception as e:
            print(f"Voice ref notice: {e}", flush=True)

    spaces_order = (
        ["ACE-Step/Ace-Step-v1.5", "OnyxMunk/Ace-Step-Munk"]
        if brief.space_preference == "acestep_official"
        else ["OnyxMunk/Ace-Step-Munk", "ACE-Step/Ace-Step-v1.5"]
    )

    raw_audio_path: Optional[Path] = None
    last_error = None
    hf_tok = (brief.hf_token or os.environ.get("HF_TOKEN") or "").strip() or None

    for space_id in spaces_order:
        try:
            report(f"Connecting to {space_id} (Singer: {profile['name']}, lang='{brief.vocal_language}')...", 0.10)
            client = Client(space_id, token=hf_tok, verbose=False)
            ref_arg = handle_file(str(ref_audio_path)) if (ref_audio_path and ref_audio_path.exists()) else None

            if space_id == "OnyxMunk/Ace-Step-Munk":
                job = client.submit(
                    style_prompt,
                    brief.lyrics,
                    float(brief.bpm),
                    brief.key_scale,
                    str(brief.time_signature),
                    brief.vocal_language,
                    float(brief.inference_steps),
                    float(brief.guidance_scale),
                    str(brief.seed).strip() in ("-1", "", "random"),
                    str(brief.seed),
                    ref_arg,
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
                    style_prompt,
                    brief.lyrics,
                    float(brief.bpm),
                    brief.key_scale,
                    str(brief.time_signature),
                    brief.vocal_language,
                    float(brief.inference_steps),
                    float(brief.guidance_scale),
                    str(brief.seed).strip() in ("-1", "", "random"),
                    str(brief.seed),
                    ref_arg,
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

            report(f"Synthesizing song with singer '{profile['name']}' on {space_id}...", 0.18)
            while not job.done():
                st = job.status()
                elapsed = int(time.time() - t0)
                pct = min(0.82, 0.18 + (elapsed / 340.0) * 0.62)
                desc = f"Singing as {profile['name']} on {space_id} ({elapsed}s elapsed)"
                if st.rank is not None and st.queue_size is not None:
                    desc += f" · Queue {st.rank + 1}/{st.queue_size}"
                report(desc, pct)
                time.sleep(4)

            res = job.result()
            if res and isinstance(res[0], str) and Path(res[0]).exists():
                raw_audio_path = Path(res[0])
            else:
                raw_audio_path = _find_recent_gradio_mp3(t0)

            if raw_audio_path and raw_audio_path.exists():
                break
        except Exception as exc:
            last_error = str(exc)
            report(f"Notice: {space_id} returned '{last_error[:80]}' — trying fallback...", 0.15)

    if not raw_audio_path or not raw_audio_path.exists():
        raise RuntimeError(f"All generation backends failed. Last error: {last_error}")

    raw_saved = OUTPUTS_DIR / f"{slug}_Raw.mp3"
    shutil.copy2(raw_audio_path, raw_saved)

    if brief.use_seedvc and ref_audio_path and ref_audio_path.exists():
        report(f"Running Seed-VC Zero-Shot Singing Voice Conversion for '{profile['name']}'...", 0.85)
        svc_out = OUTPUTS_DIR / f"{slug}_SeedVC.mp3"
        converted = convert_singing_voice_seedvc(raw_saved, ref_audio_path, svc_out, brief.semitone_shift)
        if converted and converted.exists():
            raw_saved = converted

    report(f"Mastering Voice Studio persona '{profile['name']}' ({brief.semitone_shift:+.1f} st + EBU R128 -14 LUFS)...", 0.90)
    masters = master_audio_tracks(
        raw_saved,
        slug,
        voice_id=brief.voice_id,
        semitone_shift=brief.semitone_shift,
    )

    brief_md_path = OUTPUTS_DIR / f"{slug}_Production_Brief.md"
    brief_md_content = format_brief_markdown(brief, profile, slug, masters)
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
        "voice_id": brief.voice_id,
        "voice_name": profile["name"],
        "semitone_shift": brief.semitone_shift,
        "vocal_preset": profile["name"],
        "style_prompt": style_prompt,
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
    report(f"Studio master complete! Sung by {profile['name']}.", 1.0)
    return entry


def format_brief_markdown(brief: SongBrief, profile: dict, slug: str, masters: Dict[str, Path]) -> str:
    return f"""# {brief.title}
**Take ID:** `{slug}`  
**Singer Persona (Voice Studio):** `{profile['name']}` (`{brief.voice_id}`)  
**Language:** `{brief.vocal_language}`  
**Tempo & Key:** `{brief.bpm} BPM` · `{brief.key_scale}` · `{brief.time_signature}/4`  
**Vocal Timbre Mastering:** `{profile['mode']}` (`{brief.semitone_shift:+.1f} semitones` + EBU R128 `-14.0 LUFS`)

---

## 1. Style, Singer Persona & Instrumentation Prompt
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
- **Primary Singer Master (MP3, 320 kbps):** `{masters['primary_mp3']}`
- **Original Unshifted Studio Master (MP3, 320 kbps):** `{masters['original_pitch_mp3']}`
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
    parser = argparse.ArgumentParser(description="Indic Song Studio + Voice Studio CLI")
    parser.add_argument("--list-voices", action="store_true", help="List all available Voice Studio singer personas")
    parser.add_argument("--brief", type=str, default="", help="Natural language song brief (mention any singer!)")
    parser.add_argument("--voice", type=str, default="", help="Voice Studio singer ID (e.g., 12yo_boy, female_playback, male_carnatic, elder_grandmother)")
    parser.add_argument("--title", type=str, default="", help="Song title")
    parser.add_argument("--lang", type=str, default="te", help="Vocal language code (te, hi, ta, sa, bn, pa, en)")
    parser.add_argument("--style", type=str, default="", help="Style and instrumentation prompt")
    parser.add_argument("--lyrics-file", type=str, default="", help="Path to text file containing lyrics")
    parser.add_argument("--bpm", type=int, default=108, help="Tempo in BPM")
    parser.add_argument("--key", type=str, default="D major", help="Musical key/scale")
    parser.add_argument("--duration", type=int, default=60, help="Duration in seconds")
    parser.add_argument("--semitones", type=float, default=None, help="Optional semitone override")
    parser.add_argument("--seedvc", action="store_true", help="Also run Seed-VC zero-shot singing voice conversion")
    parser.add_argument("--hf-token", type=str, default="", help="Optional Hugging Face token")
    args = parser.parse_args()

    if args.list_voices:
        for v in get_voice_catalog_list():
            print(f"{v['id']:20s} | {v['category']:20s} | {v['semitones']:+4.1f} st | {v['name']}")
        return

    preset = build_brief_from_instruction(args.brief, explicit_voice_id=args.voice)
    lyrics = preset["lyrics"]
    if args.lyrics_file and Path(args.lyrics_file).exists():
        lyrics = Path(args.lyrics_file).read_text(encoding="utf-8")

    st = args.semitones if args.semitones is not None else preset["semitone_shift"]

    brief = SongBrief(
        title=args.title or preset["title"],
        brief_text=args.brief or preset["brief_text"],
        vocal_language=args.lang or preset["vocal_language"],
        style_prompt=args.style or preset["style_prompt"],
        lyrics=lyrics,
        bpm=args.bpm or preset["bpm"],
        key_scale=args.key or preset["key_scale"],
        duration=args.duration,
        voice_id=preset["voice_id"],
        semitone_shift=float(st),
        vocal_preset=preset["voice_id"],
        use_seedvc=args.seedvc,
        hf_token=args.hf_token,
        h3_prompt=preset["h3_prompt"],
    )
    entry = generate_song(brief)
    print("\n=== GENERATION COMPLETE ===")
    print(json.dumps(entry["files"], indent=2))


if __name__ == "__main__":
    main()
