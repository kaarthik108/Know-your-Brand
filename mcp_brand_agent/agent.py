import os
from google.adk.agents import LlmAgent, ParallelAgent, LoopAgent, SequentialAgent
from pydantic import BaseModel
from typing import List, Dict, Literal
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import ToolContext
# from .tool_helper import search_web
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

class SentimentBreakdown(BaseModel):
    positive: float
    negative: float
    neutral: float

class PlatformSentiment(SentimentBreakdown):
    count: int

class WordCloudTheme(BaseModel):
    word: str
    weight: float

class Mention(BaseModel):
    date: str
    text: str
    sentiment: Literal["positive", "negative", "neutral"]
    ethical_context: str
    url: str

class PlatformMentions(BaseModel):
    name: Literal["Twitter", "LinkedIn", "Reddit", "News"]
    mentions: List[Mention]

class SinglePlatformAnalysisReport(BaseModel):
    brand_name: str
    platform_name: Literal["Twitter", "LinkedIn", "Reddit", "News"]
    total_mentions_on_platform: int
    platform_sentiment_breakdown: SentimentBreakdown
    ethical_highlights_on_platform: List[str]
    word_cloud_themes_on_platform: List[WordCloudTheme]
    mentions_on_platform: List[Mention]

class BrandSentimentReport(BaseModel):
    brand_name: str
    total_mentions: int
    overall_sentiment: SentimentBreakdown
    platform_sentiment: Dict[Literal["Twitter", "LinkedIn", "Reddit", "News"], PlatformSentiment]
    ethical_highlights: List[str]
    word_cloud_themes: List[WordCloudTheme]
    platforms: List[PlatformMentions]

# model_groq = LiteLlm(
#     model="groq/qwen-qwq-32b",
#     api_key=os.getenv("GROQ_API_KEY"),
# )
model_o4 = LiteLlm(
    model="gpt-4.1",
    api_key=os.getenv("OPENAI_API_KEY")
)
# model = 'gemini-2.5-flash-preview-04-17'

# model_qwen = LiteLlm(
#     model="together_ai/Qwen/Qwen2.5-72B-Instruct-Turbo",
#     api_key=os.getenv("TOGETHERAI_API_KEY"),
#     # max_tokens=93762
# )

search_web = MCPToolset(
    connection_params=StdioServerParameters(
                command='npx',
                args=["-y", "@brightdata/mcp"],
                env={
                    "API_TOKEN": os.getenv("MCP_TOKEN"),
                    "WEB_UNLOCKER_ZONE": "web_unlocker1",
                    # "BROWSER_AUTH": "SBR_USER:SBR_PASS"
                }
            )
)

model_gemini = "gemini-2.5-flash-preview-04-17"

def exit_loop(tool_context: ToolContext):
  """Call this function ONLY when the critique indicates no further changes are needed, signaling the iterative process should end."""
  print(f"  [Tool Call] exit_loop triggered by {tool_context.agent_name}")
  tool_context.actions.escalate = True
  # Return empty dict as tools should typically return JSON-serializable output
  return {}


# Create platform-specific search agents
twitter_agent = LlmAgent(
    model=model_o4,
    name='twitter_agent',
    description="Searches Twitter/X for brand mentions and provides analysis",
    instruction="""
Search for exactly 3 Twitter/X posts about the brand, then analyze and return structured data.

First, search using brand name, hashtags, and keywords from x.com domain only.

Then analyze the posts and return this JSON structure:
{
  "brand_name": "the brand name",
  "platform_name": "Twitter",
  "total_mentions_on_platform": 3,
  "platform_sentiment_breakdown": {
    "positive": 0.6,
    "negative": 0.3,
    "neutral": 0.1
  },
  "ethical_highlights_on_platform": [
    "key ethical theme 1",
    "key ethical theme 2"
  ],
  "word_cloud_themes_on_platform": [
    {"word": "theme_word", "weight": 8}
  ],
  "mentions_on_platform": [
    {
      "date": "actual date or Recent",
      "text": "actual post content",
      "sentiment": "positive/negative/neutral",
      "ethical_context": "relevant theme",
      "url": "post link or x.com domain"
    }
  ]
}

Extract 10+ significant words for word_cloud_themes_on_platform. Return only valid JSON.
    """,
    tools=[search_web],
    # output_schema=SinglePlatformAnalysisReport,
    output_key="twitter_results"
)

# twitter_loop_agent = LoopAgent(
#     name="twitter_loop_agent",
#     description="Loop agent for Twitter search",
#     sub_agents=[twitter_agent],
#     max_iterations=2
# )

