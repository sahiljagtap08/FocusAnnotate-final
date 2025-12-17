# 🧬 AI-Assisted Behavioral Annotation Pipeline

**Privacy-Preserving Automated Video Analysis for Neurodiversity Research**

---

> *"We were spending 40 hours annotating a single participant's video. Forty hours. Like archaeologists brushing dirt off bones with a toothbrush."*
>
> So we built something that does it in nine minutes.

---

## What This Does

This pipeline converts raw 30-minute Zoom recordings into granular behavioral datasets—automatically.

It replaces the soul-crushing process of frame-by-frame manual video coding by using **Gemini 1.5 Pro's multimodal understanding** to detect specific physical actions.

| Input | Output |
|-------|--------|
| `P09_Full_Session.mp4` (400MB, 30min) | `P09_FINAL_ANNOTATIONS.json` (2KB) |

The system classifies every moment as **"Task"** or **"Off Task"** based on dominant hand activity—catching micro-interruptions as short as 2-3 seconds.

---

## 🔒 Privacy & IRB Compliance

**CRITICAL:** This software was architected for human subject research. No raw data leaves your machine.

| Protection Layer | How It Works |
|------------------|--------------|
| **Audio Removal** | FFmpeg strips all audio tracks (`-an` flag) *before* upload. No spoken PII ever transmitted. |
| **Resolution Masking** | Video downsampled to 480p. Reduces facial fidelity while preserving motion. |
| **Zero Retention** | Script issues immediate `delete_file` API command after analysis. Google doesn't keep it. |
| **Encrypted Transit** | All data transmitted via HTTPS to Google Vertex AI. |

---

## 🏗 System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        LOCAL MACHINE (Your Laptop)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                 │
│   │  RAW VIDEO   │───▶│   COMPRESS   │───▶│    CHUNK     │                 │
│   │  1080p/400MB │    │  480p/40MB   │    │  5-min segs  │                 │
│   │              │    │  Audio: ❌    │    │              │                 │
│   └──────────────┘    └──────────────┘    └──────┬───────┘                 │
│                                                  │                          │
│                        ┌─────────────────────────┘                          │
│                        ▼                                                    │
└────────────────────────┼────────────────────────────────────────────────────┘
                         │ HTTPS (encrypted)
                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GOOGLE CLOUD (Temporary)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────────────────────────────────────────────────┐             │
│   │                   GEMINI 1.5 PRO                         │             │
│   │  • Reads visual clock overlay                            │             │
│   │  • Classifies: "Task" vs "Off Task"                      │             │
│   │  • Returns JSON with timestamps                          │             │
│   └──────────────────────────────────────────────────────────┘             │
│                                │                                            │
│                                ▼                                            │
│                    🗑️ FILE DELETED IMMEDIATELY                              │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              OUTPUT                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   P09_FINAL_ANNOTATIONS.json                                               │
│   ┌────────────────────────────────────────────────────────┐               │
│   │  [                                                     │               │
│   │    {"start_time": "14:05:00", "end_time": "14:05:52",  │               │
│   │     "label": "Off Task"},                              │               │
│   │    {"start_time": "14:05:52", "end_time": "14:06:01",  │               │
│   │     "label": "Task"},                                  │               │
│   │    ...                                                 │               │
│   │  ]                                                     │               │
│   └────────────────────────────────────────────────────────┘               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## The Four Stages

### Stage 1: The Privacy Firewall

Before anything leaves your machine:

```
Raw Video (1080p, 400MB)
        │
        ▼
   ┌─────────┐
   │ FFmpeg  │──▶ Downscale to 480p (90% size reduction)
   │         │──▶ Strip audio track (-an flag)
   │         │──▶ Re-encode H.264
   └─────────┘
        │
        ▼
Sanitized Video (480p, 40MB, SILENT)
```

**Why 480p?** Retains 100% temporal resolution (fps) for behavioral analysis. Reduces file size for faster upload. Degrades facial detail as bonus privacy layer.

### Stage 2: The Chunking Engine

Long videos make AI models lazy. They start hallucinating. They skip sections.

**Solution:** Force context refresh every 5 minutes.

