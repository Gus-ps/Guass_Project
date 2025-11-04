"""Consolidated backend functions: ticker validation, fetchers (Yahoo, Wikipedia, Reddit, YouTube),
Anthropic/OpenAI wrappers, analysis and orchestration.

This file intentionally groups the main functions used by the service so endpoints can import
from a single place.
"""
from typing import List, Tuple
import json
import requests
import yfinance as yf
from bs4 import BeautifulSoup
from datetime import datetime
import math
import statistics

# Local config and prompts
from src import config
from src import prompts


# Simple logger
import logging
logger = logging.getLogger("llm_stock_insights")
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def safe_truncate(text, max_len=2000):
    if not text:
        return text
    return text if len(text) <= max_len else text[:max_len] + "..."


def validate_ticker(ticker: str) -> Tuple[bool, dict]:
    """Validate a ticker symbol and return structured metadata.

    Returns (valid, metadata_dict). metadata_dict contains keys:
      - message: human readable message
      - name: company name if found
      - info: raw yfinance info dict (may be empty)
    """
    t = yf.Ticker(ticker)
    try:
        info = t.info
    except Exception as e:
        logger.warning("yfinance failed to fetch info for %s: %s", ticker, e)
        return False, {"message": f"Failed to fetch ticker info: {e}", "info": {}}

    if not info:
        return False, {"message": f"Ticker {ticker} not found or no info available", "info": {}}

    name = info.get("longName") or info.get("shortName")
    if not name:
        return False, {"message": f"Ticker {ticker} appears invalid (no company name found)", "info": info}

    metadata = {
        "message": "ok",
        "name": name,
        "info": info,
    }
    return True, metadata


def fetch_yahoo_company(ticker: str) -> dict:
    """Fetch basic company data from Yahoo via yfinance.
    
    Returns dict with keys: summary, info, history (last 90 days)
    """
    logger.info("Fetching Yahoo Finance data for ticker: %s", ticker)
    t = yf.Ticker(ticker)
    result = {"info": {}, "summary": "", "history": None}
    try:
        info = t.info or {}
        result["info"] = info
        result["summary"] = info.get("longBusinessSummary") or info.get("shortBusinessSummary") or ""
        logger.info("Successfully fetched Yahoo info for %s (company: %s)", ticker, info.get("longName", "Unknown"))
        
        hist = t.history(period="90d")
        if hist is not None and not hist.empty:
            # Convert Timestamp objects to ISO strings for JSON serialization
            hist_reset = hist.reset_index()
            for col in hist_reset.columns:
                if hist_reset[col].dtype == 'datetime64[ns]' or str(hist_reset[col].dtype).startswith('datetime'):
                    hist_reset[col] = hist_reset[col].astype(str)
            result["history"] = hist_reset.to_dict(orient="records")
            logger.info("Successfully fetched %d days of price history for %s", len(result["history"]), ticker)
        else:
            logger.warning("No price history available for %s", ticker)
    except Exception as e:
        logger.warning("Error fetching Yahoo data for %s: %s", ticker, e)
    return result


