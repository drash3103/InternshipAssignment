# BeyondChats Internship Assignment: Reddit User Persona Generator

This repository contains a Python script that generates user personas from Reddit profiles by analyzing posts and comments, producing text, HTML, and WebP outputs with citations. The script uses `praw` for Reddit API access, `spacy` for named entity recognition (NER), and `t5-small` for text summarization. Sample outputs for users `kojied` and `Hungry-Move-6603` are included.

## Repository Contents
- `reddit_persona.py`: Main script to generate personas.
- `requirements.txt`: Dependencies.
- `README.md`: This file.
- Output files:
  - `kojied_persona.txt`, `kojied_persona.html`, `kojied_persona.webp`
  - `Hungry-Move-6603_persona.txt`, `Hungry-Move-6603_persona.html`, `Hungry-Move-6603_persona.webp`

## Prerequisites
- Python 3.8 or higher
- A Reddit account with API credentials
- A Unix-like system (e.g., macOS, Linux) or Windows with Python installed

## Setup

### 1. Clone the Repository
```bash
git clone https://github.com/drash3103/beyondchats-internship.git
cd beyondchats-internship
```

### 2. Set Up a Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
python3 -m spacy download en_core_web_sm
```

The `requirements.txt` includes:
- `praw`
- `spacy`
- `transformers==4.44.2`
- `torch==2.4.1`

### 4. Set Up Reddit API Credentials
1. Log in to [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps).
2. Click "Create App" or "Create Another App."
3. Enter:
   - **Name**: `profileExtractor`
   - **App Type**: `script`
   - **Redirect URI**: `http://localhost:8080`
4. Click "Create App."
5. Note the `client_id` (below the app name) and `client_secret`.
6. Use a `user_agent` like: `script:profileExtractor:v1.0 (by /u/your_username)` (replace `your_username` with your Reddit username, e.g., `/u/drash_3`).

**Security Note**: Do not share your `client_id` or `client_secret`, and do not hardcode them in the script.

## Execution
1. Run the script:
   ```bash
   python3 reddit_persona.py
   ```
2. Enter your Reddit API credentials when prompted:
   - `client_id`
   - `client_secret`
   - `user_agent` (e.g., `script:profileExtractor:v1.0 (by /u/drash_3)`)
3. Enter Reddit usernames (comma-separated, e.g., `new_user1,new_user2`).

## Outputs
For each username, the script generates:
- **Text**: `<username>_persona.txt` with persona details (name, age, occupation, place, interests, etc.) and source URLs.
- **HTML**: `<username>_persona.html` with a styled webpage using Tailwind CSS.

**Sample Outputs** (included in the repository):
- `kojied_persona.txt`, `kojied_persona.html`, `kojied_persona.webp`
- `Hungry-Move-6603_persona.txt`, `Hungry-Move-6603_persona.html`, `Hungry-Move-6603_persona.webp`

## Notes
- Uses `t5-small` for CPU-based summarization, optimized for 8GB RAM systems.
- Follows PEP-8 guidelines.
- To generate personas for new profiles, enter their usernames when running the script.
- The script requires valid Reddit API credentials for data fetching.

## Contact
- Email: jdrashti8@gmail.com
- Internshala: Message via the platform

Submitted for BeyondChats AI/LLM Engineer Intern Assignment, July 2025.