```
30-minute video
        │
        ▼
┌───┬───┬───┬───┬───┬───┐
│ 1 │ 2 │ 3 │ 4 │ 5 │ 6 │  ← 6 independent chunks
└───┴───┴───┴───┴───┴───┘
  5m  5m  5m  5m  5m  5m
```

Each chunk analyzed fresh. No context bleed. Maximum granularity.

### Stage 3: The AI Inference Engine

**Model:** Gemini 1.5 Pro (1M token context window)

**Prompt Engineering:**
- Role: Behavioral research coder
- Target: Dominant hand activity (the one wearing the watch)
- Instruction: Read visual clock for timestamps
- Output: Pure JSON, no markdown

**Classification Rules:**
| Label | Definition |
|-------|------------|
| **Task** | Hand actively picking up chip OR placing chip in box |
| **Off Task** | Everything else (resting, fidgeting, adjusting, talking) |

### Stage 4: Data Aggregation

```
chunk_001.json ─┐
chunk_002.json ─┼──▶ MERGE ──▶ P09_FINAL_ANNOTATIONS.json
chunk_003.json ─┤
chunk_004.json ─┤
chunk_005.json ─┤
chunk_006.json ─┘
```

Output is structurally identical to human-labeled ground truth CSVs. Direct comparison ready.

---

## 🛠 Installation

### Prerequisites

