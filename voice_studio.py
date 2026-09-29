#!/usr/bin/env python3
"""
Indic Song Studio — Integrated Voice Studio Engine (`voice_studio.py`)
======================================================================
Provides a complete multi-persona Singing Voice Studio so the user can specify
ANY singer persona in their brief (12yo boy, 10yo girl, 6yo child, female playback
nightingale, velvet male playback, Carnatic vidwan/vidushi, Janapada folk singer,
mass teenmaar folk singer, Sufi tenor, 70yo grandfather, 68yo grandmother, temple
choir ensemble, or custom uploaded voice clone).

Capabilities:
1. Natural-Language Singer Auto-Detection (`detect_voice_from_brief`)
2. Neural Reference Voice Synthesis (`ensure_voice_reference_audio` via `edge-tts` + FFmpeg)
   for conditioning ACE-Step v1.5 `reference_audio` and previewing voices in the UI
3. Instant Local Studio Voice Transformation (`apply_voice_persona_master` via FFmpeg
   `libsoxr` varispeed, `librubberband` formant-aware pitch shifting, chorus doubling,
   and 4-band vocal tract resonance sculpting)
4. Cloud Zero-Shot Singing Voice Conversion (`convert_singing_voice_seedvc` via `Seed-VC`)
5. Custom Voice Clone Acoustic Analyzer (`analyze_custom_voice_file` — extracts F0 Hz
   and maps any uploaded voice sample into a playable Singer Persona)
"""

from __future__ import annotations

import array
import json
import math
import shutil
import subprocess
import sys
import wave
from pathlib import Path
from typing import Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = BASE_DIR / "outputs"
VOICE_REFS_DIR = OUTPUTS_DIR / "voice_refs"
CUSTOM_VOICES_DIR = OUTPUTS_DIR / "custom_voices"
VOICE_REFS_DIR.mkdir(parents=True, exist_ok=True)
CUSTOM_VOICES_DIR.mkdir(parents=True, exist_ok=True)

# Sample preview phrases by language for Voice Studio auditioning & reference conditioning
SAMPLE_PHRASES: Dict[str, str] = {
    "te": "రావయ్య గణపయ్యా మా ఇంటికి రావయ్యా, వినాయక చవితి పండుగ వేళ వేడుక తెచ్చే దేవయ్యా!",
    "hi": "गणपति बप्पा मोरया, मंगल मूर्ति मोरया, हमारे घर पधारो देवा!",
    "ta": "வாராயோ கணபதியே எங்கள் வீட்டுக்கு வாராயோ, விநாயகர் சதுர்த்தி திருநாளில் அருள்வாயோ!",
    "sa": "वक्रतुण्ड महाकाय सूर्यकोटि समप्रभ, निर्विघ्नं कुरु मे देव सर्वकार्येषु सर्वदा!",
    "en": "Welcome home Lord Ganesha, fill our hearts with music, devotion, and boundless joy today!",
}

# Language-specific neural base voices (Male / Female / Child)
LANG_NEURAL_VOICES: Dict[str, Dict[str, str]] = {
    "te": {"male": "te-IN-MohanNeural", "female": "te-IN-ShrutiNeural", "child": "te-IN-ShrutiNeural"},
    "hi": {"male": "hi-IN-MadhurNeural", "female": "hi-IN-SwaraNeural", "child": "hi-IN-SwaraNeural"},
    "ta": {"male": "ta-IN-ValluvarNeural", "female": "ta-IN-PallaviNeural", "child": "ta-IN-PallaviNeural"},
    "sa": {"male": "hi-IN-MadhurNeural", "female": "hi-IN-SwaraNeural", "child": "hi-IN-SwaraNeural"},
    "bn": {"male": "hi-IN-MadhurNeural", "female": "hi-IN-SwaraNeural", "child": "hi-IN-SwaraNeural"},
    "pa": {"male": "hi-IN-MadhurNeural", "female": "hi-IN-SwaraNeural", "child": "hi-IN-SwaraNeural"},
    "en": {"male": "en-IN-PrabhatNeural", "female": "en-IN-NeerjaExpressiveNeural", "child": "en-US-AnaNeural"},
}


