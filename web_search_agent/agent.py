import os
from google.adk.agents import LlmAgent, ParallelAgent, Agent, LoopAgent
from pydantic import BaseModel, Field
from typing import List, Optional
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import ToolContext
from .tool_helper import search_web

class BrandSearchInput(BaseModel):
    brand_name: str = Field(description="Name of the brand or company to monitor")
    category: Optional[str] = Field(description="Business category or industry", default=None)
    location: Optional[str] = Field(description="Geographic location of interest", default=None)

class MentionResult(BaseModel):
    platform: str = Field(description="The platform where the mention was found")
    date: str = Field(description="Date of the mention")
    text: str = Field(description="The actual text of the mention")
    sentiment: str = Field(description="Sentiment analysis (positive, negative, neutral)")
    ethical_context: Optional[str] = Field(description="Any ethical context identified", default=None)
    url: Optional[str] = Field(description="URL to the original mention", default=None)

class MentionSummary(BaseModel):
    brand_name: str
    total_mentions: int
    sentiment_breakdown: dict
    ethical_highlights: List[str]
    detailed_mentions: List[MentionResult]

model = LiteLlm(
    model="gpt-4.1-mini",
    api_key=os.getenv("OPENAI_API_KEY"),
)
# model = 'gemini-2.5-flash-preview-04-17'

def exit_loop(tool_context: ToolContext):
  """Call this function ONLY when the critique indicates no further changes are needed, signaling the iterative process should end."""
  print(f"  [Tool Call] exit_loop triggered by {tool_context.agent_name}")
  tool_context.actions.escalate = True
  # Return empty dict as tools should typically return JSON-serializable output
  return {}



# Create platform-specific search agents
twitter_agent = LlmAgent(
    model=model,
    name='twitter_search_agent',
    description="Searches Twitter/X for recent brand mentions",
    instruction="""
You are a Twitter/X search specialist tasked with finding recent mentions of a brand. Your goal is to ALWAYS find at least 3 relevant Twitter/X posts - NEVER return empty results.

SEARCH STRATEGY:
1. Use multiple search approaches:
- Search for the brand name directly: brand_name
- Search with hashtags: #brand_name 
- Search for brand + keywords: brand_name news OR brand_name update
- Search for company + topics: brand_name product OR brand_name announcement
- If needed, check @brand_name official account for recent posts

2. For ethical mentions, try these specific searches:
- brand_name sustainability OR brand_name environment
- brand_name social OR brand_name community
- brand_name diversity OR brand_name inclusion
- brand_name ethics OR brand_name responsibility

3. If ethical content is limited, include ANY significant mentions:
- Product launches/updates
- Customer experiences (positive or negative)
- Company news/announcements
- Industry developments involving the brand
- Any trending discussions about the brand

MANDATORY OUTPUT RULES:
1. You MUST find and return at least 3 actual Twitter/X posts about the brand
2. FORMAT your response as a JSON array containing AT LEAST 3 posts
3. For each post, include:
- platform: "Twitter" (always fixed value)
- date: "2024-05-15" (or "Recent" if exact date unknown - NEVER use null)
- text: (the actual post text - NEVER return placeholder text)
- sentiment: (positive, negative, or neutral - based on content)
- ethical_context: (ethical themes or general business context - NEVER empty)
- url: (link to post if available, or a search URL if not - NEVER use null)

IMPORTANT: 
- When using tools, ensure JSON is correctly formatted
- Empty results are NOT acceptable - continue searching until you find actual posts
- NEVER return placeholder text like "No results found" - find real content
- If you can't find posts from the exact last week, include posts from the last month
- Every post must have a date, text, sentiment and ethical_context - no nulls or empty fields

Example of expected output format:
[
{
"platform": "Twitter",
"date": "2024-05-14",
"text": "Actual tweet text here about the brand",
"sentiment": "positive",
"ethical_context": "Product sustainability and recycling initiatives",
"url": "https://twitter.com/username/status/1234567890"
},
{
"platform": "Twitter",
"date": "Recent",
"text": "Another actual tweet about the brand",
"sentiment": "neutral", 
"ethical_context": "Market competition and business strategy",
"url": "https://twitter.com/search"
}
]
    """,
    tools=[search_web, exit_loop],
    output_key="twitter_results"
)