| Requirement | Version | Check |
|-------------|---------|-------|
| Python | 3.9+ | `python --version` |
| FFmpeg | Any | `ffmpeg -version` |
| API Key | Google AI Studio | [Get one here](https://aistudio.google.com/) |

### Step 1: Install FFmpeg

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
# Add bin folder to System PATH
```

### Step 2: Install Python Dependencies

```bash
pip install google-generativeai tqdm
```

Or use the requirements file:

```bash
pip install -r requirements.txt
```

**requirements.txt:**
```text
google-generativeai
tqdm
```

### Step 3: Get API Key

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Click **"Get API key"**
3. Copy the key

---

## 🚀 Usage

### Quick Start

**1.** Drop your video file into the project folder

**2.** Open `video_pipeline.py` and configure:

```python
# ================= CONFIGURATION =================
API_KEY = "YOUR_API_KEY_HERE"
INPUT_VIDEO = "P09_Full_Session.mp4"
CHUNK_DURATION = 300  # seconds (5 minutes)
# =================================================
```

**3.** Run it:

```bash
python video_pipeline.py
```

**4.** Get your output:

```
P09_Full_Session_FINAL_ANNOTATIONS.json
```

### Example Output

```json
[
  {
    "start_time": "14:05:00",
    "end_time": "14:05:52",
    "label": "Off Task"
  },
  {
    "start_time": "14:05:52",
    "end_time": "14:06:01",
    "label": "Task"
  },
  {
    "start_time": "14:06:01",
    "end_time": "14:06:18",
    "label": "Off Task"
  }
]
```

---

## ⚙️ Advanced Configuration

### Changing Chunk Duration

Shorter chunks = more API calls, higher precision, slower processing.

```python
CHUNK_DURATION = 180  # 3 minutes for difficult videos
CHUNK_DURATION = 300  # 5 minutes (default)
CHUNK_DURATION = 600  # 10 minutes for clear, stable footage
```

### Modifying Task Definition

Edit the prompt in `analyze_chunk()`:

```python
# Current (chip sorting task)
"The hand is ACTIVELY picking up a chip or placing it in the box."

# Example modification (assembly task)
"The hand is manipulating components OR using tools on the workpiece."
```

---

## ❓ Troubleshooting

### Quick Reference

| Error | Cause | Fix |
|-------|-------|-----|
| `FileNotFoundError: ffmpeg` | FFmpeg not in PATH | Run `ffmpeg -version`. Reinstall if missing. |
| `400 Bad Request` / `API_KEY_INVALID` | Invalid API key | Ensure key starts with `AIza...` (see below) |
| `429 Resource Exhausted` | Rate limit hit | Wait 60 seconds. Reduce parallel runs. |
| `Empty JSON Output` | Safety filter triggered | Lower `CHUNK_DURATION` to 180s |
| `Timestamps don't match` | Clock not visible | Ensure Zoom timestamp overlay is enabled in recording |
| `Created 0 chunks` | Video compression or splitting failed | See detailed fix below |

---

### "Created 0 chunks" - Detailed Fix

This happens when FFmpeg fails silently during video processing. Common causes:

**1. Odd Video Width (libx264 error)**

If your source video has an odd width after scaling, libx264 will fail. The error looks like:
```
width not divisible by 2 (853x480)
```

**Fix:** Ensure `TARGET_RESOLUTION` uses `-2` instead of `-1`:
```python
# Wrong - may produce odd width
TARGET_RESOLUTION = "scale=-1:480"

# Correct - ensures even width
TARGET_RESOLUTION = "scale=-2:480"
```

**2. Corrupted or Unreadable Video**

Test if FFmpeg can read your video:
```bash
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 YOUR_VIDEO.mp4
```
This should print the duration in seconds (e.g., `1878.320000`). If it errors, your video file may be corrupted.

**3. Leftover Temp Files**

If a previous run failed, clean up before retrying:
```bash
rm -f temp_compressed.mp4 temp_chunk_*.mp4
```

---

### API Key Issues

**Symptom:** `API key not valid. Please pass a valid API key.`

**Common Cause:** Extra character when copy-pasting the key.

Google API keys **always** start with `AIza`. If your key starts with anything else (like `YAIza` or `xAIza`), you have a typo.

```python
# Wrong - has extra 'Y' at the start
API_KEY = "YAIzaSyCzRd9QK8sRfC0gGroNaCX6iJqfzOjVGvA"

# Correct
API_KEY = "AIzaSyCzRd9QK8sRfC0gGroNaCX6iJqfzOjVGvA"
```

**To get a fresh key:**
1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Click **"Get API key"**
3. Copy carefully (no extra characters)

---

### Rate Limit / Quota Exhausted (429 Error)

**Symptom:** `429 Quota exceeded` or `RATE_LIMIT_EXCEEDED`

**Understanding the Error:**

Check the `quota_limit_value` in the error message:
- `quota_limit_value: "0"` = Your project has **no quota allocated**. You need to enable the Generative Language API or use a different key.
- `quota_limit_value: "15"` (or similar) = You're hitting the actual rate limit. Wait and retry.

**Solutions:**

1. **Use Google AI Studio key (Recommended)**
   - Keys from [AI Studio](https://aistudio.google.com/) come with free tier quota (15 requests/minute for Gemini 1.5 Pro)
   - Keys from Google Cloud Console require manual quota enablement

2. **Enable API in Cloud Console**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Navigate to **APIs & Services** > **Library**
   - Search for and enable **Generative Language API**
   - Go to **Quotas** and ensure GenerateContent quota is > 0

3. **Built-in Retry Logic**
   - The script automatically retries on rate limits with exponential backoff (60s, 120s, 180s)
   - A 5-second delay between chunks helps prevent hitting limits

---

## 📊 Validation

Compare AI output against human ground truth:

```bash
python compare_annotations.py \
  --ai P09_FINAL_ANNOTATIONS.json \
  --gt P09_Final.xlsx \
  --output P09_accuracy_report.json
```

Metrics generated:
- Overall accuracy
- Precision / Recall per class
- Confusion matrix
- Boundary error analysis (onset/offset precision)

---

## 📁 Project Structure

```
FocusAnnotate/
├── video_pipeline.py          # Main script
├── compare_annotations.py     # Validation script
├── requirements.txt           # Python dependencies
├── README.md                  # This file
│
├── data/
│   ├── raw/                   # Original videos (never uploaded)
│   ├── processed/             # Sanitized videos (temporary)
│   └── outputs/               # Final JSON annotations
│
└── ground_truth/
    ├── P09_Final.xlsx         # Human annotations
    ├── P13_Final.xlsx
    └── ...
```

---

## 📜 Citation

```bibtex
@software{focusannotate2025,
  title = {FocusAnnotate: AI-Assisted Behavioral Annotation Pipeline},
  author = {Jagtap, Sahil and Islam, Anika Binte and Motti, Vivian},
  year = {2025},
  institution = {George Mason University},
  note = {NSF-funded research on neurodiversity in the workplace}
}
```

---

## License

MIT License. See `LICENSE` file.

---

<p align="center">
  <i>Built at 3 a.m. in Fairfax, Virginia.</i><br>
  <i>Because nobody should spend 40 hours watching the same hand pick up chips, this does it while you grab a coffee.</i>
</p>