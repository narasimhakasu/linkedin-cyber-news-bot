print(os.environ.keys())

import requests
from datetime import datetime

# =========================
# CONFIG
# =========================
import os

ACCESS_TOKEN = os.environ["LINKEDIN_ACCESS_TOKEN"]
PERSON_URN = os.environ["PERSON_URN"]
NEWS_API_KEY = os.environ["NEWS_API_KEY"]


NEWS_API_URL = "https://newsapi.org/v2/everything"

HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "X-Restli-Protocol-Version": "2.0.0"
}

# =========================
# FETCH NEWS FROM NEWSAPI
# =========================


def clean_summary(text):
    if not text:
        return ""

    # Hard cut at first '[' (NewsAPI truncation marker)
    if "[" in text:
        text = text.split("[")[0]

    # Remove trailing dots / ellipsis
    while text.endswith(".") or text.endswith("…"):
        text = text[:-1]

    return text.strip()





def fetch_news():
    params = {
        "domains": (
            "thehackernews.com,"
            "bleepingcomputer.com,"
            "zdnet.com,"
            "darkreading.com,"
            "securityweek.com,"
            "threatpost.com"
        ),
        "q": (
            '"cybersecurity" OR "information security" OR '
            '"data breach" OR "ransomware" OR "malware" OR '
            '"zero trust" OR "cloud security" OR '
            '"AI security" OR "XDR" OR "SASE" OR '
            '"security framework" OR "DevSecOps"'
        ),
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 15,
        "apiKey": NEWS_API_KEY
    }

    r = requests.get(NEWS_API_URL, params=params)
    data = r.json()

    if not data.get("articles"):
        raise Exception("No articles returned")

    # --- CONTENT LANES ---
    THREAT_TERMS = [
        "breach", "attack", "exploited", "vulnerability",
        "zero-day", "malware", "ransomware", "phishing"
    ]

    ADVANCEMENT_TERMS = [
        "framework", "architecture", "zero trust", "cloud",
        "ai", "machine learning", "automation", "platform",
        "defense", "mitigation", "best practice", "strategy",
        "improvement", "advancement", "solution"
    ]

    EXCLUDE_TERMS = [
        "arrest", "interpol", "europol", "sentenced",
        "trial", "court", "leader", "gang", "wanted"
    ]

    for article in data["articles"]:
        title = (article.get("title") or "").lower()
        desc = (article.get("description") or "").lower()
        text = f"{title} {desc}"

        # Hard exclusions
        if any(x in text for x in EXCLUDE_TERMS):
            continue

        # Must match at least ONE lane
        if not (
            any(x in text for x in THREAT_TERMS) or
            any(x in text for x in ADVANCEMENT_TERMS)
        ):
            continue

        if not article.get("urlToImage"):
            continue

        return {
                    "title": article["title"],
                    "summary": clean_summary(article["description"])[:300],
                    "image_url": article["urlToImage"],
                    "link": article["url"]
                }


    raise Exception("No suitable cybersecurity article found")




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
    upload_url = data["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
    asset = data["asset"]

    return upload_url, asset

# =========================
# UPLOAD IMAGE (PUT)
# =========================
def upload_image(upload_url, image_url):
    image_bytes = requests.get(image_url).content

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/octet-stream"
    }

    r = requests.put(upload_url, headers=headers, data=image_bytes)
    print("Image upload:", r.status_code)

# =========================
# CREATE LINKEDIN POST
# =========================
def create_post(title, summary, asset, link):
    text = (
        f"🔐 Cybersecurity Update | {datetime.now().strftime('%d %b %Y')}\n\n"
        f"📰 {title}\n\n"
        f"{summary}\n\n"
        f"🔗 Read more: {link}\n\n"
        f"#CyberSecurity #InfoSec #TechSecurity"
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

    print("Post create:", r.status_code)


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    news = fetch_news()
    upload_url, asset = register_upload()
    upload_image(upload_url, news["image_url"])
    create_post(
    news["title"],
    news["summary"],
    asset,
    news["link"]
)



