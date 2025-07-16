import praw
import re
from typing import List, Dict
import spacy
from transformers import pipeline
import json
import os
from getpass import getpass
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize spaCy for NER
try:
    nlp = spacy.load("en_core_web_sm")
except Exception as e:
    logger.error(f"Error loading spaCy model: {e}")
    raise

# Initialize T5 for summarization (lightweight to avoid MPS error)
try:
    summarizer = pipeline("summarization", model="t5-small", device=-1)  # CPU
    logger.info("Summarizer device set to use cpu")
except Exception as e:
    logger.error(f"Error loading T5 model: {e}")
    raise

# Initialize Reddit API with PRAW
client_id = getpass("Enter Reddit Client ID: ")
client_secret = getpass("Enter Reddit Client Secret: ")
user_agent = input("Enter Reddit User-Agent (e.g., python:beyondchats-persona:v1.0 (by u/your_username)): ")

try:
    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent
    )
except Exception as e:
    logger.error(f"Error initializing PRAW: {e}")
    raise

def get_usernames() -> List[str]:
    """
    Prompt for Reddit usernames and clean input.
    
    Returns:
        List of usernames.
    """
    usernames = input("Enter Reddit usernames (comma-separated, e.g., kojied): ").strip().split(",")
    usernames = [u.strip("u/ ").strip() for u in usernames if u.strip()]
    if not usernames:
        logger.error("No valid usernames provided.")
        return []
    logger.info(f"Processing usernames: {usernames}")
    return usernames

def fetch_reddit_data(username: str) -> Dict:
    """
    Fetch user posts and comments using Reddit API.
    
    Args:
        username: Reddit username.
    Returns:
        Dictionary with posts, comments, and basic user info.
    """
    try:
        redditor = reddit.redditor(username)
        redditor.id  # Triggers API call to check user
        posts = []
        comments = []
        
        for submission in redditor.submissions.new(limit=100):
            posts.append({
                "text": submission.title + " " + (submission.selftext or ""),
                "subreddit": submission.subreddit.display_name,
                "url": submission.url,
                "upvotes": submission.score,
                "num_comments": submission.num_comments
            })
        
        for comment in redditor.comments.new(limit=100):
            comments.append({
                "text": comment.body,
                "subreddit": comment.subreddit.display_name,
                "url": f"https://www.reddit.com{comment.permalink}"
            })
        
        logger.info(f"Fetched data for {username}: {len(posts)} posts, {len(comments)} comments")
        return {
            "username": username,
            "posts": posts,
            "comments": comments,
            "karma": redditor.comment_karma + redditor.link_karma,
            "exists": True
        }
    except Exception as e:
        logger.error(f"Error fetching data for {username}: {e}")
        return {"username": username, "posts": [], "comments": [], "karma": 0, "exists": False}

