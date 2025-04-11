import torch
import os
from yt_dlp import YoutubeDL
import whisper
import torch
import time
import os
import ffmpeg
import requests
import json
import re
import streamlit as st

def file_exist(path):
    """Check if file exists and is not locked."""
    if os.path.exists(path):
        try:
            with open(path, 'rb'):
                return True
        except PermissionError:
            return False
    return False

def download_audio(url):
    """Download audio as MP3 from a YouTube URL and save it to 'downloads/' folder."""
    downloads_dir = os.path.join('.', 'downloads')
    os.makedirs(downloads_dir, exist_ok=True)

    audio_path = os.path.join(downloads_dir, 'audio.%(ext)s')
    final_audio_file = os.path.join(downloads_dir, 'audio.mp3')

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': audio_path,
        'postprocessors': [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }
        ],
        'noplaylist': True,
        'quiet': False,
        'windowsfilenames': True
    }

    with YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([url])
        except Exception as e:
            st.toast(f"Audio download failed: {e}")
            return False

    return file_exist(final_audio_file)



def download_video(url):
    """Download YouTube video as MP4 and save in ./downloads."""
    downloads_dir = os.path.join('.', 'downloads')
    os.makedirs(downloads_dir, exist_ok=True)

    final_video_file = os.path.join(downloads_dir, 'video.mp4')
    video_outtmpl = os.path.join(downloads_dir, 'video.%(ext)s')

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': video_outtmpl,
        'merge_output_format': 'mp4',
        'noplaylist': True,
        'quiet': False,
        'windowsfilenames': True
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Wait for final .mp4 file to be unlocked and ready
        timeout = 80
        while timeout > 0:
            if file_exist(final_video_file):
                return True
            time.sleep(0.5)
            timeout -= 0.5

        st.toast("⚠️ Timeout: final video file still locked or missing.")
        return False

    except Exception as e:
        st.toast(f"❌ Video download failed: {e}")
        return False


