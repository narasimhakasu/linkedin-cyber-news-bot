import os
import json
import requests
from datetime import datetime, timedelta

# =========================
# DOMAIN ROTATION CONFIG
# =========================

DOMAINS = ["cybersecurity", "cloud", "ai", "data"]
ROTATION_FILE = "rotation_state.json"

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
# ROTATION STATE
# =========================

def load_rotation_index():
    if not os.path.exists(ROTATION_FILE):
        return 0
    with open(ROTATION_FILE, "r") as f:
        return json.load(f).get("index", 0)


def save_rotation_index(index):
    with open(ROTATION_FILE, "w") as f:
        json.dump({"index": index}, f)

# =========================
# POSTED STORAGE
# =========================

def load_posted(file):
    if not os.path.exists(file):
        return set()
    with open(file, "r") as f:
        return set(json.load(f))


def save_posted(file, posted):
    with open(file, "w") as f:
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
# FETCH NEWS (ALL DOMAINS TIGHT)
# =========================

def fetch_news(domain, posted):
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

    r = requests.get(NEWS_API_URL, params=params)
    data = r.json()

    if not data.get("articles"):
        return None

    GLOBAL_EXCLUDE = [
        "arrest", "interpol", "europol", "sentenced",
        "trial", "court", "gang", "police",
        "election", "politics", "minister"
    ]

    AI_REQUIRED = [
        "model", "ml", "machine learning", "llm",
        "neural", "training", "inference",
        "dataset", "algorithm", "software",
        "platform", "enterprise"
    ]

    AI_EXCLUDE = [
        "alien", "ufo", "extraterrestrial",
        "nasa", "space", "astronomy",
        "astrophysics", "interstellar", "seti"
    ]

    CLOUD_REQUIRED = [
        "aws", "azure", "gcp", "cloud",
        "infrastructure", "service",
        "outage", "downtime", "region"
    ]

    DATA_REQUIRED = [
        "pipeline", "etl", "elt", "warehouse",
        "databricks", "snowflake", "bigquery",
        "analytics", "data platform"
    ]

    DATA_EXCLUDE = [
        "survey", "poll", "report says",
        "government data", "census",
        "statistics office"
    ]

    for article in data["articles"]:
        url = article.get("url")
        if not url or url in posted:
            continue

        text = f"{article.get('title','').lower()} {article.get('description','').lower()}"

        if any(x in text for x in GLOBAL_EXCLUDE):
            continue

        if domain == "ai":
            if not any(x in text for x in AI_REQUIRED):
                continue
            if any(x in text for x in AI_EXCLUDE):
                continue

        if domain == "cloud":
            if not any(x in text for x in CLOUD_REQUIRED):
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
# LINKEDIN HELPERS
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

    r = requests.post(url, headers={**HEADERS, "Content-Type": "application/json"}, json=payload)
    data = r.json()["value"]
    upload_url = data["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
    return upload_url, data["asset"]


def upload_image(upload_url, image_url):
    image = requests.get(image_url).content
    r = requests.put(upload_url, headers={
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/octet-stream"
    }, data=image)
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
    return r.status_code == 201

# =========================
# MAIN
# =========================

if __name__ == "__main__":
    rotation_index = load_rotation_index()
    total_domains = len(DOMAINS)

    posted_successfully = False

    for attempt in range(total_domains):
        domain_index = (rotation_index + attempt) % total_domains
        domain = DOMAINS[domain_index]

        print(f"🔄 Trying domain: {domain}")

        posted_file = f"posted_articles_{domain}.json"
        posted = load_posted(posted_file)

        news = fetch_news(domain, posted)
        if not news:
            print(f"No article found for {domain}, trying next domain.")
            continue

        upload_url, asset = register_upload()
        if not upload_image(upload_url, news["image_url"]):
            print("Image upload failed, trying next domain.")
            continue

        if create_post(domain, news, asset):
            posted.add(news["link"])
            save_posted(posted_file, posted)

            # ✅ advance rotation to NEXT domain after the one we posted
            save_rotation_index(domain_index + 1)

            print(f"✅ Posted successfully for domain: {domain}")
            posted_successfully = True
            break

        else:
            print("Post failed, trying next domain.")

    if not posted_successfully:
        print("❌ No articles posted for any domain.")


