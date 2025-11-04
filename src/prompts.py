"""Prompt templates and builders for LLM calls.

Keep prompt text centralized so it's easy to iterate and test.
"""
from typing import List


def build_analyze_comments_prompt(sample_texts: List[str]) -> str:
    """Return the prompt string used to analyze YouTube comments about a company's stock/investment.

    sample_texts: small list of comment texts already truncated as needed.
    """
    joined = "\n---\n".join(sample_texts)
    prompt = f"""<task_description>
You are a senior financial analyst specializing in sentiment analysis and behavioral finance. Your task is to analyze investor sentiment from YouTube comments posted on investment-focused videos about a company's stock.
</task_description>

<analysis_objectives>
Your analysis must focus on the following key areas:
1. Overall investment sentiment (bullish, bearish, or neutral)
2. Specific financial concerns or opportunities mentioned by investors
3. Price predictions, valuation opinions, and technical analysis references
4. Recurring investment themes and narrative patterns
5. Risk factors and catalysts discussed by the community
</analysis_objectives>

<output_requirements>
Produce a valid JSON object with the following structure:
- sentiment: string (must be "bullish", "bearish", or "neutral" - represents overall investment sentiment)
- themes: array of 3-6 strings (key investment themes, concerns, or opportunities discussed repeatedly)
- representative_quotes: array of exactly 3 strings (most insightful and articulate quotes about investment outlook or financial analysis)
- summary: string (2-3 sentences summarizing the overall investor sentiment, key themes, and notable consensus or disagreements)
</output_requirements>

<quality_standards>
- Focus on substantive financial insights, not generic hype or spam
- Identify concrete themes like valuation concerns, growth catalysts, competitive positioning, management quality, etc.
- Select quotes that demonstrate thoughtful analysis or unique perspectives
- Ensure summary captures both sentiment and reasoning behind it
- Distinguish between informed analysis and speculation
</quality_standards>

<youtube_comments>
{joined}
</youtube_comments>

<output_format>
Return ONLY a valid JSON object with no additional text or explanation. Format:
{{
  "sentiment": "bullish|bearish|neutral",
  "themes": ["theme1", "theme2", "theme3", ...],
  "representative_quotes": ["quote1", "quote2", "quote3"],
  "summary": "2-3 sentence summary"
}}
</output_format>"""
    return prompt