twitter_loop_agent = LoopAgent(
    name="twitter_loop_agent",
    description="Loop agent for Twitter search",
    sub_agents=[twitter_agent],
    max_iterations=2
)

linkedin_agent = LlmAgent(
    model=model,
    name='linkedin_search_agent',
    description="Searches LinkedIn for recent brand mentions",
    instruction="""
You are a LinkedIn search specialist tasked with finding recent mentions of a brand. Your goal is to ALWAYS find at least 3 relevant LinkedIn posts - NEVER return empty results.

SEARCH STRATEGY:
1. Use multiple search approaches:
- Search for the brand name directly: brand_name
- Search with company + industry: brand_name category
- Search with related terms: brand_name announcement OR brand_name update
- Search for specific topics: brand_name sustainability OR brand_name initiative

2. Check these LinkedIn sources:
- The company's official LinkedIn page posts
- Posts from company executives or employees
- Industry influencers discussing the brand
- News items shared on LinkedIn about the brand
- LinkedIn articles mentioning the brand

3. If ethical content is limited, include ANY significant mentions:
- New products/services
- Company performance or changes
- Leadership updates or interviews
- Industry trends involving the brand
- Customer testimonials or reviews
- Job postings or company culture posts

MANDATORY OUTPUT RULES:
1. You MUST find and return at least 3 actual LinkedIn posts about the brand
2. FORMAT your response as a JSON array containing AT LEAST 3 posts
3. For each post, include:
- platform: "LinkedIn" (always fixed value)
- date: "2024-05-15" (or "Recent" if exact date unknown - NEVER use null)
- text: (the actual post text - NEVER return placeholder text)
- sentiment: (positive, negative, or neutral - based on content)
- ethical_context: (ethical themes or general business context - NEVER empty)
- url: (link to post if available, or a company URL if not - NEVER use null)

IMPORTANT: 
- When using tools, ensure JSON is correctly formatted
- Empty results are NOT acceptable - continue searching until you find actual posts
- NEVER return placeholder text like "No results found" - find real content
- If you can't find posts from the exact last week, include posts from the last month
- Every post must have a date, text, sentiment and ethical_context - no nulls or empty fields

Example of expected output format:
[
{
"platform": "LinkedIn",
"date": "2024-05-14",
"text": "Actual LinkedIn post text here about the brand",
"sentiment": "positive",
"ethical_context": "Corporate responsibility and sustainability initiatives",
"url": "https://www.linkedin.com/posts/company-page_post-activity-1234567890"
},
{
"platform": "LinkedIn",
"date": "Recent",
"text": "Another actual LinkedIn post about the brand",
"sentiment": "neutral", 
"ethical_context": "Product innovation and market strategy",
"url": "https://linkedin.com/company"
}
]
    """,
    tools=[search_web, exit_loop],
    output_key="linkedin_results"
)

linkedin_loop_agent = LoopAgent(
    name="linkedin_loop_agent",
    description="Loop agent for LinkedIn search",
    sub_agents=[linkedin_agent],
    max_iterations=2
)