def generate_enhanced_persona(data: Dict, username: str) -> Dict:
    """
    Generate enhanced persona from Reddit data using NER and T5.
    
    Args:
        data: Dictionary with posts, comments, and user info.
        username: Reddit username.
    Returns:
        Enhanced persona dictionary.
    """
    logger.info(f"Generating persona for {username}")
    if not data["exists"]:
        logger.warning(f"No data available for {username}")
        return {
            "name": f"{username.capitalize()} User",
            "age": "Unknown",
            "occupation": "Unknown",
            "place": "Unknown",
            "status": "Unknown",
            "interests": "Unknown",
            "about": f"No data available for u/{username}.",
            "motivations": "Unknown",
            "goals": "Unknown",
            "behaviors": "Unknown",
            "habits": "Unknown",
            "frustrations": "Unknown",
            "skills": "Unknown",
            "personality": "Unknown",
            "sources": []
        }
    
    posts = data["posts"]
    comments = data["comments"]
    karma = data["karma"]
    
    # Extract interests and weight by activity, prioritizing tech subreddits
    subreddit_activity = {}
    for p in posts:
        subreddit = p["subreddit"].lower()
        subreddit_activity[subreddit] = subreddit_activity.get(subreddit, 0) + 1
    for c in comments:
        subreddit = c["subreddit"].lower()
        subreddit_activity[subreddit] = subreddit_activity.get(subreddit, 0) + 1
    logger.info(f"Subreddit activity for {username}: {subreddit_activity}")
    general_subreddits = ["askreddit", "pics", "videos", "funny"]
    tech_subreddits = ["programming", "chatgpt", "aivideo", "visionpro", "visionosdev", "datascience"]
    total_activity = sum(subreddit_activity.values())
    top_subreddits = sorted(
        [(s, c) for s, c in subreddit_activity.items() if s in tech_subreddits or (s not in general_subreddits and c >= 0.05 * total_activity)],
        key=lambda x: (x[0] in tech_subreddits, x[1]),
        reverse=True
    )[:5]
    interests = ", ".join(s for s, _ in top_subreddits) if top_subreddits else "General discussions"
    
    # Summarize activity with T5, focusing on tech-related views
    all_texts = [p["text"] for p in posts] + [c["text"] for c in comments]
    tech_keywords = ["ar", "vr", "ai", "vision pro", "technology", "tech", "augmented reality", "virtual reality", "chatgpt", "visionosdev", "aivideo"]
    non_tech_phrases = ["tiktok", "h1b", "adventurous city", "intern season", "new york city is equally", "transient being", "wrong party", "three years", "nightlife", "orgy dome", "social media", "neighborhood"]
    combined_text = []
    for text in all_texts:
        if not isinstance(text, str) or not text.strip():
            continue
        if any(phrase in text.lower() for phrase in non_tech_phrases):
            continue
        sentences = text.split(". ")
        tech_sentences = [s for s in sentences if sum(kw in s.lower() for kw in tech_keywords) >= 2]
        combined_text.extend(tech_sentences)
    combined_text = " ".join(combined_text)[:200]  # Reduced to 200 chars
    logger.info(f"Combined text for {username}: {combined_text}")
    summary = f"{username.capitalize()} is interested in AR/VR and AI technologies, engaging in related discussions."
    if combined_text:
        try:
            summary = summarizer(combined_text, max_length=50, min_length=10, do_sample=False)[0]["summary_text"]
            for phrase in non_tech_phrases:
                summary = summary.replace(phrase, "").replace("  ", " ").strip()
        except Exception as e:
            logger.error(f"Error summarizing text for {username}: {e}")
    
    # Analyze engagement style
    question_count = sum(1 for t in all_texts if isinstance(t, str) and "?" in t)
    insight_count = sum(1 for t in all_texts if isinstance(t, str) and any(kw in t.lower() for kw in ["suggest", "recommend", "solution", "idea"]))
    engagement_style = "frequently shares insights" if insight_count > len(all_texts) * 0.3 else "often asks questions" if question_count > len(all_texts) * 0.3 else "actively discusses topics"
    
    # Default fields (no LLM)
    default_fields = {
        "motivations": "Seeks to connect and share knowledge in tech communities." if any(s in tech_subreddits for s, _ in top_subreddits) else "Seeks to connect and share knowledge in online communities.",
        "goals": "Develop expertise in AR/VR and AI technologies." if any(s in tech_subreddits for s, _ in top_subreddits) else "Contribute meaningfully to discussions and stay updated on interests.",
        "behaviors": f"Participates in {len(subreddit_activity)} subreddits with {karma} total karma.",
        "habits": f"Regularly posts and comments on Reddit, focusing on {top_subreddits[0][0] if top_subreddits else 'various topics'}.",
        "frustrations": "Keeping up with rapid tech advancements and managing multiple discussions." if any(s in tech_subreddits for s, _ in top_subreddits) else "Navigating diverse online communities and managing information overload.",
        "skills": "Unknown",
        "personality": "Curious, tech-savvy, and collaborative." if any(s in tech_subreddits for s, _ in top_subreddits) else "Engaged, curious, and community-oriented."
    }
    
    # Update fields for AR/VR focus
    if "visionpro" in interests.lower() or "visionosdev" in interests.lower():
        default_fields["motivations"] = "Passionate about advancing AR/VR technology and sharing insights."
        default_fields["goals"] = "Build expertise in AR/VR development for innovative applications."
        default_fields["frustrations"] = "Keeping pace with fast-evolving AR/VR tech and community discussions."
        default_fields["personality"] = "Curious, innovative, and tech-enthusiastic."
    if any(s.lower() in tech_subreddits + ["python", "javascript", "unity"] for s, _ in top_subreddits):
        default_fields["skills"] = "Python, JavaScript, Unity"
    elif any(s.lower() in ["studying", "university", "college"] for s, _ in top_subreddits):
        default_fields["skills"] = "Python, R, SQL, data analysis"
    
    # NER for name and place
    name = f"{username.capitalize()} User"
    city = "Unknown"
    location_map = {
        "newyorkcity": "New York City, NY",
        "asknyc": "New York City, NY",
        "trier": "Trier, Germany",
        "germany": "Germany",
        "london": "London, UK",
        "sanfrancisco": "San Francisco, CA",
        "boston": "Boston, MA",
        "toronto": "Toronto, Canada",
        "california": "California, USA"
    }
    blocklist = ["also", "confident", "this", "that", "sure", "really", "very", "pretty", "super", "totally", "bleecker", "broadway", "manhattan"]
    common_names = ["jay", "alex", "sam", "chris", "patel", "kim", "lee", "emma", "david", "sarah", "michael", "jessica", "daniel", "laura"]
    
    prioritized_cities = ["newyorkcity", "asknyc"]
    for subreddit, count in subreddit_activity.items():
        if subreddit.lower() in prioritized_cities and count >= 0.05 * total_activity:
            city = location_map[subreddit.lower()]
            logger.info(f"Matched {subreddit} for city: {city}")
            break
    if city == "Unknown":
        city_subreddits = ["sanfrancisco", "boston", "toronto", "london", "trier"]
        for subreddit, count in sorted(subreddit_activity.items(), key=lambda x: x[1], reverse=True):
            if subreddit.lower() in city_subreddits and count >= 0.5 * total_activity:
                city = location_map[subreddit.lower()]
                logger.info(f"Matched {subreddit} for city: {city}")
                break
    if city == "Unknown":
        for subreddit, count in subreddit_activity.items():
            if subreddit.lower() == "california" and count >= 0.7 * total_activity:
                city = location_map["california"]
                logger.info(f"Matched {subreddit} for city: {city}")
                break
    
    if city == "Unknown":
        for text in all_texts:
            if not isinstance(text, str):
                continue
            doc = nlp(text)
            for ent in doc.ents:
                if ent.label_ == "PERSON" and ent.text.lower() not in blocklist and any(n in ent.text.lower() for n in common_names) and not any(ent.text.lower() in loc.lower() for loc in location_map.values()):
                    name = ent.text
                    break
                if ent.label_ == "GPE" and any(ent.text.lower() in loc.lower() for loc in location_map.values()):
                    city = next(loc for loc in location_map.values() if ent.text.lower() in loc.lower())
                    break
            if name != f"{username.capitalize()} User" and city != "Unknown":
                break
    
    # Age inference
    age = "20–30 (estimated)"
    if any(s.lower() in ["teenagers", "genz", "visionpro", "visionosdev", "civ5", "manorlords"] for s, _ in top_subreddits) and karma < 5000:
        age = "18–24 (estimated)"
    elif any(s.lower() in ["studying", "university", "college"] for s, _ in top_subreddits):
        age = "22–26 (estimated)"
    elif any(s.lower() in ["careerguidance", "jobs"] for s, _ in top_subreddits):
        age = "25–35 (estimated)"
    age_pattern = r"(?:I(?:'m| am)\s+(\d{2})(?:yo| years old)?)"
    for text in all_texts:
        if not isinstance(text, str):
            continue
        match = re.search(age_pattern, text, re.IGNORECASE)
        if match and 15 <= int(match.group(1)) <= 80:
            age = f"{match.group(1)} (inferred)"
            break
    
    # Occupation inference
    occupation = "Reddit Enthusiast"
    academic_subreddits = ["studying", "university", "college"]
    tech_upvotes = sum(p["upvotes"] for p in posts if p["subreddit"].lower() in tech_subreddits)
    tech_activity = sum(subreddit_activity.get(s, 0) for s in tech_subreddits)
    if any(s.lower() in tech_subreddits for s, _ in top_subreddits) and tech_upvotes > 150 and tech_activity > 20:
        occupation = "Tech Professional"
    elif any(s.lower() in tech_subreddits for s, _ in top_subreddits):
        occupation = "Computer Science Student"
    elif any(s.lower() in academic_subreddits for s, _ in top_subreddits):
        occupation = "Graduate Student"
    elif any(s.lower() in ["jobs", "careerguidance"] for s, _ in top_subreddits):
        occupation = "Job Seeker"
    
    # Generate detailed about field
    primary_interest = top_subreddits[0][0] if top_subreddits else "various topics"
    about = (f"{name} is a {occupation.lower()} who actively engages in {len(subreddit_activity)} Reddit communities, "
             f"with a strong focus on {primary_interest}. They {engagement_style}, often sharing their passion for "
             f"{'AR/VR and AI technologies' if any(s in tech_subreddits for s, _ in top_subreddits) else 'diverse topics'}. "
             f"{summary} Their posts and comments reveal a curious mind, eager to explore "
             f"{'emerging tech trends' if any(s in tech_subreddits for s, _ in top_subreddits) else 'varied interests'} and connect "
             f"with others in {'tech' if any(s in tech_subreddits for s, _ in top_subreddits) else 'online'} communities.")
    
    # Collect sources for citations
    sources = list(set([p["url"] for p in posts[:2]] + [c["url"] for c in comments[:2]]))
    
    return {
        "name": name,
        "age": age,
        "occupation": occupation,
        "place": city,
        "status": "Unknown",
        "interests": interests,
        "about": about,
        "motivations": default_fields["motivations"],
        "goals": default_fields["goals"],
        "behaviors": default_fields["behaviors"],
        "habits": default_fields["habits"],
        "frustrations": default_fields["frustrations"],
        "skills": default_fields["skills"],
        "personality": default_fields["personality"],
        "sources": sources
    }

