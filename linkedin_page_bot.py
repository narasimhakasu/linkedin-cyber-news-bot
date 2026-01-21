import os
import json
import requests
from datetime import datetime, timedelta

# =========================
# DOMAIN ROTATION CONFIG
# =========================

DOMAINS = ["cybersecurity", "cloud", "ai", "data"]
ROTATION_FILE = "rotation_state.json"
GLOBAL_POSTED_FILE = "posted_articles_global.json"

DOMAIN_CONFIGS = {
    "cybersecurity": {
        "domains": [
            "thehackernews.com", "bleepingcomputer.com", "darkreading.com",
            "securityweek.com", "threatpost.com", "zdnet.com",
            "cloudflare.com", "cisa.gov", "nist.gov"
        ],
        "query": (
            "cybersecurity OR cyber attack OR data breach OR ransomware "
            "OR zero-day OR vulnerability OR exploited OR malware "
            "OR security advisory OR patch OR mitigation OR zero trust"
        ),
        "title": "🔐 Cybersecurity Update",
        "hashtags": "#CyberSecurity #InfoSec #SecurityNews"
    },

    "cloud": {
        "domains": [
            "aws.amazon.com", "cloud.google.com", "azure.microsoft.com",
            "cloudflare.com", "zdnet.com", "techcrunch.com"
        ],
        "query": (
            "AWS OR Azure OR Google Cloud OR cloud outage "
            "OR cloud service OR infrastructure issue "
            "OR cloud security OR misconfiguration "
            "OR service disruption OR downtime"
        ),
        "title": "☁️ Cloud Update",
        "hashtags": "#CloudComputing #AWS #Azure #GCP"
    },

    "ai": {
        "domains": [
            "openai.com", "deepmind.google", "ai.googleblog.com",
            "venturebeat.com", "techcrunch.com", "wired.com"
        ],
        "query": (
            "artificial intelligence AND (model OR system OR software OR platform) "
            "OR machine learning "
            "OR LLM OR large language model "
            "OR generative AI "
            "OR AI tool "
            "OR enterprise AI "
            "OR AI platform"
        ),
        "title": "🤖 AI Update",
        "hashtags": "#AI #ArtificialIntelligence #Automation"
    },

    "data": {
        "domains": [
            "databricks.com", "snowflake.com", "cloud.google.com",
            "aws.amazon.com", "venturebeat.com", "zdnet.com"
        ],
        "query": (
            "data engineering OR data pipeline OR ETL OR ELT "
            "OR analytics platform OR big data "
            "OR Databricks OR Snowflake OR BigQuery "
            "OR Redshift OR data warehouse"
        ),
        "title": "📊 Data Update",
        "hashtags": "#DataEngineering #DataAnalytics #BigData"
    }
}

# =========================
# ENV CONFIG
# =========================

ACCESS_TOKEN = os.environ["LINKEDIN_ACCESS_TOKEN"]
PERSON_URN = os.environ["PERSON_URN"]
NEWS_API_KEY = os.environ["NEWS_API_KEY"]

NEWS_API_URL = "https://newsapi.org/v2/everything"

HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "X-Restli-Protocol-Version": "2.0.0"
}

# =========================
# STATE HELPERS
# =========================

def load_rotation_index():
    if not os.path.exists(ROTATION_FILE):
        return 0
    with open(ROTATION_FILE, "r") as f:
        return json.load(f).get("index", 0)


def save_rotation_index(index):
    with open(ROTATION_FILE, "w") as f:
        json.dump({"index": index}, f)


def load_json_set(file):
    if not os.path.exists(file):
        return set()
    with open(file, "r") as f:
        return set(json.load(f))


def save_json_set(file, data):
    with open(file, "w") as f:
        json.dump(list(data), f, indent=2)

# =========================
# CLEAN SUMMARY
# =========================

def clean_summary(text):
    if not text:
        return ""
    if "[" in text:
        text = text.split("[")[0]
    return text.rstrip(".…").strip()

# =========================
# FETCH NEWS
# =========================