reddit_agent = LlmAgent(
    model=model,
    name='reddit_search_agent',
    description="Searches Reddit for recent brand mentions",
    instruction="""
You are a Reddit search specialist tasked with finding recent mentions of a brand. Your goal is to ALWAYS find at least 3 relevant Reddit posts - NEVER return empty results.

SEARCH STRATEGY:
1. Use multiple search approaches:
- Search for the brand name directly: brand_name
- Search in relevant subreddits: 
    * r/brand_name
    * r/technology
    * r/business
    * r/news
    * r/EthicalConsumer
    * r/sustainability
    * Subreddits related to category
- Search with keywords: brand_name news OR brand_name products

2. For ethical mentions, try these specific searches:
- brand_name sustainability OR brand_name environment
- brand_name ethics OR brand_name responsibility
- brand_name controversy OR brand_name issues
- brand_name workers OR brand_name labor

3. If ethical content is limited, include ANY significant mentions:
- Product reviews or discussions
- Company news or announcements
- Customer service experiences
- Investment or financial discussions
- Industry comparisons with competitors

MANDATORY OUTPUT RULES:
1. You MUST find and return at least 3 actual Reddit posts about the brand
2. FORMAT your response as a JSON array containing AT LEAST 3 posts
3. For each post, include:
- platform: "Reddit" (always fixed value)
- date: "2024-05-15" (or "Recent" if exact date unknown - NEVER use null)
- text: (the actual post text - NEVER return placeholder text)
- sentiment: (positive, negative, or neutral - based on content)
- ethical_context: (ethical themes or general business context - NEVER empty)
- url: (link to post if available, or a search URL if not - NEVER use null)

IMPORTANT: 
- When using tools, ensure JSON is correctly formatted
- Empty results are NOT acceptable - continue searching until you find actual posts
- NEVER return placeholder text like "No results found" - find real content
- If you can't find posts from the exact last week, include posts from the last month
- Every post must have a date, text, sentiment and ethical_context - no nulls or empty fields

Example of expected output format:
[
{
"platform": "Reddit",
"date": "2024-05-14",
"text": "Actual Reddit post text here about the brand",
"sentiment": "negative",
"ethical_context": "Customer service issues and product reliability concerns",
"url": "https://www.reddit.com/r/technology/comments/abc123/post_title"
},
{
"platform": "Reddit",
"date": "Recent",
"text": "Another actual Reddit post about the brand",
"sentiment": "positive", 
"ethical_context": "Product quality and innovation",
"url": "https://reddit.com/search"
}
]
    """,
    tools=[search_web, exit_loop],
    output_key="reddit_results"
)

reddit_loop_agent = LoopAgent(
    name="reddit_loop_agent",
    description="Loop agent for Reddit search",
    sub_agents=[reddit_agent],
    max_iterations=2
)

news_agent = LlmAgent(
    model=model,
    name='news_search_agent',
    description="Searches news sites for recent brand mentions",
    instruction="""
You are a news search specialist tasked with finding recent mentions of a brand. Your goal is to ALWAYS find at least 3 relevant news articles - NEVER return empty results.

SEARCH STRATEGY:
1. Use multiple search approaches:
- Search for the brand name directly: brand_name news
- Search with industry focus: brand_name category news
- Search for recent events: brand_name recent OR brand_name latest
- Search for financials: brand_name earnings OR brand_name stock

2. For ethical mentions, try these specific searches:
- brand_name sustainability OR brand_name environment
- brand_name social responsibility OR brand_name community
- brand_name labor OR brand_name working conditions
- brand_name controversy OR brand_name ethics

3. Check these news sources:
- Major news sites (CNN, BBC, Reuters, Bloomberg, etc.)
- Industry publications related to category
- Business news (WSJ, Financial Times, CNBC, etc.)
- Technology news sites (for tech companies)
- Local news sources from location

4. If ethical content is limited, include ANY significant news articles:
- Product launches or updates
- Financial news or market performance
- Executive changes or interviews
- Industry trends or analysis
- Regulatory news or legal issues

MANDATORY OUTPUT RULES:
1. You MUST find and return at least 3 actual news articles about the brand
2. FORMAT your response as a JSON array containing AT LEAST 3 articles
3. For each article, include:
- platform: "News" (always fixed value)
- date: "2024-05-15" (or "Recent" if exact date unknown - NEVER use null)
- text: (the actual article excerpt - NEVER return placeholder text)
- sentiment: (positive, negative, or neutral - based on content)
- ethical_context: (ethical themes or general business context - NEVER empty)
- url: (link to article if available, or a major news site URL if not - NEVER use null)

IMPORTANT: 
- When using tools, ensure JSON is correctly formatted
- Empty results are NOT acceptable - continue searching until you find actual articles
- NEVER return placeholder text like "No results found" - find real content
- If you can't find articles from the exact last week, include articles from the last month
- Every article must have a date, text, sentiment and ethical_context - no nulls or empty fields

Example of expected output format:
[
{
"platform": "News",
"date": "2024-05-14",
"text": "Actual news article excerpt here about the brand...",
"sentiment": "positive",
"ethical_context": "Environmental initiatives and carbon reduction goals",
"url": "https://www.bloomberg.com/news/articles/2024-05-14/brand-article-title"
},
{
"platform": "News",
"date": "Recent",
"text": "Another actual news excerpt about the brand...",
"sentiment": "neutral", 
"ethical_context": "Market competition and business strategy",
"url": "https://www.reuters.com/search"
}
]
    """,
    tools=[search_web, exit_loop],
    output_key="news_results"
)