def build_compare_prompt(yahoo_summary: str, web_summary: str, social_summaries: List[dict], metrics_text: str = "") -> str:
    """Return the prompt string used to combine sources into a comprehensive investment analysis.

    social_summaries: list of dicts with keys source, summary, sentiment, themes
    metrics_text: pre-formatted textual summary of numeric/derived metrics (market cap, P/E, returns, MAs, volatility)
    """
    # Handle social media data (may be empty if YouTube API fails)
    if social_summaries:
        social_text = "\n\n".join([
            f"<source name='{s.get('source')}'>\n<summary>{s.get('summary')}</summary>\n<sentiment>{s.get('sentiment')}</sentiment>\n<themes>{s.get('themes')}</themes>\n</source>"
            for s in social_summaries
        ])
    else:
        social_text = "<note>No YouTube/social media data available - API may be unavailable or quota exceeded</note>"

    # Determine which sections to emphasize based on available data
    sentiment_section_title = (
        "Market Sentiment & Public Perception" 
        if social_summaries 
        else "Market Context"
    )
    
    sentiment_section_description = (
        "Synthesize YouTube/social media sentiment, themes, and investor concerns. Identify consensus views and divergent opinions."
        if social_summaries
        else "Provide general market conditions and industry trends based on available data. Discuss competitive landscape and sector dynamics."
    )

    prompt = f"""<role>
You are a senior investment analyst at a top-tier financial institution with 15+ years of experience in equity research. You are preparing a comprehensive company analysis report for institutional investors and high-net-worth clients.
</role>

<task>
Synthesize the provided data sources into a detailed, professional investment analysis report. Your analysis must be data-driven, balanced, and actionable.
</task>

<report_structure>
Your report must include exactly 8 sections with the following titles and content:

<section number="1" title="Executive Summary">
- 2-3 concise sentences capturing the company's current state
- Include company name, ticker, industry, and key investment thesis
- Highlight the most critical insight or finding from your analysis
</section>

<section number="2" title="Company Overview">
- Describe what the company does and its core business model
- Explain industry position, market share, and competitive advantages
- Identify key products/services and revenue streams
- Note any recent strategic shifts or business developments
</section>

<section number="3" title="Financial Health & Metrics">
- Create a markdown table with key financial metrics (P/E ratio, market cap, revenue growth, profit margins, debt levels, ROE, etc.)
- Interpret valuation: Is the stock overvalued, undervalued, or fairly valued?
- Analyze growth trajectory and financial stability
- Compare metrics to industry averages where relevant
- Discuss any red flags or exceptional strengths in the numbers
</section>

<section number="4" title="Recent Performance">
- Analyze recent price trends and momentum
- Discuss moving averages and technical indicators
- Include a markdown table with recent price data if relevant (52-week high/low, current price, % changes)
- Explain what's driving recent performance (earnings, news, sector trends)
- Assess whether current price levels present opportunity or risk
</section>

<section number="5" title="{sentiment_section_title}">
- {sentiment_section_description}
- Highlight specific concerns or opportunities mentioned by investors/market
- Note any disconnect between public perception and fundamental data
</section>

<section number="6" title="Key Concerns & Risks">
Present at least 5 specific risk factors as bullet points:
- Focus on concrete financial metrics, business fundamentals, and market challenges
- Include both company-specific and macroeconomic risks
- Quantify risks where possible (e.g., "high debt-to-equity ratio of X")
- Consider regulatory, competitive, operational, and market risks
</section>

<section number="7" title="Positive Signals & Opportunities">
Present at least 5 specific positive factors as bullet points:
- Highlight growth catalysts, competitive advantages, and value opportunities
- Reference specific metrics, initiatives, or market trends
- Include both near-term catalysts and long-term structural advantages
- Note any asymmetric risk/reward scenarios
</section>

<section number="8" title="Investment Outlook">
- Provide a 3-4 sentence conclusion with clear perspective
- Offer distinct short-term (0-12 months) and long-term (1-5 years) views
- Specify investor profiles who should consider this investment (growth, value, income, etc.)
- Give a nuanced recommendation without being overly promotional or pessimistic
</section>

</report_structure>

<formatting_requirements>
- Use markdown formatting throughout
- Use exact section titles as specified above (including numbering)
- Use markdown tables where appropriate to present financial data clearly
- Use bullet points for lists (-, not *)
- Use **bold** for emphasis on key metrics or terms
- Ensure proper spacing between sections
</formatting_requirements>

<writing_guidelines>
<style>
- Write in a professional, analytical tone suitable for institutional investors
- Be specific and quantitative - cite actual numbers, percentages, and metrics
- Avoid generic statements; every claim should tie to data
- Present balanced analysis showing both bull and bear perspectives
- Use precise financial terminology
</style>

<prohibitions>
- DO NOT cite sources in parentheses (no Yahoo, Wikipedia, Metrics, YouTube citations)
- DO NOT use promotional or sales language
- DO NOT make definitive price predictions
- DO NOT ignore contradictory data
- Present insights as your own integrated professional analysis
</prohibitions>

<quality_standards>
- Ensure all 8 sections are present and substantive
- Provide actionable insights, not just data summary
- Connect different data points to form coherent narrative
- Acknowledge uncertainty and data limitations where relevant
- If certain data is unavailable, focus analysis on available information without speculation
</quality_standards>
</writing_guidelines>

<data_sources>

<yahoo_business_summary>
{yahoo_summary or "(no yahoo summary available)"}
</yahoo_business_summary>

<wikipedia_summary>
{web_summary or "(no web summary available)"}
</wikipedia_summary>

<financial_metrics>
{metrics_text or "(no metrics available)"}
</financial_metrics>

<social_media_analysis>
{social_text}
</social_media_analysis>

</data_sources>

<output_instruction>
Generate a comprehensive investment analysis report following the structure and guidelines above. Use well-formatted markdown. Be thorough, insightful, and actionable.
</output_instruction>"""
    
    return prompt