def extract_ticker_metadata_from_info(info: dict) -> dict:
    """Extract a compact metadata dict from yfinance info object."""
    if not info:
        return {}
    return {
        "name": info.get("longName") or info.get("shortName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "market_cap": info.get("marketCap"),
        "trailing_pe": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "beta": info.get("beta"),
        "website": info.get("website"),
        "country": info.get("country"),
    }


def fetch_wikipedia_summary(query: str) -> dict:
    """Fetch Wikipedia summary for a company using the MediaWiki API.
    
    Returns: {title, summary, url}
    """
    logger.info("Fetching Wikipedia summary for: %s", query)
    try:
        params = {"action": "query", "format": "json", "prop": "extracts|info", "exintro": True, "titles": query, "redirects": 1, "inprop": "url"}
        headers = {
            "User-Agent": "LLM-Stock-Insights/1.0 (Educational Project; Python/requests)"
        }
        r = requests.get("https://en.wikipedia.org/w/api.php", params=params, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        pages = data.get("query", {}).get("pages", {})
        for pid, page in pages.items():
            if "missing" in page:
                logger.warning("Wikipedia page not found for: %s", query)
                continue
            logger.info("Successfully fetched Wikipedia summary for: %s", page.get("title"))
            return {"title": page.get("title"), "summary": page.get("extract"), "url": page.get("fullurl")}
    except Exception as e:
        logger.warning("Wikipedia fetch failed for %s: %s", query, e)
    return {}



def fetch_youtube_comments_for_query(query: str, max_videos: int = 5, max_comments_per_video: int = 50) -> dict:
    """Fetch comments from top YouTube videos for a query using the YouTube Data API.
    
    Focuses on financial/investment analysis videos with relevant comments.
    Only fetches videos from the last 5 years.
    
    Requires YOUTUBE_API_KEY in environment. If not set, returns empty dict.
    Will try multiple videos and skip those with disabled comments.
    
    Returns dict with:
    - all_comments: flat list of all comment dicts
    - videos: list of dicts with {video_id, title, top_comments (filtered for relevance)}
    """
    if not config.YOUTUBE_API_KEY:
        logger.info("YOUTUBE_API_KEY not provided; skipping YouTube fetch")
        return {"all_comments": [], "videos": []}
    try:
        # Enhance query to target financial/investment content
        financial_query = f"{query} stock analysis investment earnings"
        logger.info("Searching YouTube for financial content: %s", financial_query)
        
        # Calculate date 5 years ago in RFC 3339 format
        from datetime import datetime, timedelta
        five_years_ago = (datetime.utcnow() - timedelta(days=365*5)).strftime('%Y-%m-%dT%H:%M:%SZ')
        
        search_url = "https://www.googleapis.com/youtube/v3/search"
        # Request more videos than we need so we have backups if some have disabled comments
        params = {
            "part": "snippet", 
            "q": financial_query, 
            "type": "video", 
            "maxResults": max_videos * 3, 
            "order": "relevance",  # Most relevant first
            "publishedAfter": five_years_ago,  # Only videos from last 5 years
            "key": config.YOUTUBE_API_KEY
        }
        logger.info("Filtering videos published after: %s", five_years_ago)
        r = requests.get(search_url, params=params, timeout=10)
        
        # Check for 403 errors specifically
        if r.status_code == 403:
            logger.warning("YouTube API returned 403 Forbidden - API key may be invalid or quota exceeded. Skipping YouTube data.")
            return {"all_comments": [], "videos": []}
            
        r.raise_for_status()
        videos = r.json().get("items", [])
        all_comments = []
        video_summaries = []
        videos_with_comments = 0
        
        for v in videos:
            # Stop if we've already gotten enough videos with comments
            if videos_with_comments >= max_videos:
                break
                
            vid = v["id"]["videoId"]
            video_title = v["snippet"].get("title", "Unknown")
            
            # Filter videos - prefer financial/investment content in title
            title_lower = video_title.lower()
            financial_keywords = ['stock', 'invest', 'earnings', 'analysis', 'buy', 'sell', 'financial', 'dividend', 'valuation', 'portfolio', 'market']
            
            is_financial = any(keyword in title_lower for keyword in financial_keywords)
            if not is_financial:
                logger.info("Skipping non-financial video: %s", video_title)
                continue
            
            logger.info("Trying to fetch comments from financial video: %s (ID: %s)", video_title, vid)
            
            comment_list = fetch_comments_for_video(vid, max_comments_per_video)
            
            if comment_list:
                # Filter comments for financial relevance
                relevant_comments = filter_financial_comments(comment_list)
                
                if relevant_comments:
                    all_comments.extend(relevant_comments)
                    videos_with_comments += 1
                    logger.info("Successfully fetched %d relevant comments (from %d total) from video: %s", 
                              len(relevant_comments), len(comment_list), video_title)
                    
                    # Store video info with top 3 RELEVANT comments
                    video_summaries.append({
                        "video_id": vid,
                        "title": video_title,
                        "url": f"https://www.youtube.com/watch?v={vid}",
                        "top_comments": relevant_comments[:3]  # First 3 relevant comments
                    })
                else:
                    logger.info("No relevant financial comments found in video: %s", video_title)
            # If no comments, continue to next video (don't break - just skip this one)
            
        logger.info("Total comments collected from %d videos: %d", videos_with_comments, len(all_comments))
        return {"all_comments": all_comments, "videos": video_summaries}
    except Exception as e:
        logger.warning("YouTube search failed for %s: %s - continuing without YouTube data", query, e)
        return {"all_comments": [], "videos": []}


def filter_financial_comments(comments: list) -> list:
    """Filter and rank comments to keep only those related to financial/investment topics.
    
    Uses keyword matching to identify relevant comments about:
    - Stock performance and analysis
    - Investment decisions (buy/sell/hold)
    - Financial metrics and valuations
    - Company earnings and fundamentals
    - Market sentiment and predictions
    
    Returns filtered list of relevant comment dicts, sorted by relevance score.
    """
    # Financial/investment keywords with importance weights
    high_value_keywords = {
        # Investment actions (high value)
        'buy': 3, 'sell': 3, 'hold': 2, 'invest': 2, 'investing': 2, 'portfolio': 2, 
        'bullish': 3, 'bearish': 3, 'long term': 3, 'short term': 2,
        # Valuation (high value)
        'overvalued': 3, 'undervalued': 3, 'valuation': 2, 'target price': 3, 
        'fair value': 2, 'intrinsic value': 3, 'discounted': 2,
        # Financial metrics (medium-high)
        'pe ratio': 2, 'p/e': 2, 'eps': 2, 'revenue': 2, 'earnings': 2, 'profit': 2, 
        'dividend': 2, 'yield': 2, 'cash flow': 2, 'debt': 2, 'margin': 2,
        # Analysis terms
        'fundamentals': 2, 'analysis': 1, 'forecast': 2, 'prediction': 2, 'outlook': 2,
        'due diligence': 3, 'dcf': 2, 'balance sheet': 2, 'income statement': 2,
        # Risk/reward
        'risk': 2, 'reward': 2, 'opportunity': 2, 'upside': 2, 'downside': 2,
        'conviction': 2, 'thesis': 2, 'moat': 3, 'competitive advantage': 3,
    }
    
    medium_value_keywords = [
        'stock', 'share', 'price', 'market cap', 'growth', 'quarter', 'quarterly',
        'report', 'guidance', 'beat', 'miss', 'estimate', 'market', 'sector',
        'revenue', 'sales', 'profit', 'margin', 'roi', 'return', 'performance',
        'financial', 'investor', 'shareholder', 'value', 'worth', 'evaluation',
        'recommendation', 'rating', 'upgrade', 'downgrade', 'catalyst', 'momentum'
    ]
    
    # Negative keywords (spam, off-topic)
    spam_keywords = [
        'subscribe', 'like and subscribe', 'check out my', 'click here', 
        'giveaway', 'free money', 'get rich', 'first!', 'early squad', 
        'notification squad', 'who else', 'anyone else', 'came here from',
        'full video', 'check my channel', 'dm me', 'contact me', 'crypto'
    ]
    
    scored_comments = []
    
    for comment in comments:
        text = comment.get('text', '').lower()
        
        # Minimum word count requirement (at least 10 words for substantive content)
        word_count = len(text.split())
        if word_count < 10:
            continue
        
        # Skip very short comments by character count
        if len(text.strip()) < 40:
            continue
        
        # Skip spam
        if any(spam in text for spam in spam_keywords):
            continue
        
        # Calculate relevance score
        score = 0
        
        # High value keywords
        for keyword, weight in high_value_keywords.items():
            if keyword in text:
                score += weight
        
        # Medium value keywords
        for keyword in medium_value_keywords:
            if keyword in text:
                score += 1
        
        # Bonus for longer, more detailed comments
        if word_count > 30:
            score += 1
        if word_count > 50:
            score += 2
        if word_count > 100:
            score += 2
        
        # Keep comment if it has meaningful financial content (score >= 4)
        if score >= 4:
            scored_comments.append({
                'comment': comment,
                'score': score,
                'word_count': word_count
            })
    
    # Sort by score (highest first)
    scored_comments.sort(key=lambda x: x['score'], reverse=True)
    
    # Extract just the comments
    relevant_comments = [item['comment'] for item in scored_comments]
    
    logger.info("Filtered %d/%d comments as financially relevant (top scores: %s, word counts: %s)", 
                len(relevant_comments), len(comments),
                [item['score'] for item in scored_comments[:5]],
                [item['word_count'] for item in scored_comments[:5]])
    
    return relevant_comments


def fetch_comments_for_video(video_id: str, max_comments: int = 50) -> list:
    """Helper to fetch comments for a single YouTube video."""
    if not config.YOUTUBE_API_KEY:
        return []
    try:
        comments = []
        url = "https://www.googleapis.com/youtube/v3/commentThreads"
        params = {"part": "snippet", "videoId": video_id, "maxResults": 100, "key": config.YOUTUBE_API_KEY}
        while len(comments) < max_comments:
            r = requests.get(url, params=params, timeout=10)
            
            # Provide detailed error info for debugging
            if r.status_code == 403:
                try:
                    error_data = r.json()
                    error_reason = error_data.get("error", {}).get("errors", [{}])[0].get("reason", "unknown")
                    logger.warning("YouTube video %s returned 403. Reason: %s (comments may be disabled or API quota exceeded)", video_id, error_reason)
                except:
                    logger.warning("YouTube video %s returned 403 Forbidden (comments may be disabled)", video_id)
                return []
            
            r.raise_for_status()
            data = r.json()
            for item in data.get("items", []):
                top = item["snippet"]["topLevelComment"]["snippet"]
                comments.append({"author": top.get("authorDisplayName"), "text": top.get("textDisplay")})
                if len(comments) >= max_comments:
                    break
            page = data.get("nextPageToken")
            if not page:
                break
            params["pageToken"] = page
        return comments
    except Exception as e:
        logger.warning("Failed to fetch comments for video %s: %s", video_id, e)
        return []


# Anthropic wrapper (SDK or HTTP)
try:
    from anthropic import Anthropic
    _anthropic_sdk = True
except Exception:
    _anthropic_sdk = False


def anthropic_complete(prompt: str, max_tokens: int = 512, temperature: float = 0.0) -> str:
    """Call Anthropic Messages API endpoint (SDK if installed, otherwise HTTP).
    
    Returns the text of the completion.
    """
    if not config.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not configured")
    
    if _anthropic_sdk:
        try:
            logger.info("Creating the Summary")
            client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
            # Use Messages API (current Anthropic format)
            message = client.messages.create(
                model=config.ANTHROPIC_MODEL,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return message.content[0].text
        except Exception as e:
            logger.error("Anthropic SDK call failed: %s", e)
            raise
    
    # fallback HTTP using Messages API
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": config.ANTHROPIC_API_KEY,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }
    payload = {
        "model": config.ANTHROPIC_MODEL,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}]
    }
    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
    r.raise_for_status()
    data = r.json()
    return data.get("content", [{}])[0].get("text", "")


# NOTE: OpenAI support removed — Anthropic-only design


def analyze_comments_with_anthropic(comments: List[dict], source_name: str) -> dict:
    """Use Anthropic to analyze a list of comments and return a structured summary.
    
    Expects comments to be a list of dicts with text/body fields.
    Returns dict with keys: source, summary, sentiment, themes, representative_quotes
    """
    if not comments:
        return {"source": source_name, "summary": "", "sentiment": "neutral", "themes": [], "representative": []}
    
    sample_texts = []
    for c in comments[:30]:
        text = c.get("body") or c.get("text") or ""
        sample_texts.append(safe_truncate(text, 800))

    prompt = prompts.build_analyze_comments_prompt(sample_texts)
    try:
        resp = anthropic_complete(prompt, max_tokens=800)
    except Exception as e:
        logger.warning("Anthropic call failed: %s", e)
        return {"source": source_name, "summary": "(analysis failed)", "sentiment": "unknown", "themes": [], "representative": []}

    try:
        text = resp.strip()
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            payload = json.loads(text[start : end + 1])
            payload.setdefault("source", source_name)
            return payload
    except Exception:
        logger.warning("Failed to parse Anthropic response as JSON; returning raw text")
    return {"source": source_name, "summary": resp}


def compute_company_metrics(yahoo: dict) -> dict:
    """Compute a small set of numeric/derived metrics from yahoo fetch.

    Returns a dict with keys like market_cap, trailing_pe, forward_pe, beta, pct_change (period), ma_short, ma_long, volatility, avg_volume
    """
    logger.info("Computing financial metrics from Yahoo data")
    info = yahoo.get("info") or {}
    history = yahoo.get("history") or []
    metrics = {}
    # Basic info-driven metrics
    metrics["market_cap"] = info.get("marketCap")
    metrics["trailing_pe"] = info.get("trailingPE")
    metrics["forward_pe"] = info.get("forwardPE")
    metrics["beta"] = info.get("beta")
    metrics["sector"] = info.get("sector")
    metrics["industry"] = info.get("industry")

    # Compute derived metrics from history (list of records with at least 'Close' and maybe 'Date')
    closes = []
    volumes = []
    for row in history:
        # row may have 'Close' or 'close' depending on source; be permissive
        c = row.get("Close") or row.get("close")
        v = row.get("Volume") or row.get("volume")
        try:
            if c is not None:
                closes.append(float(c))
            if v is not None:
                volumes.append(int(v))
        except Exception:
            continue

    if closes:
        # percent change over available window
        try:
            pct_change = (closes[-1] - closes[0]) / closes[0] * 100.0
        except Exception:
            pct_change = None
        metrics["period_pct_change"] = pct_change

        # moving averages (short=50 or available, long=200 or available)
        def moving_average(values, window):
            if len(values) < window:
                return None
            return sum(values[-window:]) / window

        metrics["ma_50"] = moving_average(closes, 50) or moving_average(closes, min(10, len(closes)))
        metrics["ma_200"] = moving_average(closes, 200) or moving_average(closes, min(50, len(closes)))

        # volatility as std dev of daily returns (percent)
        returns = []
        for i in range(1, len(closes)):
            try:
                returns.append((closes[i] - closes[i - 1]) / closes[i - 1])
            except Exception:
                continue
        if returns:
            vol = statistics.pstdev(returns) * math.sqrt(252)  # annualized approx
            metrics["volatility_annual_approx"] = vol
        else:
            metrics["volatility_annual_approx"] = None

    if volumes:
        metrics["avg_volume"] = sum(volumes) / len(volumes)

    return metrics


def format_metrics_text(metrics: dict) -> str:
    """Format the metrics dict into a readable short text block for inclusion in prompts/reports."""
    if not metrics:
        return "(no metrics available)"
    lines = []
    if metrics.get("sector"):
        lines.append(f"Sector: {metrics.get('sector')}, Industry: {metrics.get('industry')}")
    mc = metrics.get("market_cap")
    if mc is not None:
        # human-readable market cap
        try:
            if mc >= 1_000_000_000_000:
                mc_str = f"${mc/1_000_000_000_000:.2f}T"
            elif mc >= 1_000_000_000:
                mc_str = f"${mc/1_000_000_000:.2f}B"
            elif mc >= 1_000_000:
                mc_str = f"${mc/1_000_000:.2f}M"
            else:
                mc_str = f"${mc}"
        except Exception:
            mc_str = str(mc)
        lines.append(f"Market cap: {mc_str}")
    if metrics.get("trailing_pe") is not None:
        lines.append(f"Trailing P/E: {metrics.get('trailing_pe')}")
    if metrics.get("forward_pe") is not None:
        lines.append(f"Forward P/E: {metrics.get('forward_pe')}")
    if metrics.get("beta") is not None:
        lines.append(f"Beta: {metrics.get('beta')}")
    if metrics.get("period_pct_change") is not None:
        lines.append(f"Price change over sample: {metrics.get('period_pct_change'):.2f}%")
    if metrics.get("ma_50") is not None:
        lines.append(f"MA-50 (approx): {metrics.get('ma_50'):.2f}")
    if metrics.get("ma_200") is not None:
        lines.append(f"MA-200 (approx): {metrics.get('ma_200'):.2f}")
    if metrics.get("volatility_annual_approx") is not None:
        lines.append(f"Approx annual volatility (std): {metrics.get('volatility_annual_approx'):.2%}")
    if metrics.get("avg_volume") is not None:
        lines.append(f"Avg volume (sample): {int(metrics.get('avg_volume'))}")

    return "\n".join(lines)


def compare_and_summarize(yahoo: dict, web: dict, social_summaries: List[dict]) -> dict:
    """Use Anthropic to combine sources and produce a markdown opinion.

    Returns a dict with keys:
      - markdown: the raw markdown string returned by the LLM
      - source: which LLM produced it
      - inputs: small summary of the inputs used (yahoo_summary, web_summary, metrics)
    """
    yahoo_summary = yahoo.get("summary") or (yahoo.get("info", {}).get("longBusinessSummary") if yahoo.get("info") else "")
    web_summary = web.get("summary") if web else ""

    # metrics_text may be attached to the yahoo dict by the caller
    metrics_text = yahoo.get("_metrics_text", "") if isinstance(yahoo, dict) else ""

    prompt = prompts.build_compare_prompt(yahoo_summary, web_summary, social_summaries, metrics_text=metrics_text)

    # Use Anthropic exclusively for comparator and return a structured result
    try:
        md = anthropic_complete(prompt, max_tokens=2048)
        return {"markdown": md, "source": "anthropic", "inputs": {"yahoo_summary": yahoo_summary, "web_summary": web_summary, "metrics_text": metrics_text}}
    except Exception as e:
        logger.warning("Anthropic comparator failed: %s", e)
        return {"markdown": "# Error\nLLM comparator failed to run.", "source": "anthropic", "inputs": {"yahoo_summary": yahoo_summary, "web_summary": web_summary, "metrics_text": metrics_text}, "error": str(e)}


def generate_company_report(ticker: str) -> dict:
    """Main orchestration: validate ticker, fetch sources, analyze social, compare and return structured report.

    Steps:
    1. Validate ticker
    2. Fetch data from Yahoo, Wikipedia, YouTube
    3. Analyze YouTube comments with Anthropic
    4. Compare all sources and generate markdown report with LLM
    5. Return structured dict
    """
    ok, meta = validate_ticker(ticker)
    if not ok:
        # return structured error
        return {"error": "ticker_validation_failed", "message": meta.get("message")}

    company_name = meta.get("name")
    logger.info("Validated ticker %s -> %s", ticker, company_name)

    yahoo = fetch_yahoo_company(ticker)
    web = fetch_wikipedia_summary(company_name)
    # Fetch from more videos (5) and more comments per video (100) to get better filtering
    yt_data = fetch_youtube_comments_for_query(company_name, max_videos=5, max_comments_per_video=100)
    
    # Extract comments and video info
    yt_comments = yt_data.get("all_comments", [])
    yt_videos = yt_data.get("videos", [])

    yt_analysis = analyze_comments_with_anthropic(yt_comments, "YouTube")

    # Compute numeric metrics and attach a formatted text block for the comparator
    metrics = compute_company_metrics(yahoo)
    metrics_text = format_metrics_text(metrics)
    # attach to yahoo dict so compare_and_summarize can retrieve it without changing many call sites
    yahoo["_metrics_text"] = metrics_text

    comparator_result = compare_and_summarize(yahoo, web, [yt_analysis])

    header = {
        "title": f"Company Insight Report: {company_name} ({ticker.upper()})",
    "sources": ["Yahoo Finance", "Wikipedia", "YouTube"],
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    # Final structured report
    report = {
        "ticker": ticker.upper(),
        "company_name": company_name,
        "metadata": extract_ticker_metadata_from_info(yahoo.get("info", {})),
        "yahoo": yahoo,
        "wikipedia": web,
        "social_analyses": [yt_analysis],
        "youtube_videos": yt_videos,  # Add video info with top comments
        "metrics": metrics,
        "metrics_text": metrics_text,
        "comparator": comparator_result,
        "header": header,
    }

    return report
