# 🎵 Indic Song Studio + 🎙️ Voice Studio

A locally hosted **Web App, Voice Studio, CLI, and Agent Skill** for generating, iterating, and mastering broadcast-grade (`-14 LUFS`) Indian & multilingual songs in **any singer's voice** from a natural-language brief.

Built on **ACE-Step v1.5 Turbo (`acestep-v15-turbo`)** with reference-audio conditioning, **Seed-VC Zero-Shot Singing Voice Conversion (`f0_condition=True`)**, **Edge-TTS Multilingual Neural Reference Synthesis**, and **FFmpeg `librubberband` + `libsoxr` + EBU R128 Studio Mastering**.

---

## ✨ Key Features

- **🎙️ Integrated Voice Studio (17+ Singer Personas + Custom Voice Cloning)**:
  - **Mention anyone in your brief** — e.g., *"a 12-year-old boy"*, *"a 6-year-old kid"*, *"a melodious female playback singer"*, *"a Carnatic vidwan"*, *"a Telugu Janapada mass folk singer"*, *"a Sufi qawwali singer"*, *"a grandfather"*, or *"a temple choir"* — and the studio automatically detects and configures that singer's voice!
  - **17 Built-in Singer Personas across 4 categories:**
    - **👧 Children & Youth:** `12yo_boy` (12-Year-Old Devotional Boy), `10yo_girl` (10-Year-Old Sweet Girl), `6yo_child` (6-Year-Old Little Kid), `16yo_teen_boy` (16-Year-Old Youth Male), `16yo_teen_girl` (16-Year-Old Youth Female)
    - **👩‍🎤 Female Singers:** `female_playback` (Shreya/Chitra Style), `female_carnatic` (Carnatic Classical Vidushi), `female_folk` (Janapada Folk Female), `female_indie` (Soft Indie Acoustic Female)
    - **👨‍🎤 Male Singers:** `male_playback` (Sid Sriram/Arijit Style), `male_carnatic` (Carnatic Classical Vidwan), `male_mass_folk` (Tollywood Dappu Mass Folk Male), `male_sufi` (Sufi / Soulful High Tenor), `male_baritone` (Deep Cinematic Baritone)
    - **🕉️ Elders & Ensemble:** `elder_grandfather` (Warm Grandfather / Elder), `elder_grandmother` (Devotional Grandmother / Bhajan), `temple_choir` (Grand Temple Group Chorus)
  - **🧬 Custom Voice Cloning (`.wav` / `.mp3` Upload):** Upload any 5–20 second clean voice recording in the Web UI to analyze its fundamental frequency ($f_0$) and clone that voice onto new or existing songs.
  - **🔊 Instant Voice Audition:** Preview every singer persona's reference voice right in the browser before generating or remastering.
- **🗣️ Natural-Language Brief to Full Song Plan**:
  - Automatically parses your text brief into structured **ACE-Step style tags**, **native-script lyrics** (`[Intro]`, `[Verse 1]`, `[Chorus]`, `[Verse 2]`, `[Bridge]`, `[Outro]`), **BPM**, **Musical Scale**, **Language**, and **Voice Studio Singer Persona**.
- **⚡ Instant Voice Switching & Re-Mastering (< 3 seconds locally, or Cloud Seed-VC)**:
  - Pick any previously generated take from your library and click **"Apply Selected Singer Voice & Mastering to Current Audio"** to switch the singer (e.g., from a 12-year-old boy to a Female Playback Singer, Carnatic Vidwan, or Temple Choir) using FFmpeg `librubberband` formant-shifting, `libsoxr` varispeed, custom 4-band vocal tract EQ, and optional **Seed-VC Zero-Shot Singing Voice Conversion**.
- **🌏 10+ Native Indian & Global Languages**:
  - First-class support for **Telugu (`te`)**, **Hindi (`hi`)**, **Tamil (`ta`)**, **Kannada (`kn`)**, **Malayalam (`ml`)**, **Sanskrit (`sa`)**, **Bengali (`bn`)**, **Marathi (`mr`)**, **Punjabi (`pa`)**, and **English (`en`)**.

---

## 🚀 Quick Start

### 1. Launch the Local Web Studio (`http://127.0.0.1:7865`)

```bash
./start.sh
```

Then open **[http://127.0.0.1:7865](http://127.0.0.1:7865)** in your browser.

### 2. Command-Line Interface (`cli.py`)

List all 17+ built-in singer personas:
```bash
python3 cli.py --list-voices
```

Generate a new song from a text brief (auto-detects the singer from your brief or via `--voice`):
```bash
python3 cli.py \
  --brief "Generate a Telugu Ganesh Chaturthi song sung by a melodious female playback singer inviting Lord Ganesha to our house with festive Dholak and Nadaswaram" \
  --duration 95
```

Switch the singer voice on an existing audio file in seconds:
```bash
python3 cli.py \
  --remaster outputs/Raavayya_Ganapayya_Original_Pitch_Master.mp3 \
  --voice female_playback
```

Clone a custom `.wav`/`.mp3` voice onto a song using Seed-VC + Studio Mastering:
```bash
python3 cli.py \
  --remaster outputs/Raavayya_Ganapayya_Original_Pitch_Master.mp3 \
  --custom-voice-file /path/to/my_voice.wav \
  --custom-voice-name "My Custom Singer" \
  --use-seedvc
```

---

## 📁 Repository Structure

```text
indic-song-studio/
├── server.py                         # FastAPI local web server (http://127.0.0.1:7865)
├── song_engine.py                    # Brief parser, ACE-Step v1.5 client & mastering orchestrator
├── voice_studio.py                   # 17+ Singer Personas, Edge-TTS ref synthesis, Rubberband/SoxR & Seed-VC
├── cli.py                            # CLI wrapper for terminal & agent automation
├── start.sh                          # One-command launcher
├── requirements.txt                  # Python dependencies (fastapi, uvicorn, gradio_client, edge-tts)
├── static/
│   └── index.html                    # Interactive Web Studio UI + Voice Studio Selector & Uploader
├── skills/
│   └── indic-song-studio/
│       └── SKILL.md                  # Agent Skill definition
└── outputs/                          # Generated & mastered MP3/WAV tracks + history.json
```
