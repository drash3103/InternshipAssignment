# BeyondChats Internship Assignment: Reddit User Persona Generator

This script generates user personas from Reddit posts and comments, outputting to text and HTML files with citations.

## Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/beyondchats-internship.git
   cd beyondchats-internship
   ```
2. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python3 -m spacy download en_core_web_sm
   ```
3. Run the script and enter Reddit API credentials (from [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps), create a **script** app):
   ```bash
   python3 reddit_persona.py
   ```

## Execution
1. Enter usernames (`kojied,Hungry-Move-6603`) when prompted.
2. Outputs:
   - Text: `<username>_persona.txt`
   - HTML: `<username>_persona.html`
   - WebP: Convert HTML to `<username>_persona.webp` using Chrome or convertio.co

## Outputs
- Generated personas for  and  in text, HTML, and WebP formats (available locally).

## Notes
- Uses `t5-small` for summarization (CPU).
- Follows PEP-8 guidelines.
- Contact: jdrashti8@gmail.com 
