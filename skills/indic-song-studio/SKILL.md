---
name: indic-song-studio
description: >-
  Generate and master studio-grade (90+/100) Telugu, Indic, and multilingual devotional or film songs
  using ACE-Step v1.5 Turbo native vocal diffusion (`vocal_language='te'`) and FFmpeg SoxR varispeed
  vocal timbre sculpting (including the 12-Year-Old Boy Vocal Master at +1.0 semitone / 1.0595x and
  EBU R128 -14 LUFS mastering). Includes a locally hosted web studio (`http://127.0.0.1:7865`) and CLI wrapper.
---

# Indic Song Studio (`indic-song-studio`)

Use this skill whenever the user asks to generate, remix, or master a **Telugu, Hindi, Tamil, Sanskrit, or Indic devotional/film song**, adjust vocal age/timbre (e.g., **12-year-old boy/child voice**), write a structured **Song Production Brief**, or launch the local **Indic Song Studio** web app.

## Golden Rules (Why This Reaches 90+/100 Quality)

1. **Never use local TTS + PSOLA pitch-shifting for singing.** TTS (`edge-tts` + Praat PSOLA) sounds robotic (~10/100). Always use real end-to-end singing diffusion (`ACE-Step v1.5 Turbo` with native `vocal_language='te'` / `'hi'` / `'ta'` / `'sa'`).
2. **Never use `atempo` time-stretching when sculpting child/12-year-old vocal timbre.** Instead, apply **pure SoxR varispeed resampling** (`asetrate=48000*1.059463,aresample=48000:resampler=soxr`) for `+1.0 semitone` (`12-Year-Old Boy Master`). This shifts both pitch and vocal tract formants together with **zero** phase or percussion transient flutter.
3. **Always master to EBU R128 (`-14.0 LUFS`, `-1.0 dBTP`) at 48 kHz / 320 kbps MP3 & 24-bit WAV** with warm Indian percussion enhancement (`95 Hz +2.0 dB`), vocal presence (`3.2 kHz +1.5 dB`), and temple bell air (`10.5 kHz +2.0 dB`).

---

## 1. Launching the Locally Hosted Web App

To start the interactive **Indic Song Studio** web console on `http://127.0.0.1:7865`:

```bash
./start.sh
# Or directly with Python:
python3 server.py
```

### Web Studio Capabilities
- **1-Sentence Brief Builder**: Enter a natural language prompt (e.g., *"Ganesh Chaturthi song inviting Lord Ganesha to our house, sung by a 12-year-old kid out of love in Telugu"*) and click **Populate Brief & Lyrics**.
- **⚡ Instant Vocal Remaster (2s Local SoxR)**: Modify the vocal age/timbre (`+1.0 st` 12yo Boy Master, `+1.5 st` Young Child, `+0.5 st` Teen, `0.0 st` Original Pitch, or custom `-3.0` to `+3.0 st`) and 3-band EQ in **2 seconds locally** without waiting for cloud diffusion.
- **🎵 Generate New AI Song Take**: Submits the native-script lyrics and style prompt to `ACE-Step v1.5 Turbo` (`OnyxMunk/Ace-Step-Munk` CPU-basic non-ZeroGPU fallback + `ACE-Step/Ace-Step-v1.5` ZeroGPU) and automatically runs the SoxR + EBU R128 mastering chain.
- **A/B Master Switcher & Library**: Compare the **12yo Vocal Master** against the **Original Pitch Master** in real time and download 320 kbps MP3, 24-bit WAV, and the Production Brief Markdown.

---

## 2. Running From the Command Line (CLI Wrapper)

```bash
# Generate with the default Ganesh Chaturthi 12yo Boy Telugu Brief:
python3 song_engine.py --brief "Telugu song on Lord Ganesha for Ganesh Chaturthi sung by a 12-year-old kid" --lang te --semitones 1.0

# Custom lyrics file & tempo:
python3 song_engine.py \
  --title "Raavayya Ganapayya" \
  --lang te \
  --bpm 108 \
  --key "D major" \
  --semitones 1.0 \
  --lyrics-file my_lyrics.txt
```

---

## 3. Standalone FFmpeg SoxR 12-Year-Old Vocal Mastering Command

If you already have a raw AI song take (`raw_take.mp3`) and want to produce the **12-Year-Old Boy Vocal Master (`+1.0 st` SoxR Varispeed)**:

```bash
ffmpeg -y -i raw_take.mp3 \
  -af "asetrate=48000*1.059463,aresample=48000:resampler=soxr,highpass=f=30,equalizer=f=95:t=q:w=1.2:g=2.0,equalizer=f=3200:t=q:w=1.0:g=1.5,highshelf=f=10500:g=2.0,loudnorm=I=-14:TP=-1.0:LRA=9" \
  -ar 48000 -ac 2 -b:a 320k \
  Master_12yo_Boy_Edition.mp3
```