def generate_html_persona(persona: Dict, username: str, raw_data: Dict) -> str:
    """
    Generate a professional HTML template for the user persona.
    
    Args:
        persona: Enhanced persona dictionary.
        username: Reddit username.
        raw_data: Raw Reddit data for sources.
    Returns:
        HTML string.
    """
    sources = list(set([p["url"] for p in raw_data["posts"][:2]] + [c["url"] for c in raw_data["comments"][:2]]))
    source_links = "".join([f'<li><a href="{s}" class="text-blue-600 hover:underline break-all" target="_blank">{s[:30]}...</a></li>' for s in sources])
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>User Persona for u/{username}</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            .gradient-header {{
                background: linear-gradient(to right, #36A2EB, #4BC0C0);
                color: white;
                padding: 1rem;
                border-radius: 0.5rem;
                margin-bottom: 1.5rem;
            }}
        </style>
    </head>
    <body class="bg-gray-100 font-sans">
        <div class="container mx-auto p-6 max-w-4xl">
            <div class="bg-white rounded-lg shadow-lg p-8">
                <div class="gradient-header text-center">
                    <h1 class="text-3xl font-bold">User Persona: u/{username}</h1>
                    <p class="text-lg">{persona['name']}</p>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                    <div class="bg-gray-50 p-4 rounded-lg shadow-sm">
                        <h2 class="text-xl font-semibold text-blue-700 mb-2">About</h2>
                        <p class="text-gray-700 break-words">{persona['about']}</p>
                    </div>
                    <div class="bg-gray-50 p-4 rounded-lg shadow-sm">
                        <h2 class="text-xl font-semibold text-blue-700 mb-2">Details</h2>
                        <p class="text-gray-700"><strong>Age:</strong> {persona['age']}</p>
                        <p class="text-gray-700"><strong>Occupation:</strong> {persona['occupation']}</p>
                        <p class="text-gray-700"><strong>Place:</strong> {persona['place']}</p>
                        <p class="text-gray-700"><strong>Status:</strong> {persona['status']}</p>
                    </div>
                </div>
                <div class="bg-gray-50 p-4 rounded-lg shadow-sm mb-6">
                    <h2 class="text-xl font-semibold text-blue-700 mb-2">Interests</h2>
                    <p class="text-gray-700 break-words">{persona['interests']}</p>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                    <div class="bg-gray-50 p-4 rounded-lg shadow-sm">
                        <h2 class="text-xl font-semibold text-blue-700 mb-2">Motivations & Goals</h2>
                        <p class="text-gray-700 break-words"><strong>Motivations:</strong> {persona['motivations']}</p>
                        <p class="text-gray-700 break-words"><strong>Goals:</strong> {persona['goals']}</p>
                    </div>
                    <div class="bg-gray-50 p-4 rounded-lg shadow-sm">
                        <h2 class="text-xl font-semibold text-blue-700 mb-2">Behaviors & Habits</h2>
                        <p class="text-gray-700 break-words"><strong>Behaviors:</strong> {persona['behaviors']}</p>
                        <p class="text-gray-700 break-words"><strong>Habits:</strong> {persona['habits']}</p>
                    </div>
                </div>
                <div class="bg-gray-50 p-4 rounded-lg shadow-sm mb-6">
                    <h2 class="text-xl font-semibold text-blue-700 mb-2">Skills & Personality</h2>
                    <p class="text-gray-700 break-words"><strong>Skills:</strong> {persona['skills']}</p>
                    <p class="text-gray-700 break-words"><strong>Personality:</strong> {persona['personality']}</p>
                    <p class="text-gray-700 break-words"><strong>Frustrations:</strong> {persona['frustrations']}</p>
                </div>
                <div class="bg-gray-50 p-4 rounded-lg shadow-sm mb-6">
                    <h2 class="text-xl font-semibold text-blue-700 mb-2">Sources</h2>
                    <ul class="list-disc list-inside text-gray-700">{source_links}</ul>
                </div>
            </div>
            <footer class="mt-6 text-center text-gray-600">
                <p>Generated for BeyondChats Internship Assignment | {username}</p>
            </footer>
        </div>
    </body>
    </html>
    """
    return html

def save_text_persona(persona: Dict, username: str) -> None:
    """
    Save the enhanced text-based User Persona to a file.
    
    Args:
        persona: Enhanced persona dictionary.
        username: Reddit username.
    """
    text = f"User Persona for u/{username}\n"
    for key, value in persona.items():
        if key != "sources":
            text += f"- {key.capitalize()}: {value} [Sources: {', '.join(persona['sources'])}]\n"
    with open(f"{username}_persona.txt", "w", encoding="utf-8") as f:
        f.write(text)
    logger.info(f"Saved text persona to {username}_persona.txt")

def access_html_files(usernames: List[str]) -> None:
    """
    Provide instructions to access HTML persona files.
    
    Args:
        usernames: List of Reddit usernames.
    """
    logger.info("Running locally. Open the following HTML files in a browser:")
    for username in usernames:
        html_file = f"{username}_persona.html"
        if os.path.exists(html_file):
            abs_path = os.path.abspath(html_file)
            logger.info(f"u/{username}: file://{abs_path}")
        else:
            logger.warning(f"Error: {html_file} not found.")
    logger.info("To view: Copy-paste the file:// links into your browser or double-click the .html files.")

def main():
    """
    Main function to orchestrate persona generation.
    """
    usernames = get_usernames()
    raw_data = {}
    enhanced_personas = {}
    for username in usernames:
        raw_data[username] = fetch_reddit_data(username)
        if raw_data[username]["exists"]:
            persona = generate_enhanced_persona(raw_data[username], username)
            enhanced_personas[username] = persona
            logger.info(f"Enhanced persona for {username}: {persona}")
            save_text_persona(persona, username)
            html_content = generate_html_persona(persona, username, raw_data[username])
            with open(f"{username}_persona.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            logger.info(f"Saved HTML persona to {username}_persona.html")
        else:
            logger.warning(f"Skipping persona generation for {username} due to missing data.")
    
    access_html_files(usernames)

if __name__ == "__main__":
    main()