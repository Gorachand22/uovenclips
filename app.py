import streamlit as st
from oven import *
import os

st.set_page_config(page_title="Ucllips Generator 🤖", layout="centered", page_icon="🧊")
# Inject Custom CSS
st.markdown("""
<style>
/* General Page Styling */
body {
    font-family: 'Arial', sans-serif;
    background-color: #f4f4f9;
    color: #333333;
}

/* Header Styling */
h1 {
    text-align: center;
    font-size: 3rem;
    color: #4CAF50;
    margin-bottom: 20px;
}

/* Divider Styling */
hr {
    border: none;
    border-top: 2px solid #4CAF50;
    margin: 20px 0;
}

/* Tabs Styling */
.streamlit-tabs {
    font-size: 1.2rem;
    font-weight: bold;
    color: #4CAF50;
}

/* Buttons Styling */
button {
    background-color: #4CAF50 !important;
    border: none !important;
    color: white !important;
    padding: 10px 20px !important;
    border-radius: 8px !important;
    font-size: 1rem !important;
    cursor: pointer !important;
}

button:hover {
    background-color: #45a049 !important;
}

/* Containers Styling */
.container {
    background-color: #ffffff;
    border-radius: 10px;
    padding: 20px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    margin-bottom: 20px;
}

/* Video Player Styling */
video {
    border-radius: 10px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

/* Code Block Styling */
code {
    background-color: #f4f4f9;
    border-radius: 5px;
    padding: 5px;
    font-size: 0.9rem;
}
</style>
""", unsafe_allow_html=True)
st.markdown("""
<script>
document.addEventListener('contextmenu', event => event.preventDefault());
</script>
""", unsafe_allow_html=True)
# Init session state
for key in ['downloads_ready', 'transcript_ready', 'transcribed_by', 'subtitle_found', 'video_url']:
    if key not in st.session_state:
        st.session_state[key] = None if key == 'transcribed_by' else False

