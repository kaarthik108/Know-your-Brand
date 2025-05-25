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
    name='twitter_search_agent',
    description="Searches Twitter/X for recent brand mentions",
    instruction="""
Find exactly 3 Twitter/X posts about the brand. Search using brand name, hashtags, and keywords.

Return JSON array with 3 posts, each containing:
- platform: "Twitter"
- date: actual date or "Recent"
- text: actual post content
- sentiment: "positive", "negative", or "neutral"
- ethical_context: relevant business/ethical theme
- url: post link or x.com domain

Search multiple approaches if needed. No empty results - find real posts from x.com domain only.
    """,
    tools=[search_web],
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
    name='linkedin_search_agent',
    description="Searches LinkedIn for recent brand mentions",
    instruction="""
Find exactly 3 LinkedIn posts about the brand. Search company pages, executives, and industry posts.

Return JSON array with 3 posts, each containing:
- platform: "LinkedIn"
- date: actual date or "Recent"
- text: actual post content
- sentiment: "positive", "negative", or "neutral"
- ethical_context: relevant business/ethical theme
- url: post link or linkedin.com domain

Search multiple approaches if needed. No empty results - find real posts from linkedin.com domain only.
    """,
    tools=[search_web],
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
    name='reddit_search_agent',
    description="Searches Reddit for recent brand mentions",
    instruction="""
Find exactly 3 Reddit posts about the brand. Search relevant subreddits and brand discussions.

Return JSON array with 3 posts, each containing:
- platform: "Reddit"
- date: actual date or "Recent"
- text: actual post content
- sentiment: "positive", "negative", or "neutral"
- ethical_context: relevant business/ethical theme
- url: post link or reddit.com domain

Search multiple subreddits if needed. No empty results - find real posts from reddit.com domain only.
    """,
    tools=[search_web],
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
    name='news_search_agent',
    description="Searches news sites for recent brand mentions",
    instruction="""
Find exactly 3 news articles about the brand. Search major news sites and industry publications.

Return JSON array with 3 articles, each containing:
- platform: "News"
- date: actual date or "Recent"
- text: actual article excerpt
- sentiment: "positive", "negative", or "neutral"
- ethical_context: relevant business/ethical theme
- url: article link or news site domain

Search multiple news sources if needed. No empty results - find real articles from reputable news sites only.
    """,
    tools=[search_web],
    output_key="news_results"
)

# news_loop_agent = LoopAgent(
#     name="news_loop_agent",
#     description="Loop agent for news search",
#     sub_agents=[news_agent],
#     max_iterations=2
# )
# Create platform search sequential agent
platform_search_agent = ParallelAgent(
    name="platform_search",
    description="""Runs multiple search agents in parallel to find brand mentions on multiple platforms.""",
    sub_agents=[twitter_agent, linkedin_agent, reddit_agent, news_agent],
)

# Create platform-specific analysis agents
twitter_analysis_agent = LlmAgent(
    model=model_o4,
    name='twitter_analysis_agent',
    description="Analyzes Twitter brand mentions to provide platform-specific insights",
    instruction="""
You are a brand reputation analyst specializing in Twitter data. Your task is to:
1. Review all the Twitter mentions provided for the brand. The Twitter mentions are available as a JSON array in the {twitter_results} variable.
2. Analyze the sentiment for these Twitter mentions.
3. Identify key ethical themes or issues mentioned specifically on Twitter.
4. Extract important theme words (nouns, verbs, adjectives) from Twitter mentions for a word cloud.
5. Provide a structured summary for Twitter.

Analyze these mentions and provide your insights following this structure for Twitter:
{
  "brand_name": "the brand name",
  "platform_name": "Twitter",
  "total_mentions_on_platform": "number of Twitter mentions found, as an integer",
  "platform_sentiment_breakdown": {
    "positive": "percentage (as number, e.g., 0.6 for 60%)",
    "negative": "percentage (as number, e.g., 0.3 for 30%)",
    "neutral": "percentage (as number, e.g., 0.1 for 10%)"
  },
  "ethical_highlights_on_platform": [
    "key ethical theme 1 from Twitter",
    "key ethical theme 2 from Twitter"
  ],
  "word_cloud_themes_on_platform": [
    {
      "word": "theme_word_1_twitter",
      "weight": "frequency/importance score (integer 1-10)"
    },
    {
      "word": "theme_word_2_twitter",
      "weight": "frequency/importance score (integer 1-10)"
    }
  ],
  "mentions_on_platform": [
    {
      "date": "date of mention",
      "text": "content of mention",
      "sentiment": "sentiment of mention",
      "ethical_context": "ethical context",
      "url": "url to the mention"
    }
  ]
}

For the word_cloud_themes_on_platform, extract at least 10 significant nouns, verbs, and adjectives from the Twitter mentions.
The "mentions_on_platform" field should be the direct list of mentions received in twitter_results.
IMPORTANT: YOUR RESPONSE MUST BE ONLY THE JSON OBJECT. DO NOT INCLUDE ANY OTHER TEXT, MARKDOWN, OR EXPLANATIONS.
ALL THE FIELDS MUST BE IN DOUBLE QUOTES (KEYS AND VALUES). Ensure all numerical values are actual numbers, not strings.
Make sure your response is valid JSON that can be parsed.
    """,
    output_schema=SinglePlatformAnalysisReport,
    output_key="analysis_results_twitter"
)

