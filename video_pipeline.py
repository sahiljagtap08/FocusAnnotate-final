import os
import time
import subprocess
import json
import re
import google.generativeai as genai  # type: ignore
from tqdm import tqdm

# ================= CONFIGURATION =================
# 🔑 PASTE YOUR API KEY HERE
API_KEY = "YOUR_API_KEY_HERE"

# 📁 INPUT FILE
INPUT_VIDEO = "P7.mp4"

# ⚙️ SETTINGS
CHUNK_DURATION = 300  # 300 seconds = 5 minutes
TARGET_RESOLUTION = "scale=-2:480"  # 480p height (-2 ensures width divisible by 2)
# =================================================

genai.configure(api_key=API_KEY)

def cleanup_text(text):
    """Removes markdown formatting often added by LLMs"""
    text = text.replace("```json", "").replace("```", "").strip()
    return text

def compress_and_strip_audio(input_path, output_path):
    """
    Compresses video to 480p and REMOVES AUDIO for privacy.
    """
    print(f"🎬 Processing {input_path} (Compressing & Removing Audio)...")
    
    # -an removes audio (Privacy)
    # -vf scale resizes video
    # -crf 28 is high compression
    command = [
        "ffmpeg", "-i", input_path,
        "-vf", TARGET_RESOLUTION, 
        "-an", 
        "-c:v", "libx264", 
        "-crf", "28", 
        "-preset", "faster",
        "-y", 
        output_path
    ]
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    print("✅ Privacy scrubbing & compression complete.")

def split_video(input_path, chunk_duration):
    """
    Splits the video into smaller chunks for granular analysis.
    """
    print(f"🔪 Splitting video into {chunk_duration}s chunks...")

    # Get video duration first
    probe_cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        input_path
    ]
    result = subprocess.run(probe_cmd, capture_output=True, text=True)

    try:
        total_duration = float(result.stdout.strip())
    except:
        print("⚠️ Could not detect video duration. Trying alternative method...")
        total_duration = 3600  # Assume 1 hour max

    print(f"   📏 Video duration: {total_duration:.1f} seconds")

    # Split using time-based extraction (more reliable than segment muxer)
    chunks = []
    chunk_index = 0
    start_time = 0

    while start_time < total_duration:
        output_file = f"temp_chunk_{chunk_index:03d}.mp4"

        command = [
            "ffmpeg", "-i", input_path,
            "-ss", str(start_time),
            "-t", str(chunk_duration),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "28",
            "-an",  # No audio
            "-y",
            output_file
        ]

        subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

        # Verify the chunk was created and has content
        if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
            chunks.append(output_file)
            chunk_index += 1

        start_time += chunk_duration

    print(f"📦 Created {len(chunks)} chunks.")
    return chunks

def analyze_chunk(chunk_path, chunk_index, max_retries=3):
    """
    Uploads a chunk to Gemini and gets the JSON.
    Includes retry logic for rate limit errors.
    """
    print(f"   🚀 Uploading Chunk {chunk_index+1}...")
    video_file = genai.upload_file(path=chunk_path)

    # Wait for processing
    while video_file.state.name == "PROCESSING":
        time.sleep(2)
        video_file = genai.get_file(video_file.name)

    if video_file.state.name == "FAILED":
        raise ValueError("Video processing failed on Google servers.")

    # The Prompt
    prompt = """
    You are a behavioral research assistant. Analyze this video clip of a neurodivergent participant performing a chip sorting task.

    YOUR GOAL:
    Classify the activity of the DOMINANT HAND (wearing the watch) into two categories:
    1. "Task": The hand is ACTIVELY picking up a chip or placing it in the box.
    2. "Off Task": Any other activity (resting, waiting, fidgeting, adjusting hair/clothes, talking).

    INSTRUCTIONS:
    - Look at the VISIBLE CLOCK in the video for start_time and end_time.
    - If the clock is not readable, estimate the time relative to the video start.
    - Be extremely precise. Catch micro-interruptions.
    - Output ONLY a valid JSON array. Do not add markdown or text.

    FORMAT:
    [
      {"start_time": "HH:MM:SS", "end_time": "HH:MM:SS", "label": "Task"},
      {"start_time": "HH:MM:SS", "end_time": "HH:MM:SS", "label": "Off Task"}
    ]
    """

    model = genai.GenerativeModel(model_name="models/gemini-1.5-pro")

    data = []
    for attempt in range(max_retries):
        try:
            response = model.generate_content(
                [video_file, prompt],
                generation_config={"response_mime_type": "application/json"}
            )
            result_text = cleanup_text(response.text)
            data = json.loads(result_text)
            break  # Success - exit retry loop
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RATE_LIMIT" in error_str or "quota" in error_str.lower():
                wait_time = 60 * (attempt + 1)  # 60s, 120s, 180s
                print(f"   ⏳ Rate limited. Waiting {wait_time}s before retry {attempt+2}/{max_retries}...")
                time.sleep(wait_time)
            else:
                print(f"   ⚠️ Error analyzing chunk {chunk_index+1}: {e}")
                break  # Non-rate-limit error, don't retry

    # PRIVACY: Delete file from Cloud immediately
    try:
        genai.delete_file(video_file.name)
    except:
        pass  # Ignore deletion errors

    return data

def main():
    if not os.path.exists(INPUT_VIDEO):
        print(f"❌ Error: Input file '{INPUT_VIDEO}' not found.")
        return

    # 1. Compress & Privacy Scrub
    compressed_file = "temp_compressed.mp4"
    compress_and_strip_audio(INPUT_VIDEO, compressed_file)

    # 2. Split into Chunks
    chunks = split_video(compressed_file, CHUNK_DURATION)

    # 3. Analyze Loop
    master_timeline = []

    print("\n🧠 Starting AI Analysis Loop...")
    for i, chunk in enumerate(tqdm(chunks)):
        chunk_data = analyze_chunk(chunk, i)
        if chunk_data:
            master_timeline.extend(chunk_data)

        # Local Cleanup: Delete the chunk file to save space
        os.remove(chunk)

        # Rate limit prevention: pause between API calls
        if i < len(chunks) - 1:  # Don't wait after last chunk
            time.sleep(5)

    # 4. Save Final Result
    output_filename = f"{INPUT_VIDEO.split('.')[0]}_FINAL_ANNOTATIONS.json"
    with open(output_filename, "w") as f:
        json.dump(master_timeline, f, indent=2)

    # Final Cleanup
    if os.path.exists(compressed_file):
        os.remove(compressed_file)

    print("\n" + "="*50)
    print(f"🎉 SUCCESS! Processed {len(chunks)} chunks.")
    print(f"📄 Results saved to: {output_filename}")
    print("="*50)

if __name__ == "__main__":
    main()