def download_subtitles(url):
    """Download English subtitles from a YouTube URL and save them as a clean transcript."""
    downloads_dir = os.path.join('.', 'downloads')
    os.makedirs(downloads_dir, exist_ok=True)

    transcript_path = os.path.join(downloads_dir, 'transcript.txt')

    ydl_opts = {
        'writesubtitles': True,
        'subtitleslangs': ['en'],
        'skip_download': True,
        'outtmpl': os.path.join(downloads_dir, 'sub.%(ext)s'),
        'quiet': True
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        # Check for English subtitles
        if 'subtitles' in info and 'en' in info['subtitles']:
            # Find the downloaded .vtt file
            subtitle_file = None
            for f in os.listdir(downloads_dir):
                if f.endswith('.vtt'):
                    subtitle_file = os.path.join(downloads_dir, f)
                    break

            if subtitle_file:
                with open(subtitle_file, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()

                # Write cleaned transcript (skip first few header lines)
                with open(transcript_path, 'w', errors='ignore') as f:
                    # Skip WEBVTT header (first 3 lines typically)
                    for line in lines[3:]:
                        f.write(line)

                os.remove(subtitle_file)
                return True

        st.toast("Subtitles not available in English.")
        return False

    except Exception as e:
        st.toast(f"Subtitle download failed: {e}")
        return False
            

def _format_timestamp(seconds):
    """Convert seconds to HH:MM:SS.mmm format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"

def transcribe_audio(audio_file):
    """Transcribe audio using Whisper and save transcript in .vtt-like format."""
    downloads_dir = os.path.join('.', 'downloads')
    os.makedirs(downloads_dir, exist_ok=True)

    transcript_path = os.path.join(downloads_dir, 'transcript.txt')

    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = whisper.load_model("tiny").to(device)
    except Exception as e:
        st.toast(f"Model loading failed: {e}")
        return False

    try:
        result = model.transcribe(audio_file, verbose=None)
        with open(transcript_path, 'w', encoding='utf-8') as f:
            for segment in result["segments"]:
                start = _format_timestamp(segment['start'])
                end = _format_timestamp(segment['end'])
                text = segment['text'].strip()
                f.write(f"{start} --> {end}\n{text}\n\n")

        return True
    except Exception as e:
        st.toast(f"Transcription failed: {e}")
        return False


def fetch_hooky_timestamps(top_n=3, clip_length=30, clip_type="educational", transcript_path='downloads/transcript.txt'):
    if not os.path.exists(transcript_path):
        st.toast(f"Transcript file not found: {transcript_path}")
        return {}
    with open(transcript_path, 'r', encoding='utf-8', errors='ignore') as file:
        transcript_content = file.read().strip()

    prompt = f"""
    Analyze the following transcript and extract exactly the top {top_n} most engaging, hooky segments optimized for {clip_type} TikTok/Instagram Reels. Focus on parts that grab attention and keep viewers watching.

    Rules:
    - Each segment must be exactly {clip_length} seconds long. Trim or extend slightly to fit the duration while keeping the content coherent and impactful.
    - Output must be raw JSON only, with no markdown, no code blocks, no explanations, and no extra text.
    - Do not enclose the output in triple backticks (```) or any markers.

    Output Format (raw JSON only):
    {{
        "Segment 1": {{
            "Start Timestamp": "HH:MM:SS.mmm",
            "End Timestamp": "HH:MM:SS.mmm",
            'caption': 'Caption for Segment 1',
            "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3", "#hashtag4", "#hashtag5"]
        }},
        "Segment 2": {{
            "Start Timestamp": "HH:MM:SS.mmm",
            "End Timestamp": "HH:MM:SS.mmm",
            'caption': 'Caption for Segment 2',
            "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3", "#hashtag4", "#hashtag5"]
        }}
    }}

    Transcript:
    {transcript_content}
    """

    headers = {"Content-Type": "application/json"}
    payload = {
        "messages": [
            {
                "role": "system",
                "content": "You are an expert video editor specializing in short-form social media content."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    pollinations_urls = [
        "https://text.pollinations.ai",
        "https://text.pollinations.ai/openai"
    ]

    for i, url in enumerate(pollinations_urls):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()

            if i == 0:
                return result
            else:
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                if content:
                    segments = json.loads(content)
                    return segments
        except requests.exceptions.RequestException as e:
            st.toast(f"Request error with URL {url}: {e}")
        except json.JSONDecodeError as e:
            st.toast(f"JSON decode error from URL {url}: {e}")
        except Exception as e:
            st.toast(f"Unexpected error with URL {url}: {e}")

    st.toast("All models failed to return valid data.")
    return {}


def clip_video(response, video_file, clip_dir='clips'):
    if response is None:
        raise ValueError("Response is None.")

    if not os.path.exists(video_file):
        raise FileNotFoundError(f"Input video file not found: {video_file}")

    os.makedirs(clip_dir, exist_ok=True)

    for row in response:
        start = response[row].get('Start Timestamp')
        end = response[row].get('End Timestamp')
        clip_number = re.findall(r'([0-9]+)', row)[0]
        output_file = os.path.join(clip_dir, f"clip_{clip_number}.mp4")

        # Validate timestamps
        if not start or not end:
            st.toast(f"Skipping segment {row}: invalid timestamps")
            continue

            # Duration calculation
        def to_seconds(t):
            h, m, s = t.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)

        duration = to_seconds(end) - to_seconds(start)

        try:
            (
                ffmpeg
                .input(video_file, ss=start, t=duration)
                .output(
                    output_file,
                    vf='scale=-1:1920,crop=1080:1920,eq=contrast=1.1:brightness=0.03:saturation=1.15,fps=30,format=yuv420p',
                    acodec='aac',
                    vcodec='libx264',
                    crf=23,
                    preset='slow',
                    movflags='+faststart',
                    y=None
                )
                .global_args('-map', '0:v:0', '-map', '0:a:0')  # ✅ Fix: use global_args to map both video and audio
                .run(capture_stdout=True, capture_stderr=True)
            )

        except ffmpeg.Error as e:
            st.toast("❌ FFmpeg error:")
            st.toast(e.stderr.decode() if e.stderr else "No stderr captured.")


def clear_files():
    for f in os.listdir("downloads"):
        os.remove(os.path.join("downloads", f))

    for f in os.listdir("clips"):
        os.remove(os.path.join("clips", f))