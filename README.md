# 🎵 Indic Song Studio (`indic-song-studio`)

**Local Web Studio, CLI Wrapper & AI Agent Skill for Studio-Grade (90+/100) Telugu, Indic & Multilingual Song Generation + SoxR Vocal Timbre Mastering**

![Status](https://img.shields.io/badge/Audio_Standard-48kHz_%2F_320kbps_MP3_%26_24bit_WAV-D4A853)
![Loudness](https://img.shields.io/badge/Mastering-EBU_R128_-14_LUFS-E0533C)
![Engine](https://img.shields.io/badge/Engine-ACE--Step_v1.5_Turbo_%2B_FFmpeg_SoxR-4CAF7D)

---

## ✨ Overview

**Indic Song Studio** turns a natural-language song brief into a studio-mastered song with native Indic script lyrics (`vocal_language='te'` Telugu, `'hi'` Hindi, `'ta'` Tamil, `'sa'` Sanskrit, `'bn'` Bengali, `'pa'` Punjabi, `'en'` English) and a real-time **FFmpeg SoxR Vocal Timbre Mastering Console**.

It includes:
1. **Locally Hosted Web App (`http://127.0.0.1:7865`)**:
   - **1-Sentence Song Brief Builder**: Describe the occasion, singer age/persona, language, and beat to auto-populate the complete production brief, native lyrics, and MiniMax-H3 video prompt.
   - **⚡ Instant Vocal Timbre Remaster (2s Local SoxR)**: Modify the vocal age/timbre (`+1.0 st` **12-Year-Old Boy Master**, `+1.5 st` Young Child, `+0.5 st` Teen, `0.0 st` Original Studio Pitch, or custom `-3.0` to `+3.0 st`) and 3-band EQ (`95 Hz` Dholak/Mridangam warmth, `3.2 kHz` Vocal Presence, `10.5 kHz` Temple Bell shimmer) in **2 seconds locally**—so you can tweak and compare versions over and over without waiting for cloud generation.
   - **🎵 Full Cloud AI Song Generation**: Submits native-script lyrics and instrumentation prompts to **ACE-Step v1.5 Turbo** (with automatic fallback between non-ZeroGPU CPU/GPU spaces and ZeroGPU spaces) and automatically runs the SoxR + EBU R128 (`-14.0 LUFS`) mastering pipeline.
   - **Real-Time A/B Master Switcher**: Toggle seamlessly between **A: 12yo Vocal Master (320 kbps MP3)** and **B: Original Pitch Master (D Major)** during playback.
2. **CLI Wrapper (`song_engine.py`)**: Run full song generations or remasters from any terminal or script.
3. **Agent Skill (`skills/indic-song-studio/SKILL.md`)**: Ready-to-install skill for Google Antigravity, Claude Code, and Cursor.

---

## 🚀 Quick Start (Local Web App)

### Prerequisites
- Python 3.10+
- `ffmpeg` (with `libsoxr` and `libmp3lame`)

### 1. Clone & Launch
```bash
git clone https://github.com/vamshicreates/indic-song-studio.git
cd indic-song-studio
chmod +x start.sh
./start.sh
```

Then open **`http://127.0.0.1:7865`** in your browser.

---

## 🎧 Included Reference Production: *రావయ్య గణపయ్యా మా ఇంటికి (Raavayya Ganapayya Maa Intiki)*

Pre-loaded in `outputs/`:
- **`outputs/Raavayya_Ganapayya_Reference_12yo_Master.mp3`** — **12-Year-Old Boy Vocal Master** (`+1.0 st` / `1.059463x` SoxR Varispeed, 48 kHz, 320 kbps MP3, `-14.0 LUFS`)
- **`outputs/Raavayya_Ganapayya_Reference_Original_Pitch_Master.mp3`** — **Original Studio Pitch Master** (`0.0 st`, D Major, 108 BPM, 48 kHz, 320 kbps MP3, `-14.0 LUFS`)
- **`outputs/Raavayya_Ganapayya_Reference_Production_Brief.md`** — Full Telugu lyrics, musical architecture, and MiniMax-H3 multimodal prompt.

---

## 🛠️ CLI Usage

```bash
# Generate from a natural-language brief:
python3 song_engine.py \
  --brief "Telugu devotional song on Lord Ganesha for Ganesh Chaturthi sung by a 12-year-old kid out of love" \
  --lang te \
  --bpm 108 \
  --key "D major" \
  --semitones 1.0
```

---

## 🧩 Installing as an Agent Skill (Antigravity / Claude Code)

Copy `skills/indic-song-studio` into your workspace `.agents/skills/` or global `~/.gemini/config/skills/` directory:

```bash
cp -R skills/indic-song-studio ~/.gemini/config/skills/
```