linkedin_analysis_agent = LlmAgent(
    model=model_o4,
    name='linkedin_analysis_agent',
    description="Analyzes LinkedIn brand mentions to provide platform-specific insights",
    instruction="""
You are a brand reputation analyst specializing in LinkedIn data. Your task is to:
1. Review all the LinkedIn mentions provided for the brand. The LinkedIn mentions are available as a JSON array in the {linkedin_results} variable.
2. Analyze the sentiment for these LinkedIn mentions.
3. Identify key ethical themes or issues mentioned specifically on LinkedIn.
4. Extract important theme words (nouns, verbs, adjectives) from LinkedIn mentions for a word cloud.
5. Provide a structured summary for LinkedIn.

Analyze these mentions and provide your insights following this structure for LinkedIn:
{
  "brand_name": "the brand name",
  "platform_name": "LinkedIn",
  "total_mentions_on_platform": "number of LinkedIn mentions found, as an integer",
  "platform_sentiment_breakdown": {
    "positive": "percentage (as number, e.g., 0.6 for 60%)",
    "negative": "percentage (as number, e.g., 0.3 for 30%)",
    "neutral": "percentage (as number, e.g., 0.1 for 10%)"
  },
  "ethical_highlights_on_platform": [
    "key ethical theme 1 from LinkedIn",
    "key ethical theme 2 from LinkedIn"
  ],
  "word_cloud_themes_on_platform": [
    {
      "word": "theme_word_1_linkedin",
      "weight": "frequency/importance score (integer 1-10)"
    },
    {
      "word": "theme_word_2_linkedin",
      "weight": "frequency/importance score (integer 1-10)"
    }
  ],
  "mentions_on_platform": [
    {
      "date": "date of mention",
      "text": "content of mention",
      "sentiment": "sentiment of mention",
      "ethical_context": "ethical context",
      "url": "url to the mention"
    }
  ]
}

For the word_cloud_themes_on_platform, extract at least 10 significant nouns, verbs, and adjectives from the LinkedIn mentions.
The "mentions_on_platform" field should be the direct list of mentions received in linkedin_results.
IMPORTANT: YOUR RESPONSE MUST BE ONLY THE JSON OBJECT. DO NOT INCLUDE ANY OTHER TEXT, MARKDOWN, OR EXPLANATIONS.
ALL THE FIELDS MUST BE IN DOUBLE QUOTES (KEYS AND VALUES). Ensure all numerical values are actual numbers, not strings.
Make sure your response is valid JSON that can be parsed.
    """,
    output_schema=SinglePlatformAnalysisReport,
    output_key="analysis_results_linkedin"
)