# UI
# Title and Subtitle
st.markdown("<h1 style='text-align: center;'>🤖 Ucllips Generator</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-size: 1.2rem; color: #555;'>Generate engaging video clips from YouTube URLs or uploaded files!</p>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

# Tabs
tab1, tab2 = st.tabs(["🔗 Ulink", "📂 UploadFiles"])
with tab1:
    st.subheader("🎬 Generate Clips from URL")
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            url = st.text_input("🔗 Enter a YouTube video URL", placeholder="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        with col2:
            n_clips = st.number_input("🎯 Number of Uclips", min_value=1, max_value=3, value=3, step=1)
    clip_length = st.number_input("🕒 Clip Length (seconds)", min_value=10, max_value=50, value=30, step=5)
    clip_type = st.selectbox("🎞️ Clip Type", ["educational", "funny", "entertaining"])

    if st.button("🚀 Generate Ucllips", key='uclip1') and url:
        with st.spinner("Downloading resources..."):
                try:
                    audio_response = download_audio(url)
                    video_response = download_video(url)
                    subtitle_response = download_subtitles(url)

                    st.session_state.downloads_ready = all([audio_response, video_response])
                    st.session_state.subtitle_found = subtitle_response
                    st.session_state.video_url = url

                    st.toast("✅ Audio downloaded" if audio_response else "❌ Audio failed")
                    st.toast("✅ Video downloaded" if video_response else "❌ Video failed")

                    if subtitle_response:
                        st.session_state.transcript_ready = True
                        st.session_state.transcribed_by = "subtitles"
                        st.toast("✅ Subtitles downloaded!", icon="✅")

                except Exception as e:
                    st.toast(f"❌ Error: {e}", icon="❌")

# --- AFTER DOWNLOAD ---
if st.session_state.downloads_ready and not st.session_state.transcript_ready:
    st.warning("⚠️ Subtitles not available. Choose transcription method:")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🧠 Transcribe via AI Model"):
            with st.spinner("Transcribing..."):
                try:
                    if transcribe_audio("downloads/audio.mp3"):
                        st.session_state.transcript_ready = True
                        st.session_state.transcribed_by = "model"
                        st.toast("✅ Transcribed via model")
                except Exception as e:
                    st.toast(f"❌ Error: {e}")

    with col2:
        st.info("📥 Download Audio File")
        if os.path.exists("downloads/audio.mp3"):
            with open("downloads/audio.mp3", "rb") as f:
                st.audio(f)

    with col3:
        st.info("📥 Download Video File")
        if os.path.exists("downloads/video.mp4"):
            with open("downloads/video.mp4", "rb") as f:
                st.video(f)

# --- CLIPPING ---
if st.session_state.transcript_ready:
    with st.spinner("🔍 Finding hooky moments..."):
        response = fetch_hooky_timestamps(top_n=n_clips, clip_length=clip_length, clip_type=clip_type)

    if response:
        st.toast("✂️ Clipping video...")
        clip_video(response, "downloads/video.mp4")

        st.markdown("<h2 style='text-align: center;'>🎬 Generated Clips</h2>", unsafe_allow_html=True)
        
        # Determine the number of clips
        num_clips = len(response)
        
        # Create columns dynamically based on the number of clips
        cols = st.columns(num_clips)  # Each clip gets its own column
        
        # Iterate through the response and populate the columns
        for idx, key in enumerate(response):
            caption = response[key]['caption']
            hashtags = ' '.join(response[key]['hashtags'])
            clip_path = f"clips/clip_{key.split()[-1]}.mp4"
            
            # Check if the clip file exists
            if os.path.exists(clip_path):
                with cols[idx]:  # Use the corresponding column for this clip
                    st.markdown(f"<h3 style='text-align: center;'>🎥 {key}</h3>", unsafe_allow_html=True)
                    st.video(clip_path)  # Display the video clip
                    
                    # Display the caption and hashtags
                    st.write("**Caption:**")
                    st.code(caption, language="text")  # Caption in a copy-friendly format
                    
                    st.write("**Hashtags:**")
                    st.code(hashtags, language="text")  # Hashtags in a copy-friendly format

with tab2:
    video_file = st.file_uploader("Upload .mp4 video", type=["mp4"], key="video_file")
    transcript_file = st.file_uploader("Upload .txt transcript", type=["txt"], key="transcript_file2")

    if st.button("🚀 Generate Uclips", key='uclip2') and video_file and transcript_file:
        with open("downloads/video.mp4", "wb") as f:
            f.write(video_file.read())
        with open("downloads/transcript.txt", "wb") as f:
            f.write(transcript_file.read())

        

        with st.spinner("🔍 Finding hooky moments..."):
            response = fetch_hooky_timestamps(top_n=n_clips, clip_length=clip_length, clip_type=clip_type)

        if response:
            st.toast("✂️ Clipping video...")
            clip_video(response, "downloads/video.mp4")

            st.markdown("<h2 style='text-align: center;'>🎬 Generated Clips</h2>", unsafe_allow_html=True)
            
            # Determine the number of clips
            num_clips = len(response)
            
            # Create columns dynamically based on the number of clips
            cols = st.columns(num_clips)  # Each clip gets its own column
            
            # Iterate through the response and populate the columns
            for idx, key in enumerate(response):
                caption = response[key]['caption']
                hashtags = ' '.join(response[key]['hashtags'])
                clip_path = f"clips/clip_{key.split()[-1]}.mp4"
                
                # Check if the clip file exists
                if os.path.exists(clip_path):
                    with cols[idx]:  # Use the corresponding column for this clip
                        st.markdown(f"<h3 style='text-align: center;'>🎥 {key}</h3>", unsafe_allow_html=True)
                        st.video(clip_path)  # Display the video clip
                        
                        # Display the caption and hashtags
                        st.write("**Caption:**")
                        st.code(caption, language="text")  # Caption in a copy-friendly format
                        
                        st.write("**Hashtags:**")
                        st.code(hashtags, language="text")  # Hashtags in a copy-friendly format

# Clear Button
st.markdown("<hr>", unsafe_allow_html=True)
st.info("🧹 Before next generation, clear files")
if st.button("🧹 Clear Files"):
    clear_files()