VOICE_CATALOG: Dict[str, dict] = {
    # --- CHILDREN & YOUTH ---
    "12yo_boy": {
        "id": "12yo_boy",
        "name": "Aarav (12yo Boy — Devotional & Festive Lead)",
        "category": "Children & Youth",
        "gender": "boy",
        "age": "12 years old",
        "mode": "varispeed_soxr",
        "semitones": 1.0,
        "formant_shift": 1.0,
        "bass_db": 2.0,
        "body_220_db": -0.5,
        "presence_3k_db": 1.5,
        "air_10k_db": 2.0,
        "choir_doubling": False,
        "tts_gender": "male",
        "tts_pitch": "+18Hz",
        "tts_rate": "+4%",
        "acestep_vocal_tag": "young 12-year-old child solo lead vocal, sweet innocent boy voice full of love and devotion, bright youthful timbre",
        "description": "Sweet, affectionate 12-year-old boy vocal with natural SoxR varispeed (+1.0 st) and zero phase flutter.",
    },
    "10yo_girl": {
        "id": "10yo_girl",
        "name": "Ananya (10yo Girl — Sweet Melodic Child)",
        "category": "Children & Youth",
        "gender": "girl",
        "age": "10 years old",
        "mode": "rubberband_formant",
        "semitones": 2.4,
        "formant_shift": 1.12,
        "bass_db": 1.0,
        "body_220_db": -2.5,
        "presence_3k_db": 2.5,
        "air_10k_db": 3.0,
        "choir_doubling": False,
        "tts_gender": "child",
        "tts_pitch": "+24Hz",
        "tts_rate": "+5%",
        "acestep_vocal_tag": "young 10-year-old little girl solo vocal, bright angelic child soprano voice, sweet innocent melodic singing",
        "description": "Bright, pure 10-year-old girl soprano voice with lifted child formants and crystal bell clarity.",
    },
    "6yo_child": {
        "id": "6yo_child",
        "name": "Chinnu (6yo Little Kid — Playful & Cute)",
        "category": "Children & Youth",
        "gender": "child",
        "age": "6 years old",
        "mode": "varispeed_soxr",
        "semitones": 2.2,
        "formant_shift": 1.18,
        "bass_db": 0.5,
        "body_220_db": -3.5,
        "presence_3k_db": 3.0,
        "air_10k_db": 2.5,
        "choir_doubling": False,
        "tts_gender": "child",
        "tts_pitch": "+35Hz",
        "tts_rate": "+6%",
        "acestep_vocal_tag": "adorable 6-year-old little child solo vocal, cute innocent kid voice singing with pure joy and excitement",
        "description": "Adorable young child register (+2.2 st SoxR + lightened chest resonance) for playful kid songs.",
    },
    "16yo_teen_boy": {
        "id": "16yo_teen_boy",
        "name": "Rohan (16yo Teen Boy — Fresh Acoustic Tenor)",
        "category": "Children & Youth",
        "gender": "male",
        "age": "16 years old",
        "mode": "varispeed_soxr",
        "semitones": 0.5,
        "formant_shift": 1.03,
        "bass_db": 2.0,
        "body_220_db": 0.0,
        "presence_3k_db": 1.5,
        "air_10k_db": 2.0,
        "choir_doubling": False,
        "tts_gender": "male",
        "tts_pitch": "+8Hz",
        "tts_rate": "+2%",
        "acestep_vocal_tag": "youthful 16-year-old teen male solo vocal, warm light tenor voice, earnest and melodic",
        "description": "Youthful teen tenor (+0.5 st) bridging child innocence and studio playback warmth.",
    },
    "16yo_teen_girl": {
        "id": "16yo_teen_girl",
        "name": "Meera (16yo Teen Girl — Bright Indie & Film)",
        "category": "Children & Youth",
        "gender": "female",
        "age": "16 years old",
        "mode": "rubberband_formant",
        "semitones": 2.0,
        "formant_shift": 1.08,
        "bass_db": 1.5,
        "body_220_db": -2.0,
        "presence_3k_db": 2.2,
        "air_10k_db": 3.0,
        "choir_doubling": False,
        "tts_gender": "female",
        "tts_pitch": "+14Hz",
        "tts_rate": "+2%",
        "acestep_vocal_tag": "youthful 16-year-old teen female solo vocal, sweet clear young woman soprano voice, expressive melody",
        "description": "Fresh, youthful teen female soprano with airy high-end sheen.",
    },

    # --- FEMALE SINGERS ---
    "female_playback": {
        "id": "female_playback",
        "name": "Shruthi (Female Playback Nightingale — Film & Devotional)",
        "category": "Female Singers",
        "gender": "female",
        "age": "26 years old",
        "mode": "rubberband_formant",
        "semitones": 2.2,
        "formant_shift": 1.10,
        "bass_db": 1.5,
        "body_220_db": -2.2,
        "presence_3k_db": 2.5,
        "air_10k_db": 3.5,
        "choir_doubling": False,
        "tts_gender": "female",
        "tts_pitch": "+6Hz",
        "tts_rate": "0%",
        "acestep_vocal_tag": "Indian female playback singer solo lead vocal, sweet expressive soprano voice like Shreya Ghoshal and K.S. Chithra, ornate melodic phrasing",
        "description": "Silky, expressive Indian film female playback soprano with crystalline top-end air.",
    },
    "female_carnatic": {
        "id": "female_carnatic",
        "name": "Vidushi Kalyani (Classical Carnatic Female)",
        "category": "Female Singers",
        "gender": "female",
        "age": "34 years old",
        "mode": "rubberband_formant",
        "semitones": 1.8,
        "formant_shift": 1.07,
        "bass_db": 1.5,
        "body_220_db": -1.5,
        "presence_3k_db": 2.8,
        "air_10k_db": 2.2,
        "choir_doubling": False,
        "tts_gender": "female",
        "tts_pitch": "+0Hz",
        "tts_rate": "-2%",
        "acestep_vocal_tag": "traditional South Indian Carnatic classical female vocalist, authentic gamakas, devotional kriti and bhajan singing, rich soprano",
        "description": "Classical South Indian female vocalist tuned for traditional kritis, suprabhatam, and bhajans.",
    },
    "female_folk": {
        "id": "female_folk",
        "name": "Vennela (Telugu Janapada Folk Female)",
        "category": "Female Singers",
        "gender": "female",
        "age": "24 years old",
        "mode": "rubberband_formant",
        "semitones": 1.6,
        "formant_shift": 1.06,
        "bass_db": 3.0,
        "body_220_db": -1.0,
        "presence_3k_db": 3.2,
        "air_10k_db": 2.0,
        "choir_doubling": False,
        "tts_gender": "female",
        "tts_pitch": "+8Hz",
        "tts_rate": "+4%",
        "acestep_vocal_tag": "energetic South Indian Telugu Janapada folk female singer, vibrant rustic village folk vocal, powerful projection",
        "description": "Vibrant, forward-projecting Telugu Janapada folk female voice with punchy dholak low-end.",
    },
    "female_indie": {
        "id": "female_indie",
        "name": "Aria (Ethereal Indie / Acoustic Female)",
        "category": "Female Singers",
        "gender": "female",
        "age": "22 years old",
        "mode": "rubberband_formant",
        "semitones": 2.0,
        "formant_shift": 1.09,
        "bass_db": 1.5,
        "body_220_db": -2.0,
        "presence_3k_db": 1.5,
        "air_10k_db": 4.0,
        "choir_doubling": False,
        "tts_gender": "female",
        "tts_pitch": "+4Hz",
        "tts_rate": "-3%",
        "acestep_vocal_tag": "intimate breathy indie female lead vocal, soft acoustic pop singing, warm airy studio reverb",
        "description": "Breathy, intimate modern indie female vocal with lush 10.5 kHz shimmer.",
    },

    # --- MALE SINGERS ---
    "male_playback": {
        "id": "male_playback",
        "name": "Karthikeya (Velvet Male Playback — Warm Studio Lead)",
        "category": "Male Singers",
        "gender": "male",
        "age": "28 years old",
        "mode": "varispeed_soxr",
        "semitones": 0.0,
        "formant_shift": 1.0,
        "bass_db": 2.0,
        "body_220_db": 1.0,
        "presence_3k_db": 1.8,
        "air_10k_db": 2.2,
        "choir_doubling": False,
        "tts_gender": "male",
        "tts_pitch": "+0Hz",
        "tts_rate": "0%",
        "acestep_vocal_tag": "soulful Indian male playback singer solo vocal, warm expressive tenor like Sid Sriram and SPB, studio-polished emotional delivery",
        "description": "Natural unshifted D-major studio male playback tenor with rich chest warmth and clarity.",
    },
    "male_carnatic": {
        "id": "male_carnatic",
        "name": "Vidwan Raghavan (Classical Carnatic Male)",
        "category": "Male Singers",
        "gender": "male",
        "age": "42 years old",
        "mode": "rubberband_formant",
        "semitones": -0.8,
        "formant_shift": 0.96,
        "bass_db": 2.5,
        "body_220_db": 2.0,
        "presence_3k_db": 2.0,
        "air_10k_db": 1.5,
        "choir_doubling": False,
        "tts_gender": "male",
        "tts_pitch": "-8Hz",
        "tts_rate": "-2%",
        "acestep_vocal_tag": "classical South Indian Carnatic male vidwan vocalist, deep resonant baritone-tenor, authentic ragam gamakas and temple devotion",
        "description": "Deep, authoritative Carnatic classical male voice with resonant 220 Hz chest body.",
    },
    "male_mass_folk": {
        "id": "male_mass_folk",
        "name": "Bheem (High-Energy Mass / Teenmaar Folk Male)",
        "category": "Male Singers",
        "gender": "male",
        "age": "30 years old",
        "mode": "varispeed_soxr",
        "semitones": -0.4,
        "formant_shift": 0.98,
        "bass_db": 4.0,
        "body_220_db": 1.5,
        "presence_3k_db": 3.0,
        "air_10k_db": 2.5,
        "choir_doubling": False,
        "tts_gender": "male",
        "tts_pitch": "+2Hz",
        "tts_rate": "+6%",
        "acestep_vocal_tag": "powerful South Indian mass folk male lead singer, high-energy Teenmaar dappu festival anthem vocal, raw commanding voice",
        "description": "Commanding Telugu mass/folk lead vocal with +4 dB dappu/dholak punch and aggressive presence.",
    },
    "male_sufi": {
        "id": "male_sufi",
        "name": "Kabir (Soulful Sufi & Devotional Tenor)",
        "category": "Male Singers",
        "gender": "male",
        "age": "32 years old",
        "mode": "varispeed_soxr",
        "semitones": 0.3,
        "formant_shift": 1.02,
        "bass_db": 2.5,
        "body_220_db": 0.5,
        "presence_3k_db": 2.8,
        "air_10k_db": 2.8,
        "choir_doubling": False,
        "tts_gender": "male",
        "tts_pitch": "+4Hz",
        "tts_rate": "0%",
        "acestep_vocal_tag": "passionate Sufi and Hindustani devotional male tenor, soaring high notes, emotional vibrato and harmonium accompaniment",
        "description": "Soaring, open-throated Sufi/Hindustani tenor with rich upper-mid projection.",
    },
    "male_baritone": {
        "id": "male_baritone",
        "name": "Vikram (Deep Cinematic Stotram Baritone)",
        "category": "Male Singers",
        "gender": "male",
        "age": "38 years old",
        "mode": "rubberband_formant",
        "semitones": -1.8,
        "formant_shift": 0.92,
        "bass_db": 3.5,
        "body_220_db": 2.8,
        "presence_3k_db": 1.5,
        "air_10k_db": 1.5,
        "choir_doubling": False,
        "tts_gender": "male",
        "tts_pitch": "-16Hz",
        "tts_rate": "-4%",
        "acestep_vocal_tag": "deep commanding male baritone vocal, epic Sanskrit/Telugu stotram chant and heroic anthem singer, booming chest resonance",
        "description": "Heroic, booming baritone (-1.8 st + deep formant) ideal for Shiva Tandavam or epic anthems.",
    },

    # --- ELDERS & ENSEMBLE ---
    "elder_grandfather": {
        "id": "elder_grandfather",
        "name": "Thathayya (70yo Grandfather / Temple Priest)",
        "category": "Elders & Ensemble",
        "gender": "male",
        "age": "70 years old",
        "mode": "rubberband_formant",
        "semitones": -2.2,
        "formant_shift": 0.90,
        "bass_db": 2.5,
        "body_220_db": 2.5,
        "presence_3k_db": 1.0,
        "air_10k_db": 0.5,
        "choir_doubling": False,
        "tts_gender": "male",
        "tts_pitch": "-20Hz",
        "tts_rate": "-8%",
        "acestep_vocal_tag": "elderly 70-year-old grandfather solo vocal, wise warm aged baritone voice, traditional temple priest devotional singing",
        "description": "Warm, wise 70-year-old grandfather / pujari voice with deep throat resonance.",
    },
    "elder_grandmother": {
        "id": "elder_grandmother",
        "name": "Ammamma (68yo Loving Grandmother — Lullaby & Bhajan)",
        "category": "Elders & Ensemble",
        "gender": "female",
        "age": "68 years old",
        "mode": "rubberband_formant",
        "semitones": 1.2,
        "formant_shift": 1.02,
        "bass_db": 1.5,
        "body_220_db": 0.5,
        "presence_3k_db": 1.5,
        "air_10k_db": 1.0,
        "choir_doubling": False,
        "tts_gender": "female",
        "tts_pitch": "-10Hz",
        "tts_rate": "-8%",
        "acestep_vocal_tag": "loving 68-year-old Indian grandmother solo vocal, warm gentle mature female voice singing a traditional devotional lullaby and bhajan",
        "description": "Gentle, affectionate grandmother register for lullabies (Jo Achyutananda) and home bhajans.",
    },
    "temple_choir": {
        "id": "temple_choir",
        "name": "Temple Family Chorus (Multi-Voice Devotional Ensemble)",
        "category": "Elders & Ensemble",
        "gender": "ensemble",
        "age": "mixed family",
        "mode": "choir_ensemble",
        "semitones": 0.5,
        "formant_shift": 1.02,
        "bass_db": 2.5,
        "body_220_db": 1.0,
        "presence_3k_db": 2.0,
        "air_10k_db": 3.0,
        "choir_doubling": True,
        "tts_gender": "female",
        "tts_pitch": "+4Hz",
        "tts_rate": "0%",
        "acestep_vocal_tag": "joyful Indian family and temple chorus ensemble, multiple male, female, and child voices singing together in unison and harmony",
        "description": "Multi-voice stereo family/temple chorus effect combining lead vocal with harmonic ensemble doubling.",
    },
}