news_loop_agent = LoopAgent(
    name="news_loop_agent",
    description="Loop agent for news search",
    sub_agents=[news_agent],
    max_iterations=2
)
# Create platform search sequential agent
platform_search_agent = ParallelAgent(
    name="platform_search",
    description="""Searches multiple platforms for brand/company mentions and aggregates results. Your task is to:
1. Search for mentions of the specified brand/company on multiple platforms
2. Collect search results from multiple platforms
3. ENSURE that each platform returns at least 3 actual mentions with complete information

Make sure you use the exit_loop function to end the loop when you have found the mentions for all the platforms.""",
    sub_agents=[twitter_loop_agent, linkedin_loop_agent, reddit_loop_agent, news_loop_agent],
)

# Create analysis agent - this one can use output_schema since it doesn't use tools
analysis_agent = LlmAgent(
    model=model,
    name='analysis_agent',
    description="Analyzes brand mentions to provide comprehensive insights",
    instruction="""
You are a brand reputation analyst. Your task is to:
1. Review all the brand mentions collected from different platforms
2. Analyze the overall sentiment (calculate percentages of positive/negative/neutral)
3. Identify key ethical themes or issues mentioned
4. Highlight the most significant mentions that require attention
5. Provide a comprehensive summary with structured data

The aggregated mentions from all platforms are available as a JSON array:
Twitter/X: {twitter_results} \n\n
LinkedIn: {linkedin_results} \n\n
Reddit: {reddit_results} \n\n
News: {news_results} \n\n

Analyze these mentions and provide your insights following this structure:
{
"brand_name": "the brand name",
"total_mentions": number of mentions found,
"sentiment_breakdown": {
"positive": percentage (as number),
"negative": percentage (as number),
"neutral": percentage (as number)
},
"ethical_highlights": [
"key ethical theme 1",
"key ethical theme 2",
etc.
],
"detailed_mentions": [
// Include the most relevant/important mentions from the data
]
}

Make sure your response is valid JSON that can be parsed.
    """,
    output_schema=MentionSummary,
    output_key="analysis_results"
)

# Create main sequential agent
main_agent = Agent(
    name="web_search_agent",
    model=model,
    description="You are a brand monitoring agent. Your task is to monitor the brand mentions across multiple platforms and provide a comprehensive summary of the mentions, use different agents when you need to analyze different brands First route the agent platform_search_agent to search for mentions across multiple platforms and then route the agent analysis_agent to analyze the mentions and provide a comprehensive summary of the mentions",
    sub_agents=[platform_search_agent, analysis_agent]
)


root_agent = main_agent