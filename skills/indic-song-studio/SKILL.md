---
name: indic-song-studio
description: Generate, iterate, and master broadcast-grade 90+/100 Indian and multilingual songs with an integrated Voice Studio (17+ singer personas across children, female/male playback, Carnatic classical, Janapada folk, Sufi, elders, choir, plus custom voice cloning) using ACE-Step v1.5 Turbo, Seed-VC zero-shot singing voice conversion, FFmpeg Rubberband/SoxR formant-pitch mastering, and a local Web Studio UI.
---

# Indic Song Studio + Voice Studio (`indic-song-studio`)

Use this skill whenever the user wants to:
1. **Generate a studio-grade song** in **Telugu, Hindi, Tamil, Kannada, Malayalam, Sanskrit, Bengali, Marathi, Punjabi, or English** from a natural-language brief.
2. **Have any singer persona sing the song** — whether the user specifies a *12-year-old boy*, *10-year-old girl*, *6-year-old child*, *Female Playback Singer (Shreya/Chitra style)*, *Male Playback Singer (Sid Sriram/Arijit style)*, *Carnatic Vidushi/Vidwan*, *Telugu Janapada Mass Folk singer*, *Sufi Qawwali singer*, *Grandfather/Grandmother elder*, *Temple Choir*, or uploads a **custom `.wav`/`.mp3` voice sample** for voice cloning.
3. **Launch a local interactive Web App + Voice Studio** (`http://127.0.0.1:7865`) where the user can type a natural-language brief, audition 17+ singer voices, upload a custom reference voice, tweak lyrics/BPM/key/style tags, and re-master or convert any take into any singer's voice in seconds.

---

## Architecture & Pipeline

1. **Natural-Language Brief & Singer Persona Parser (`song_engine.py` + `voice_studio.py`)**
   - Automatically detects language (`te`, `hi`, `ta`, `kn`, `ml`, `sa`, `en`, etc.), tempo (BPM), musical scale/raga, duration, and **who is singing** directly from the user's text brief (`detect_voice_from_brief`).
   - Built-in **17+ Singer Personas** across 4 categories:
     - **Children & Youth:** `12yo_boy`, `10yo_girl`, `6yo_child`, `16yo_teen_boy`, `16yo_teen_girl`
     - **Female Singers:** `female_playback`, `female_carnatic`, `female_folk`, `female_indie`
     - **Male Singers:** `male_playback`, `male_carnatic`, `male_mass_folk`, `male_sufi`, `male_baritone`
     - **Elders & Ensemble:** `elder_grandfather`, `elder_grandmother`, `temple_choir`
     - **Custom Cloned Voices:** `custom_<id>` registered from any `.wav`/`.mp3`/`.m4a` uploaded by the user.

2. **Reference Voice Conditioning & Audition (`voice_studio.py`)**
   - Synthesizes clean, native-script reference vocal phrases via `edge-tts` (`ensure_voice_reference_audio`) or uses the user's uploaded audio clip.
   - Feeds the reference vocal clip (`param_10` / `reference_audio`) + persona-specific vocal tags into **ACE-Step v1.5 Turbo (`acestep-v15-turbo`)** so the diffusion model shapes the singing timbre, phrasing, and register around the chosen singer from the very first pass.

3. **Studio Vocal Tract Mastering & Zero-Shot Singing Voice Conversion (`voice_studio.py`)**
   - **Local Studio Vocal Tract Engine (< 3 seconds):** Uses FFmpeg `librubberband` formant-aware pitch shifting (`rubberband=pitch=...:formant=shifted`), `libsoxr` varispeed resampling, stereo `chorus` ensemble doubling (for choir), 4-band persona-specific vocal EQ, dynamic compression, stereo mud removal, and **EBU R128 loudness normalization (`-14 LUFS`, `-1.0 dBTP`)**.
   - **Cloud Zero-Shot Singing Voice Conversion (`use_seedvc=True`):** Calls `Seed-VC` (`mmwmm/Seed-VC` / `Uniaff/Seed-VC`) with `f0_condition=True` (singing mode) and pitch-preserving synthesis to clone any reference or uploaded voice onto the generated song melody before final EBU R128 mastering.

---

## Quick Start Commands

### 1. Launch the Local Web App (`http://127.0.0.1:7865`)
```bash
/Users/rachanalekkala/Documents/VamshiCreates/AntiGravity/VamshiCreates/indic-song-studio/start.sh
```

### 2. List All Available Singer Voices via CLI
```bash
/Users/rachanalekkala/Documents/VamshiCreates/AntiGravity/VamshiCreates/MiniMax-H3/.venv/bin/python \
  /Users/rachanalekkala/Documents/VamshiCreates/AntiGravity/VamshiCreates/indic-song-studio/cli.py \
  --list-voices
```

### 3. Generate a Song from a Text Brief (Auto-Detects Singer from Brief or `--voice`)
```bash
/Users/rachanalekkala/Documents/VamshiCreates/AntiGravity/VamshiCreates/MiniMax-H3/.venv/bin/python \
  /Users/rachanalekkala/Documents/VamshiCreates/AntiGravity/VamshiCreates/indic-song-studio/cli.py \
  --brief "Generate a Telugu Ganesh Chaturthi song sung by a melodious female playback singer inviting Lord Ganesha home with Nadaswaram and Dholak" \
  --duration 95
```

### 4. Switch / Remaster an Existing Song into Any Singer's Voice Instantly
```bash
/Users/rachanalekkala/Documents/VamshiCreates/AntiGravity/VamshiCreates/MiniMax-H3/.venv/bin/python \
  /Users/rachanalekkala/Documents/VamshiCreates/AntiGravity/VamshiCreates/indic-song-studio/cli.py \
  --remaster "/Users/rachanalekkala/Documents/VamshiCreates/AntiGravity/VamshiCreates/indic-song-studio/outputs/Raavayya_Ganapayya_Original_Pitch_Master.mp3" \
  --voice "female_playback"
```

### 5. Clone a Custom Voice onto a Song
```bash
/Users/rachanalekkala/Documents/VamshiCreates/AntiGravity/VamshiCreates/MiniMax-H3/.venv/bin/python \
  /Users/rachanalekkala/Documents/VamshiCreates/AntiGravity/VamshiCreates/indic-song-studio/cli.py \
  --remaster "/path/to/song.mp3" \
  --custom-voice-file "/path/to/my_singer_sample.wav" \
  --custom-voice-name "My Custom Singer" \
  --use-seedvc
```
