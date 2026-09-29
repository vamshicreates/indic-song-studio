#!/usr/bin/env python3
"""
CLI wrapper for Indic Song Studio + Voice Studio.
Supports generating new songs from a text brief, listing all 17+ singer personas,
and remastering/converting any existing song into any singer's voice.
"""

import argparse
import json
import sys
from pathlib import Path

from song_engine import (
    OUTPUTS_DIR,
    SongBrief,
    build_brief_from_instruction,
    convert_singing_voice_seedvc,
    generate_song,
    master_audio_tracks,
)
from voice_studio import (
    analyze_and_register_custom_voice,
    ensure_voice_reference_audio,
    get_voice_catalog_list,
    get_voice_profile,
)


def main():
    parser = argparse.ArgumentParser(
        description="Indic Song Studio + Voice Studio CLI — Generate & master songs in any singer's voice."
    )
    parser.add_argument("--list-voices", action="store_true", help="List all available Voice Studio singer personas")
    parser.add_argument("--brief", type=str, default="", help="Natural language song brief (mention language, topic, and singer)")
    parser.add_argument("--title", type=str, default="", help="Override song title")
    parser.add_argument("--language", "--lang", dest="language", type=str, default="", help="Override language code (te, hi, ta, kn, ml, sa, en)")
    parser.add_argument("--voice", type=str, default="", help="Singer voice preset ID (e.g., 12yo_boy, female_playback, male_carnatic, temple_choir)")
    parser.add_argument("--style", type=str, default="", help="Override style prompt")
    parser.add_argument("--lyrics", type=str, default="", help="Override lyrics text")
    parser.add_argument("--lyrics-file", type=str, default="", help="Path to text file containing lyrics")
    parser.add_argument("--bpm", type=int, default=0, help="Override BPM (60-180)")
    parser.add_argument("--key-scale", "--key", dest="key_scale", type=str, default="", help="Override musical key scale (e.g., D major)")
    parser.add_argument("--duration", type=int, default=60, help="Target song duration in seconds (default: 60)")
    parser.add_argument("--seed", type=str, default="-1", help="Random seed (-1 for random)")
    parser.add_argument("--pitch-semitones", "--semitones", dest="semitones", type=float, default=None, help="Manual pitch shift override in semitones")
    parser.add_argument("--remaster", type=str, default="", help="Path to an existing audio file to switch singer voice / remaster")
    parser.add_argument("--custom-voice-file", type=str, default="", help="Path to a custom .wav/.mp3 voice sample to clone")
    parser.add_argument("--custom-voice-name", type=str, default="Custom Singer", help="Display name for custom cloned voice")
    parser.add_argument("--use-seedvc", "--seedvc", dest="use_seedvc", action="store_true", help="Enable Cloud Seed-VC zero-shot singing voice conversion")
    parser.add_argument("--hf-token", type=str, default="", help="Optional Hugging Face token")

    args = parser.parse_args()

    if args.list_voices:
        voices = get_voice_catalog_list()
        print(f"{'ID':<22} | {'Category':<20} | {'Pitch (st)':<10} | {'Name'}")
        print("-" * 95)
        for v in voices:
            print(f"{v['id']:<22} | {v['category']:<20} | {v['semitones']:+6.1f} st  | {v['name']}")
        return

    voice_id = args.voice
    if args.custom_voice_file:
        custom_meta = analyze_and_register_custom_voice(
            uploaded_path=Path(args.custom_voice_file).expanduser().resolve(),
            custom_name=args.custom_voice_name,
        )
        voice_id = custom_meta["id"]
        print(f"[Voice Studio] Registered custom voice: {custom_meta['name']} ({voice_id}, F0={custom_meta.get('detected_f0_hz')} Hz)")

    if args.remaster:
        src = Path(args.remaster).expanduser().resolve()
        if not src.exists():
            print(f"Error: File not found: {src}", file=sys.stderr)
            sys.exit(1)
        vp = voice_id or "12yo_boy"
        profile = get_voice_profile(vp)
        slug = f"{src.stem}_{vp}"
        print(f"[Voice Studio] Transforming '{src.name}' -> Singer='{profile['name']}' ({vp}, use_seedvc={args.use_seedvc})...")

        working_src = src
        if args.use_seedvc:
            ref_wav = ensure_voice_reference_audio(vp, args.language or "te")
            svc_out = OUTPUTS_DIR / f"{slug}_SeedVC.mp3"
            st_val = args.semitones if args.semitones is not None else profile["semitones"]
            converted = convert_singing_voice_seedvc(src, ref_wav, svc_out, semitone_shift=st_val)
            if converted and converted.exists():
                working_src = converted

        masters = master_audio_tracks(
            raw_mp3=working_src,
            slug=slug,
            voice_id=vp,
            semitone_shift=args.semitones,
        )
        print(json.dumps({k: str(v) for k, v in masters.items()}, indent=2))
        return

    if not args.brief and not args.lyrics and not args.lyrics_file:
        parser.print_help()
        sys.exit(1)

    preset = build_brief_from_instruction(args.brief, explicit_voice_id=voice_id)
    lyrics = args.lyrics or preset["lyrics"]
    if args.lyrics_file and Path(args.lyrics_file).exists():
        lyrics = Path(args.lyrics_file).read_text(encoding="utf-8")

    st = args.semitones if args.semitones is not None else preset["semitone_shift"]
    brief = SongBrief(
        title=args.title or preset["title"],
        brief_text=args.brief or preset["brief_text"],
        vocal_language=args.language or preset["vocal_language"],
        style_prompt=args.style or preset["style_prompt"],
        lyrics=lyrics,
        bpm=args.bpm or preset["bpm"],
        key_scale=args.key_scale or preset["key_scale"],
        duration=args.duration or preset["duration"],
        seed=str(args.seed),
        voice_id=preset["voice_id"],
        semitone_shift=float(st),
        vocal_preset=preset["voice_id"],
        use_seedvc=args.use_seedvc,
        hf_token=args.hf_token,
        h3_prompt=preset["h3_prompt"],
    )
    entry = generate_song(brief)
    print(json.dumps(entry, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