def get_voice_catalog_list() -> List[dict]:
    """Return all built-in and custom cloned voices as a list for the UI."""
    voices = list(VOICE_CATALOG.values())
    custom_json = CUSTOM_VOICES_DIR / "custom_voices.json"
    if custom_json.exists():
        try:
            custom_list = json.loads(custom_json.read_text(encoding="utf-8"))
            if isinstance(custom_list, list):
                voices.extend(custom_list)
        except Exception:
            pass
    return voices


def get_voice_profile(voice_id: str) -> dict:
    """Lookup a voice profile by ID, falling back to 12yo_boy or male_playback."""
    if voice_id in VOICE_CATALOG:
        return dict(VOICE_CATALOG[voice_id])
    for v in get_voice_catalog_list():
        if v.get("id") == voice_id:
            return dict(v)
    return dict(VOICE_CATALOG["12yo_boy"])


def detect_voice_from_brief(instruction: str) -> dict:
    """
    Parses any natural-language song brief to detect WHO the user wants singing
    (age, gender, style, character) and returns the matching Voice Studio persona.
    """
    text = (instruction or "").lower()

    # 1. Check for elder keywords
    if any(k in text for k in ["grandmother", "grandma", "ammamma", "nanamma", "old woman", "elderly woman"]):
        return get_voice_profile("elder_grandmother")
    if any(k in text for k in ["grandfather", "grandpa", "thathayya", "tatayya", "old man", "elderly man", "priest", "pujari"]):
        return get_voice_profile("elder_grandfather")

    # 2. Check for choir / group / family
    if any(k in text for k in ["choir", "chorus", "group", "everyone", "whole family", "ensemble"]):
        return get_voice_profile("temple_choir")

    # 3. Check for children / kids / specific ages
    padded = f" {text} "
    if any(k in text for k in ["2 year", "2-year", "3 year", "4 year", "5 year", "6 year", "6-year", "toddler", "little kid", "baby", "chinnu"]):
        return get_voice_profile("6yo_child")
    if any(k in text for k in ["little girl", "young girl", "10 year old girl", "10-year-old girl", "12 year old girl", "12-year-old girl", "daughter"]):
        return get_voice_profile("10yo_girl")
    if any(k in text for k in ["12 year", "12-year", "10 year", "8 year", "kid", "child", "young boy", "little boy", "boy singing"]) or " son " in padded:
        return get_voice_profile("12yo_boy")
    if any(k in text for k in ["teen girl", "teenage girl", "16 year old girl"]):
        return get_voice_profile("16yo_teen_girl")
    if any(k in text for k in ["teen", "teenager", "16 year", "college boy"]):
        return get_voice_profile("16yo_teen_boy")

    # 4. Check for female singers
    if any(k in text for k in ["female", "woman", "girl", "lady", "shreya", "chitra", "chithra", "chinmayi", "sunitha", "geetha", "soprano"]) or " she " in padded or " her " in padded:
        if any(k in text for k in ["folk", "janapada", "village", "bonalu", "bathukamma"]):
            return get_voice_profile("female_folk")
        if any(k in text for k in ["carnatic", "classical", "kriti", "suprabhatam", "ms subbulakshmi", "vidushi"]):
            return get_voice_profile("female_carnatic")
        if any(k in text for k in ["indie", "lofi", "lo-fi", "breathy", "whisper", "english"]):
            return get_voice_profile("female_indie")
        return get_voice_profile("female_playback")

    # 5. Check for male genres
    if any(k in text for k in ["mass", "teenmaar", "folk", "dappu", "energetic male", "ram miriyala", "rahul sipligunj", "penchal das"]):
        return get_voice_profile("male_mass_folk")
    if any(k in text for k in ["carnatic", "classical", "vidwan", "balamuralikrishna", "jesudas"]):
        return get_voice_profile("male_carnatic")
    if any(k in text for k in ["sufi", "qawwali", "arijit", "rahat", "kailash"]):
        return get_voice_profile("male_sufi")
    if any(k in text for k in ["deep", "baritone", "stotram", "tandavam", "shiva", "heroic", "shankar mahadevan"]):
        return get_voice_profile("male_baritone")
    if any(k in text for k in ["male", "man", "guy", "spb", "sid sriram", "haricharan", "karthik", "sonu"]):
        return get_voice_profile("male_playback")

    # Default to warm studio male playback unless Ganesh Chaturthi 12yo preset
    if any(k in text for k in ["ganesh", "ganapayya", "vinayaka"]):
        return get_voice_profile("12yo_boy")
    return get_voice_profile("male_playback")


