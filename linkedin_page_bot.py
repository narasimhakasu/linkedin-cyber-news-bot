import os
import json
import requests
from datetime import datetime, timedelta

# =========================
# CONFIG
# =========================
POSTED_FILE = "posted_articles.json"

ACCESS_TOKEN = os.environ["LINKEDIN_ACCESS_TOKEN"]
PERSON_URN = os.environ["PERSON_URN"]
NEWS_API_KEY = os.environ["NEWS_API_KEY"]

NEWS_API_URL = "https://newsapi.org/v2/everything"

HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "X-Restli-Protocol-Version": "2.0.0"
}

# =========================
# POSTED ARTICLES STORAGE
# =========================
def load_posted():
    if not os.path.exists(POSTED_FILE):
        return set()
    with open(POSTED_FILE, "r") as f:
        return set(json.load(f))


def save_posted(posted):
    with open(POSTED_FILE, "w") as f:
        json.dump(list(posted), f, indent=2)

# =========================
# CLEAN SUMMARY
# =========================
def clean_summary(text):
    if not text:
        return ""
    if "[" in text:
        text = text.split("[")[0]
    while text.endswith(".") or text.endswith("…"):
        text = text[:-1]
    return text.strip()

# =========================
# FETCH NEWS
# =========================
def fetch_news():
    posted = load_posted()

    params = {
        "domains": (
            "thehackernews.com,"
            "bleepingcomputer.com,"
            "zdnet.com,"
            "darkreading.com,"
            "securityweek.com,"
            "threatpost.com,"
            "csis.org,"
            "nist.gov,"
            "cloudflare.com,"
            "wired.com,"
            "arstechnica.com,"
            "techcrunch.com,"
            "venturebeat.com,"
            "infosecurity-magazine.com,"
            "cisa.gov,"
            "mitre.org,"
            "sans.org"
        ),
        "q": (
            "cybersecurity OR security OR cyber attack OR breach OR "
            "ransomware OR vulnerability OR zero-day OR malware OR "
            "cloud security OR AI security OR DevSecOps OR "
            "zero trust OR framework OR compliance OR mitigation"
        ),
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 50,
        "from": (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d"),
        "apiKey": NEWS_API_KEY
    }

    r = requests.get(NEWS_API_URL, params=params)
    data = r.json()

    if not data.get("articles"):
        return None

    THREAT_TERMS = [
        "breach", "attack", "exploited", "vulnerability",
        "zero-day", "malware", "ransomware", "phishing"
    ]

    ADVANCEMENT_TERMS = [
        "framework", "architecture", "zero trust", "cloud",
        "ai", "automation", "platform", "defsecops",
        "mitigation", "best practice", "strategy",
        "compliance", "standard", "guideline"
    ]

    EXCLUDE_TERMS = [
        "arrest", "interpol", "europol", "sentenced",
        "trial", "court", "gang", "police"
    ]

    for article in data["articles"]:
        url = article.get("url")
        if not url or url in posted:
            continue

        title = (article.get("title") or "").lower()
        desc = (article.get("description") or "").lower()
        text = f"{title} {desc}"

        if any(x in text for x in EXCLUDE_TERMS):
            continue

        if not (
            any(x in text for x in THREAT_TERMS) or
            any(x in text for x in ADVANCEMENT_TERMS)
        ):
            continue

        if not article.get("urlToImage"):
            continue

        print("Selected NEW article:", article["title"])

        return {
            "title": article["title"],
            "summary": clean_summary(article["description"])[:300],
            "image_url": article["urlToImage"],
            "link": url
        }

    return None


# =========================
# REGISTER IMAGE UPLOAD
# =========================
def register_upload():
    url = "https://api.linkedin.com/v2/assets?action=registerUpload"

    payload = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": PERSON_URN,
            "serviceRelationships": [{
                "relationshipType": "OWNER",
                "identifier": "urn:li:userGeneratedContent"
            }]
        }
    }

    r = requests.post(
        url,
        headers={**HEADERS, "Content-Type": "application/json"},
        json=payload
    )

    data = r.json()["value"]
    upload_url = data["uploadMechanism"][
        "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
    ]["uploadUrl"]

    asset = data["asset"]
    return upload_url, asset

# =========================
# UPLOAD IMAGE
# =========================
def upload_image(upload_url, image_url):
    image = requests.get(image_url).content
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/octet-stream"
    }
    r = requests.put(upload_url, headers=headers, data=image)
    return r.status_code == 201 or r.status_code == 200

# =========================
# CREATE POST
# =========================
def create_post(title, summary, asset, link):
    text = (
        f"🔐 Cybersecurity Update | {datetime.now().strftime('%d %b %Y')}\n\n"
        f"📰 {title}\n\n"
        f"{summary}\n\n"
        f"🔗 Read more: {link}\n\n"
        f"#CyberSecurity #InfoSec #CloudSecurity #DevSecOps"
    )

    payload = {
        "author": PERSON_URN,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "IMAGE",
                "media": [{
                    "status": "READY",
                    "media": asset,
                    "title": {"text": "Cybersecurity Update"}
                }]
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }

    r = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers={**HEADERS, "Content-Type": "application/json"},
        json=payload
    )

    return r.status_code == 201

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    posted = load_posted()
    news = fetch_news()

    if not news:
        print("No new article found.")
        exit()

    upload_url, asset = register_upload()

    if not upload_image(upload_url, news["image_url"]):
        print("Image upload failed.")
        exit()

    if create_post(news["title"], news["summary"], asset, news["link"]):
        posted.add(news["link"])
        save_posted(posted)
        print("Posted successfully.")
    else:
        print("Post failed.")