linkedin_agent = LlmAgent(
    model=model_o4,
    name='linkedin_agent',
    description="Searches LinkedIn for brand mentions and provides analysis",
    instruction="""
Search for exactly 3 LinkedIn posts about the brand, then analyze and return structured data.

First, search company pages, executives, and industry posts from linkedin.com domain only.

Then analyze the posts and return this JSON structure:
{
  "brand_name": "the brand name",
  "platform_name": "LinkedIn",
  "total_mentions_on_platform": 3,
  "platform_sentiment_breakdown": {
    "positive": 0.6,
    "negative": 0.3,
    "neutral": 0.1
  },
  "ethical_highlights_on_platform": [
    "key ethical theme 1",
    "key ethical theme 2"
  ],
  "word_cloud_themes_on_platform": [
    {"word": "theme_word", "weight": 8}
  ],
  "mentions_on_platform": [
    {
      "date": "actual date or Recent",
      "text": "actual post content",
      "sentiment": "positive/negative/neutral",
      "ethical_context": "relevant theme",
      "url": "post link or linkedin.com domain"
    }
  ]
}

Extract 10+ significant words for word_cloud_themes_on_platform. Return only valid JSON.
    """,
    tools=[search_web],
    # output_schema=SinglePlatformAnalysisReport,
    output_key="linkedin_results"
)

# linkedin_loop_agent = LoopAgent(
#     name="linkedin_loop_agent",
#     description="Loop agent for LinkedIn search",
#     sub_agents=[linkedin_agent],
#     max_iterations=2
# )

reddit_agent = LlmAgent(
    model=model_gemini,
    name='reddit_agent',
    description="Searches Reddit for brand mentions and provides analysis",
    instruction="""
Search for exactly 3 Reddit posts about the brand, then analyze and return structured data.

First, search relevant subreddits and brand discussions from reddit.com domain only.

Then analyze the posts and return this JSON structure:
{
  "brand_name": "the brand name",
  "platform_name": "Reddit",
  "total_mentions_on_platform": 3,
  "platform_sentiment_breakdown": {
    "positive": 0.6,
    "negative": 0.3,
    "neutral": 0.1
  },
  "ethical_highlights_on_platform": [
    "key ethical theme 1",
    "key ethical theme 2"
  ],
  "word_cloud_themes_on_platform": [
    {"word": "theme_word", "weight": 8}
  ],
  "mentions_on_platform": [
    {
      "date": "actual date or Recent",
      "text": "actual post content",
      "sentiment": "positive/negative/neutral",
      "ethical_context": "relevant theme",
      "url": "post link or reddit.com domain"
    }
  ]
}

Extract 10+ significant words for word_cloud_themes_on_platform. Return only valid JSON.
    """,
    tools=[search_web],
    # output_schema=SinglePlatformAnalysisReport,
    output_key="reddit_results"
)

# reddit_loop_agent = LoopAgent(
#     name="reddit_loop_agent",
#     description="Loop agent for Reddit search",
#     sub_agents=[reddit_agent],
#     max_iterations=2
# )

news_agent = LlmAgent(
    model=model_o4,
    name='news_agent',
    description="Searches news sites for brand mentions and provides analysis",
    instruction="""
Search for exactly 3 news articles about the brand, then analyze and return structured data.

First, search major news sites and industry publications from reputable news sites only.

Then analyze the articles and return this JSON structure:
{
  "brand_name": "the brand name",
  "platform_name": "News",
  "total_mentions_on_platform": 3,
  "platform_sentiment_breakdown": {
    "positive": 0.6,
    "negative": 0.3,
    "neutral": 0.1
  },
  "ethical_highlights_on_platform": [
    "key ethical theme 1",
    "key ethical theme 2"
  ],
  "word_cloud_themes_on_platform": [
    {"word": "theme_word", "weight": 8}
  ],
  "mentions_on_platform": [
    {
      "date": "actual date or Recent",
      "text": "actual article excerpt",
      "sentiment": "positive/negative/neutral",
      "ethical_context": "relevant theme",
      "url": "article link or news site domain"
    }
  ]
}

Extract 10+ significant words for word_cloud_themes_on_platform. Return only valid JSON.
    """,
    tools=[search_web],
    # output_schema=SinglePlatformAnalysisReport,
    output_key="news_results"
)

# news_loop_agent = LoopAgent(
#     name="news_loop_agent",
#     description="Loop agent for news search",
#     sub_agents=[news_agent],
#     max_iterations=2
# )
# Create platform search sequential agent


root_agent = ParallelAgent(
    name="mcp_brand_agent",
    description="Searches and analyzes brand mentions across multiple platforms in parallel.",
    sub_agents=[
        twitter_agent,
        linkedin_agent,
        reddit_agent,
        news_agent
    ]
)