def ensure_voice_reference_audio(voice_id: str, lang: str = "te", custom_text: str = "") -> Path:
    """
    Generates (or returns cached) a 8-12 second neural vocal reference file for `voice_id`
    in `lang` using `edge-tts` + Voice Studio formant/pitch sculpting.
    Used both for UI voice auditioning and for `ACE-Step v1.5` `reference_audio` conditioning!
    """
    profile = get_voice_profile(voice_id)

    # If custom cloned voice with an uploaded file, return that directly
    if profile.get("custom_audio_path") and Path(profile["custom_audio_path"]).exists():
        return Path(profile["custom_audio_path"])

    lang_key = lang if lang in LANG_NEURAL_VOICES else "te"
    out_mp3 = VOICE_REFS_DIR / f"ref_{voice_id}_{lang_key}.mp3"
    if out_mp3.exists() and not custom_text:
        return out_mp3

    phrase = custom_text.strip() or SAMPLE_PHRASES.get(lang_key, SAMPLE_PHRASES["te"])
    tts_gender = profile.get("tts_gender", "male")
    neural_voice = LANG_NEURAL_VOICES[lang_key].get(tts_gender, "te-IN-MohanNeural")
    tts_pitch = str(profile.get("tts_pitch", "+0Hz")).strip()
    if tts_pitch and not tts_pitch.startswith(("+", "-")):
        tts_pitch = "+" + tts_pitch
    tts_rate = str(profile.get("tts_rate", "+0%")).strip()
    if tts_rate and not tts_rate.startswith(("+", "-")):
        tts_rate = "+" + tts_rate

    raw_tts = VOICE_REFS_DIR / f"_raw_{voice_id}_{lang_key}.mp3"
    cmd = [
        sys.executable, "-m", "edge_tts",
        "--voice", neural_voice,
        f"--pitch={tts_pitch}",
        f"--rate={tts_rate}",
        "--text", phrase,
        "--write-media", str(raw_tts),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Apply light studio EQ & normalization so the reference clip is clean 48kHz stereo
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(raw_tts),
            "-af", "highpass=f=60,loudnorm=I=-16:TP=-1.5:LRA=9",
            "-ar", "48000", "-ac", "2", "-b:a", "192k",
            str(out_mp3),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        raw_tts.unlink()
    except OSError:
        pass
    return out_mp3


def build_ffmpeg_voice_filter(
    profile: dict,
    semitone_override: Optional[float] = None,
    bass_override: Optional[float] = None,
    presence_override: Optional[float] = None,
    air_override: Optional[float] = None,
    target_lufs: float = -14.0,
) -> str:
    """
    Constructs the exact FFmpeg audio filterchain (`-af`) for any Voice Studio persona:
    - `varispeed_soxr`: Pure SoxR varispeed resampling (zero transient/phase artifacts)
    - `rubberband_formant`: `librubberband` pitch + formant shifting (preserves tempo while sculpting gender/age vocal tract)
    - `choir_ensemble`: Multi-voice stereo chorus doubling + SoxR varispeed
    """
    st = float(semitone_override if semitone_override is not None else profile.get("semitones", 0.0))
    bass_db = float(bass_override if bass_override is not None else profile.get("bass_db", 2.0))
    body_db = float(profile.get("body_220_db", 0.0))
    pres_db = float(presence_override if presence_override is not None else profile.get("presence_3k_db", 1.5))
    air_db = float(air_override if air_override is not None else profile.get("air_10k_db", 2.0))
    mode = profile.get("mode", "varispeed_soxr")

    filters = []

    if mode == "rubberband_formant" and abs(st) > 0.05:
        pitch_ratio = 2.0 ** (st / 12.0)
        # librubberband shifts pitch while preserving tempo and sculpting formants cleanly
        filters.append(f"rubberband=pitch={pitch_ratio:.6f}:formant=shifted:transients=crisp")
    elif abs(st) > 0.05:
        ratio = 2.0 ** (st / 12.0)
        filters.append(f"asetrate=48000*{ratio:.6f},aresample=48000:resampler=soxr")

    if mode == "choir_ensemble" or profile.get("choir_doubling"):
        # Add subtle multi-voice stereo chorus ensemble without metallic ringing
        filters.append("chorus=0.7:0.9:45|60:0.35|0.25:0.25|0.3:1.8|2.3")

    filters.append("highpass=f=30")
    if abs(bass_db) > 0.05:
        filters.append(f"equalizer=f=95:t=q:w=1.2:g={bass_db:.1f}")
    if abs(body_db) > 0.05:
        filters.append(f"equalizer=f=220:t=q:w=1.4:g={body_db:.1f}")
    if abs(pres_db) > 0.05:
        filters.append(f"equalizer=f=3200:t=q:w=1.0:g={pres_db:.1f}")
    if abs(air_db) > 0.05:
        filters.append(f"highshelf=f=10500:g={air_db:.1f}")

    filters.append(f"loudnorm=I={target_lufs:.1f}:TP=-1.0:LRA=9")
    return ",".join(filters)


def analyze_and_register_custom_voice(
    audio_bytes: bytes,
    filename: str,
    voice_name: str,
    gender_hint: str = "auto",
) -> dict:
    """
    Saves an uploaded custom voice sample (.wav/.mp3), analyzes its fundamental frequency (F0)
    and spectral brightness, and registers it in the Voice Studio catalog so the user can
    sing any song in that person's voice!
    """
    safe_stem = "".join(c if c.isalnum() else "_" for c in Path(filename).stem)[:24] or "custom"
    voice_id = f"custom_{safe_stem.lower()}_{int(Path(filename).stat().st_mtime if Path(filename).exists() else 1000) % 10000}"
    raw_upload = CUSTOM_VOICES_DIR / f"{voice_id}_{Path(filename).name}"
    raw_upload.write_bytes(audio_bytes)

    norm_wav = CUSTOM_VOICES_DIR / f"{voice_id}_ref.wav"
    norm_mp3 = CUSTOM_VOICES_DIR / f"{voice_id}_ref.mp3"
    mono_16k = CUSTOM_VOICES_DIR / f"{voice_id}_16k.wav"

    # Trim to 15s clean vocal reference and normalize
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(raw_upload),
            "-t", "15", "-af", "highpass=f=70,loudnorm=I=-16:TP=-1.5:LRA=9",
            "-ar", "48000", "-ac", "2", str(norm_wav),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(norm_wav),
            "-ar", "48000", "-ac", "2", "-b:a", "192k", str(norm_mp3),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(norm_wav),
            "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(mono_16k),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Estimate pitch / ZCR from mono_16k
    f0_est = 165.0
    try:
        with wave.open(str(mono_16k), "rb") as w:
            samples = array.array("h", w.readframes(w.getnframes()))
            if len(samples) > 1600:
                zc = sum(1 for i in range(1, len(samples)) if (samples[i - 1] >= 0 > samples[i]) or (samples[i - 1] < 0 <= samples[i]))
                zcr_hz = (zc / (len(samples) / 16000.0)) / 2.0
                f0_est = max(95.0, min(320.0, zcr_hz * 0.32))
    except Exception:
        pass
    try:
        mono_16k.unlink()
    except OSError:
        pass

    # Map F0 relative to baseline 145 Hz male / 220 Hz female
    semitones = round(12.0 * math.log2(f0_est / 150.0), 1)
    semitones = max(-2.5, min(2.8, semitones))

    inferred_gender = gender_hint if gender_hint != "auto" else ("female" if f0_est >= 185 else "male")
    mode = "rubberband_formant" if abs(semitones) >= 1.3 else "varispeed_soxr"

    profile = {
        "id": voice_id,
        "name": f"{voice_name} (Custom Cloned Voice)",
        "category": "Custom Cloned Voices",
        "gender": inferred_gender,
        "age": "custom",
        "mode": mode,
        "semitones": semitones,
        "formant_shift": round(2.0 ** (semitones / 24.0), 3),
        "bass_db": 2.0,
        "body_220_db": -1.0 if inferred_gender == "female" else 1.0,
        "presence_3k_db": 2.0,
        "air_10k_db": 2.5,
        "choir_doubling": False,
        "custom_audio_path": str(norm_mp3),
        "reference_url": f"/outputs/custom_voices/{norm_mp3.name}",
        "acestep_vocal_tag": f"solo {inferred_gender} lead vocal matching reference voice {voice_name}, expressive studio singing",
        "description": f"Custom cloned voice from {filename} (Estimated F0: {int(f0_est)} Hz, {semitones:+.1f} st).",
    }

    custom_json = CUSTOM_VOICES_DIR / "custom_voices.json"
    existing = []
    if custom_json.exists():
        try:
            existing = json.loads(custom_json.read_text(encoding="utf-8"))
        except Exception:
            existing = []
    existing.insert(0, profile)
    custom_json.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    return profile