reddit_analysis_agent = LlmAgent(
    model=model_gemini,
    name='reddit_analysis_agent',
    description="Analyzes Reddit brand mentions to provide platform-specific insights",
    instruction="""
You are a brand reputation analyst specializing in Reddit data. Your task is to:
1. Review all the Reddit mentions provided for the brand. The Reddit mentions are available as a JSON array in the {reddit_results} variable.
2. Analyze the sentiment for these Reddit mentions.
3. Identify key ethical themes or issues mentioned specifically on Reddit.
4. Extract important theme words (nouns, verbs, adjectives) from Reddit mentions for a word cloud.
5. Provide a structured summary for Reddit.

Analyze these mentions and provide your insights following this structure for Reddit:
{
  "brand_name": "the brand name",
  "platform_name": "Reddit",
  "total_mentions_on_platform": "number of Reddit mentions found, as an integer",
  "platform_sentiment_breakdown": {
    "positive": "percentage (as number, e.g., 0.6 for 60%)",
    "negative": "percentage (as number, e.g., 0.3 for 30%)",
    "neutral": "percentage (as number, e.g., 0.1 for 10%)"
  },
  "ethical_highlights_on_platform": [
    "key ethical theme 1 from Reddit",
    "key ethical theme 2 from Reddit"
  ],
  "word_cloud_themes_on_platform": [
    {
      "word": "theme_word_1_reddit",
      "weight": "frequency/importance score (integer 1-10)"
    },
    {
      "word": "theme_word_2_reddit",
      "weight": "frequency/importance score (integer 1-10)"
    }
  ],
  "mentions_on_platform": [
    {
      "date": "date of mention",
      "text": "content of mention",
      "sentiment": "sentiment of mention",
      "ethical_context": "ethical context",
      "url": "url to the mention"
    }
  ]
}

For the word_cloud_themes_on_platform, extract at least 10 significant nouns, verbs, and adjectives from the Reddit mentions.
The "mentions_on_platform" field should be the direct list of mentions received in reddit_results.
IMPORTANT: YOUR RESPONSE MUST BE ONLY THE JSON OBJECT. DO NOT INCLUDE ANY OTHER TEXT, MARKDOWN, OR EXPLANATIONS.
ALL THE FIELDS MUST BE IN DOUBLE QUOTES (KEYS AND VALUES). Ensure all numerical values are actual numbers, not strings.
Make sure your response is valid JSON that can be parsed.
    """,
    output_schema=SinglePlatformAnalysisReport,
    output_key="analysis_results_reddit"
)

news_analysis_agent = LlmAgent(
    model=model_o4,
    name='news_analysis_agent',
    description="Analyzes News brand mentions to provide platform-specific insights",
    instruction="""
You are a brand reputation analyst specializing in News data. Your task is to:
1. Review all the News mentions provided for the brand. The News mentions are available as a JSON array in the {news_results} variable.
2. Analyze the sentiment for these News mentions.
3. Identify key ethical themes or issues mentioned specifically in News articles.
4. Extract important theme words (nouns, verbs, adjectives) from News mentions for a word cloud.
5. Provide a structured summary for News.

Analyze these mentions and provide your insights following this structure for News:
{
  "brand_name": "the brand name",
  "platform_name": "News",
  "total_mentions_on_platform": "number of News mentions found, as an integer",
  "platform_sentiment_breakdown": {
    "positive": "percentage (as number, e.g., 0.6 for 60%)",
    "negative": "percentage (as number, e.g., 0.3 for 30%)",
    "neutral": "percentage (as number, e.g., 0.1 for 10%)"
  },
  "ethical_highlights_on_platform": [
    "key ethical theme 1 from News",
    "key ethical theme 2 from News"
  ],
  "word_cloud_themes_on_platform": [
    {
      "word": "theme_word_1_news",
      "weight": "frequency/importance score (integer 1-10)"
    },
    {
      "word": "theme_word_2_news",
      "weight": "frequency/importance score (integer 1-10)"
    }
  ],
  "mentions_on_platform": [
    {
      "date": "date of mention",
      "text": "content of mention",
      "sentiment": "sentiment of mention",
      "ethical_context": "ethical context",
      "url": "url to the mention"
    }
  ]
}

For the word_cloud_themes_on_platform, extract at least 10 significant nouns, verbs, and adjectives from the News mentions.
The "mentions_on_platform" field should be the direct list of mentions received in news_results.
IMPORTANT: YOUR RESPONSE MUST BE ONLY THE JSON OBJECT. DO NOT INCLUDE ANY OTHER TEXT, MARKDOWN, OR EXPLANATIONS.
ALL THE FIELDS MUST BE IN DOUBLE QUOTES (KEYS AND VALUES). Ensure all numerical values are actual numbers, not strings.
Make sure your response is valid JSON that can be parsed.
    """,
    output_schema=SinglePlatformAnalysisReport,
    output_key="analysis_results_news"
)

parallel_analysis_coordinator_agent = ParallelAgent(
    name="parallel_analysis_coordinator",
    description="Coordinates parallel analysis of brand mentions for each platform.",
    sub_agents=[
        twitter_analysis_agent,
        linkedin_analysis_agent,
        reddit_analysis_agent,
        news_analysis_agent
    ]
)

# Create main sequential agent
main_agent = SequentialAgent(
    name="mcp_brand_agent",
    description="You are a brand monitoring agent. Your task is to monitor the brand mentions across multiple platforms and provide a comprehensive summary of the mentions",
    sub_agents=[platform_search_agent, parallel_analysis_coordinator_agent]
)

root_agent = main_agent