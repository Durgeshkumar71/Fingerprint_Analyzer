# 🚀 Deploying BioCypher to Hugging Face Spaces

This guide walks you through deploying **BioCypher** to **Hugging Face Spaces** for free in under 3 minutes, giving you a public link (e.g. `https://huggingface.co/spaces/YourUsername/BioCypher`) to share on your resume, LinkedIn, or university project portfolio!

---

## Why Hugging Face Spaces?
- **100% Free**: Includes 2 vCPU and 16GB RAM on the free tier (more than enough for fast OpenCV analysis).
- **Public URL**: Anyone in the world can test your app without installing Python.
- **Permanent Showcase**: Embeds directly into Hugging Face's global AI/Cybersecurity research hub.
- **Custom UI Preserved**: Uses the Docker SDK to run your exact Cool Slate & Sky Blue interface.

---

## Step-by-Step Deployment Instructions

### Step 1: Create a Free Hugging Face Account
1. Go to [huggingface.co/join](https://huggingface.co/join) and create an account (if you don't already have one).

### Step 2: Create a New Space
1. Navigate to [huggingface.co/new-space](https://huggingface.co/new-space).
2. Fill in the details:
   - **Space name**: `BioCypher` or `Fingerprint-Risk-Analyzer`
   - **License**: `MIT`
   - **Space SDK**: Select **Docker** 🐳
   - **Docker template**: Choose **Blank**
   - **Space hardware**: `CPU Basic • 2 vCPU • 16GB RAM • Free`
   - **Visibility**: `Public`
3. Click **"Create Space"**.

---

### Step 3: Upload the Project Files
You can upload the files in two ways:

#### Option A: Direct Git Push (Fastest)
Hugging Face Spaces gives you a Git clone URL. In your terminal:
```bash
# Add Hugging Face as a remote (replace with your HF username and Space name)
git remote add hf https://huggingface.co/spaces/YOUR_USERNAME/BioCypher

# Push your fingerprint-risk directory to Hugging Face
git push hf main
```

#### Option B: Upload via Web Browser
1. Inside your newly created Space, click the **"Files and versions"** tab.
2. Click **"Add file"** ➔ **"Upload files"**.
3. Drag and drop all files from `d:\Project\fingerprint-risk`:
   - `Dockerfile`
   - `requirements.txt`
   - `app.py`
   - `cv_engine.py`
   - `static/` (folder with css, js, and samples)
   - `templates/` (folder with index.html)
   - `README.md`
4. Click **"Commit changes to main"**.

---

### Step 4: Live App Builds Automatically!
- Hugging Face will automatically read the `Dockerfile`, install OpenCV and Flask, and start the app on port `7860`.
- Within 1–2 minutes, your status badge will turn from `Building` to `Running`!
- Your live app is now accessible to the entire world! 🎉