def fetch_news(domain, posted, global_posted):
    config = DOMAIN_CONFIGS[domain]

    params = {
        "domains": ",".join(config["domains"]),
        "q": config["query"],
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 50,
        "from": (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d"),
        "apiKey": NEWS_API_KEY
    }

    data = requests.get(NEWS_API_URL, params=params).json()
    if not data.get("articles"):
        return None

    GLOBAL_EXCLUDE = [
        "arrest", "interpol", "europol", "sentenced",
        "trial", "court", "gang", "police",
        "election", "politics", "minister"
    ]

    AI_REQUIRED = [
        "ai", "artificial intelligence",
    "model", "ml", "machine learning",
    "llm", "large language model",
    "neural", "deep learning",
    "automation", "intelligence",
    "software", "platform", "tool"
    ]

    AI_EXCLUDE = [
        "alien", "ufo", "extraterrestrial",
        "nasa", "space", "astronomy",
        "astrophysics", "interstellar", "seti"
    ]

    CLOUD_REQUIRED = ["aws", "azure", "gcp", "cloud", "outage", "region"]
    DATA_REQUIRED = [
    "data", "analytics", "engineering",
    "pipeline", "etl", "elt",
    "warehouse", "lakehouse",
    "Databricks", "Snowflake",
    "bigquery", "redshift"
    ]
    DATA_EXCLUDE = ["survey", "poll", "census", "government data"]

    for article in data["articles"]:
        url = article.get("url")
        if not url or url in posted or url in global_posted:
            continue

        text = f"{article.get('title','').lower()} {article.get('description','').lower()}"

        if any(x in text for x in GLOBAL_EXCLUDE):
            continue

        if domain == "ai":
            if not any(x in text for x in AI_REQUIRED):
                continue
            if any(x in text for x in AI_EXCLUDE):
                continue

        if domain == "cloud" and not any(x in text for x in CLOUD_REQUIRED):
            continue

        if domain == "data":
            if not any(x in text for x in DATA_REQUIRED):
                continue
            if any(x in text for x in DATA_EXCLUDE):
                continue

        if not article.get("urlToImage"):
            continue

        return {
            "title": article["title"],
            "summary": clean_summary(article["description"])[:300],
            "image_url": article["urlToImage"],
            "link": url
        }

    return None

# =========================
# LINKEDIN API
# =========================

def register_upload():
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
        "https://api.linkedin.com/v2/assets?action=registerUpload",
        headers={**HEADERS, "Content-Type": "application/json"},
        json=payload
    )
    data = r.json()["value"]
    return (
        data["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"],
        data["asset"]
    )


def upload_image(upload_url, image_url):
    image = requests.get(image_url).content
    r = requests.put(
        upload_url,
        headers={
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/octet-stream"
        },
        data=image
    )
    return r.status_code in (200, 201)


def create_post(domain, news, asset):
    cfg = DOMAIN_CONFIGS[domain]

    text = (
        f"{cfg['title']} | {datetime.now().strftime('%d %b %Y')}\n\n"
        f"📰 {news['title']}\n\n"
        f"{news['summary']}\n\n"
        f"🔗 Read more: {news['link']}\n\n"
        f"{cfg['hashtags']}"
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
                    "title": {"text": cfg["title"]}
                }]
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
    }

    r = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers={**HEADERS, "Content-Type": "application/json"},
        json=payload
    )

    if r.status_code != 201 or "id" not in r.json():
        print("❌ LinkedIn post failed:", r.text)
        return False

    print("📌 LinkedIn post ID:", r.json()["id"])
    return True

# =========================
# MAIN
# =========================

if __name__ == "__main__":
    rotation_index = load_rotation_index()
    global_posted = load_json_set(GLOBAL_POSTED_FILE)

    posted_successfully = False

    for i in range(len(DOMAINS)):
        domain_index = (rotation_index + i) % len(DOMAINS)
        domain = DOMAINS[domain_index]

        print(f"🔄 Trying domain: {domain}")

        domain_file = f"posted_articles_{domain}.json"
        domain_posted = load_json_set(domain_file)

        news = fetch_news(domain, domain_posted, global_posted)
        if not news:
            print(f"No article for {domain}, moving on.")
            continue

        upload_url, asset = register_upload()
        if not upload_image(upload_url, news["image_url"]):
            print("Image upload failed, trying next domain.")
            continue

        if create_post(domain, news, asset):
            domain_posted.add(news["link"])
            global_posted.add(news["link"])

            save_json_set(domain_file, domain_posted)
            save_json_set(GLOBAL_POSTED_FILE, global_posted)
            save_rotation_index(domain_index + 1)

            print(f"✅ Confirmed LinkedIn post for domain: {domain}")
            posted_successfully = True
            break

    if not posted_successfully:
        print("❌ No article posted in this run.")

