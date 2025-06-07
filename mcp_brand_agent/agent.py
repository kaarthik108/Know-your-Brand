import os
from google.adk.agents import LlmAgent, ParallelAgent, LoopAgent, SequentialAgent
from pydantic import BaseModel
from typing import List, Dict, Literal
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import ToolContext
from google.genai import types
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

# from google.adk.planners.built_in_planner import BuiltInPlanner
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
# model_extract = model_analysis = LiteLlm(
#     model="o4-mini",
#     api_key=os.getenv("OPENAI_API_KEY")
# )
model_extract = model_analysis = "gemini-2.5-flash-preview-05-20"
# model_qwen = LiteLlm(
#     model="together_ai/Qwen/Qwen2.5-72B-Instruct-Turbo",
#     api_key=os.getenv("TOGETHERAI_API_KEY"),
#     # max_tokens=93762
# )

def exit_loop(tool_context: ToolContext):
  """Call this function ONLY when the critique indicates no further changes are needed, signaling the iterative process should end."""
  print(f"  [Tool Call] exit_loop triggered by {tool_context.agent_name}")
  tool_context.actions.escalate = True
  # Return empty dict as tools should typically return JSON-serializable output
  return {}
TARGET_FOLDER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_brand_agent")


# Create platform-specific search agents
twitter_agent = LlmAgent(
    model=model_analysis,
    name='twitter_agent',
    description="Searches Twitter/X for brand mentions and provides analysis",
    instruction="""
Search for exactly 3 Twitter/X posts about the brand, then analyze and return structured data.

First, search using brand name, hashtags, and keywords from x.com domain only. Extract 10+ significant words for word_cloud_themes_on_platform.

CRITICAL: Return ONLY valid JSON in this EXACT structure (no markdown, no explanations):
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
      "sentiment": "positive",
      "ethical_context": "relevant theme",
      "url": "post link or x.com domain"
    }
  ]
}

IMPORTANT: 
- sentiment must be exactly "positive", "negative", or "neutral"
- platform_name must be exactly "Twitter"
- Return ONLY the JSON object, no other text
    """,
    tools=[MCPToolset(
            connection_params=StdioServerParameters(
                command='npx',
                args=["-y", "@brightdata/mcp", os.path.abspath(TARGET_FOLDER_PATH)],
                env={
                    "API_TOKEN": os.getenv("MCP_TOKEN"),
                    # "WEB_UNLOCKER_ZONE": "web_unlocker1",
                    # "BROWSER_AUTH": "SBR_USER:SBR_PASS"
                }
            )
        )],
    # output_schema=SinglePlatformAnalysisReport,
    output_key="twitter_results",
    # generate_content_config=types.GenerateContentConfig(temperature=0.01),

)

twitter_extract_agent = LlmAgent(
    model=model_extract,
    name='twitter_extract_agent',
    description="Extracts the results from the twitter_agent in the structured JSON format",
    instruction="""
    You will receive data from the twitter_agent. Your task is to extract and return ONLY valid JSON that matches the required schema.

    Input data: {twitter_results}

    IMPORTANT INSTRUCTIONS:
    1. If the input contains JSON wrapped in markdown (```json ... ```), extract only the JSON content
    2. If the input is already valid JSON, return it as-is
    3. Ensure all required fields are present: brand_name, platform_name, total_mentions_on_platform, platform_sentiment_breakdown, ethical_highlights_on_platform, word_cloud_themes_on_platform, mentions_on_platform
    4. Return ONLY the JSON object, no markdown formatting, no explanations
    5. Ensure platform_name is exactly "Twitter"
    
    Return the clean JSON:
    """,
    output_key="final_twitter_results",
    output_schema=SinglePlatformAnalysisReport,
    # disallow_transfer_to_parent=True,
    # disallow_transfer_to_peers=True
        # generate_content_config=types.GenerateContentConfig(temperature=0.01)
)
# twitter_agent.planner = twitter_extract_agent.planner = BuiltInPlanner(
#     thinking_config=types.ThinkingConfig(
#         thinking_budget=0,
#     )
# )

twitter_sequential_agent = SequentialAgent(
    name="twitter_sequential_agent",
    description="Runs the twitter_agent and twitter_extract_agent sequentially",
    sub_agents=[twitter_agent, twitter_extract_agent]
)

# twitter_loop_agent = LoopAgent(
#     name="twitter_loop_agent",
#     description="Loop agent for Twitter search",
#     sub_agents=[twitter_agent],
#     max_iterations=2
# )

linkedin_agent = LlmAgent(
    model=model_analysis,
    name='linkedin_agent',
    description="Searches LinkedIn for brand mentions and provides analysis",
    instruction="""
Search for exactly 3 LinkedIn posts about the brand, then analyze and return structured data.

First, search company pages, executives, and industry posts from linkedin.com domain only. Extract 10+ significant words for word_cloud_themes_on_platform.

CRITICAL: Return ONLY valid JSON in this EXACT structure (no markdown, no explanations):
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
      "sentiment": "positive",
      "ethical_context": "relevant theme",
      "url": "post link or linkedin.com domain"
    }
  ]
}

IMPORTANT: 
- sentiment must be exactly "positive", "negative", or "neutral"
- platform_name must be exactly "LinkedIn"
- Return ONLY the JSON object, no other text
    """,
    tools=[MCPToolset(
            connection_params=StdioServerParameters(
                command='npx',
                args=["-y", "@brightdata/mcp", os.path.abspath(TARGET_FOLDER_PATH)],
                env={
                    "API_TOKEN": os.getenv("MCP_TOKEN"),
                    # "WEB_UNLOCKER_ZONE": "web_unlocker1",
                    # "BROWSER_AUTH": "SBR_USER:SBR_PASS"
                }
            )
        )],
    # output_schema=SinglePlatformAnalysisReport,
    output_key="linkedin_results",
    # generate_content_config=types.GenerateContentConfig(temperature=0.01),
)

linkedin_extract_agent = LlmAgent(
    model=model_extract,
    name='linkedin_extract_agent',
    description="Extracts the results from the linkedin_agent in the structured JSON format",
    instruction="""
    You will receive data from the linkedin_agent. Your task is to extract and return ONLY valid JSON that matches the required schema.

    Input data: {linkedin_results}

    IMPORTANT INSTRUCTIONS:
    1. If the input contains JSON wrapped in markdown (```json ... ```), extract only the JSON content
    2. If the input is already valid JSON, return it as-is
    3. Ensure all required fields are present: brand_name, platform_name, total_mentions_on_platform, platform_sentiment_breakdown, ethical_highlights_on_platform, word_cloud_themes_on_platform, mentions_on_platform
    4. Return ONLY the JSON object, no markdown formatting, no explanations
    5. Ensure platform_name is exactly "LinkedIn"
    
    Return the clean JSON:
    """,
    output_key="final_linkedin_results",
    output_schema=SinglePlatformAnalysisReport,
    # disallow_transfer_to_parent=True,
    # disallow_transfer_to_peers=True
    # generate_content_config=types.GenerateContentConfig(temperature=0.01)
)
# linkedin_agent.planner = linkedin_extract_agent.planner = BuiltInPlanner(
#     thinking_config=types.ThinkingConfig(
#         thinking_budget=0,
#     )
# )

linkedin_sequential_agent = SequentialAgent(
    name="linkedin_sequential_agent",
    description="Runs the linkedin_agent and linkedin_extract_agent sequentially",
    sub_agents=[linkedin_agent, linkedin_extract_agent]
)

# linkedin_loop_agent = LoopAgent(
#     name="linkedin_loop_agent",
#     description="Loop agent for LinkedIn search",
#     sub_agents=[linkedin_agent],
#     max_iterations=2
# )

reddit_agent = LlmAgent(
    model=model_analysis,
    name='reddit_agent',
    description="Searches Reddit for brand mentions and provides analysis",
    instruction="""
Search for exactly 3 Reddit posts about the brand, then analyze and return structured data.

First, search relevant subreddits and brand discussions from reddit.com domain only. Extract 10+ significant words for word_cloud_themes_on_platform.

CRITICAL: Return ONLY valid JSON in this EXACT structure (no markdown, no explanations):
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
      "sentiment": "positive",
      "ethical_context": "relevant theme",
      "url": "post link or reddit.com domain"
    }
  ]
}

IMPORTANT: 
- sentiment must be exactly "positive", "negative", or "neutral"
- platform_name must be exactly "Reddit"
- Return ONLY the JSON object, no other text
    """,
    tools=[MCPToolset(
            connection_params=StdioServerParameters(
                command='npx',
                args=["-y", "@brightdata/mcp", os.path.abspath(TARGET_FOLDER_PATH)],
                env={
                    "API_TOKEN": os.getenv("MCP_TOKEN"),
                    # "WEB_UNLOCKER_ZONE": "web_unlocker1",
                    # "BROWSER_AUTH": "SBR_USER:SBR_PASS"
                }
            )
        )],
    # output_schema=SinglePlatformAnalysisReport,
    output_key="reddit_results",
    # generate_content_config=types.GenerateContentConfig(temperature=0.01),
)

reddit_extract_agent = LlmAgent(
    name='reddit_extract_agent',
    model=model_extract,
    description="Extracts the results from the reddit_agent in the structured JSON format",
    instruction="""
    You will receive data from the reddit_agent. Your task is to extract and return ONLY valid JSON that matches the required schema.

    Input data: {reddit_results}

    IMPORTANT INSTRUCTIONS:
    1. If the input contains JSON wrapped in markdown (```json ... ```), extract only the JSON content
    2. If the input is already valid JSON, return it as-is
    3. Ensure all required fields are present: brand_name, platform_name, total_mentions_on_platform, platform_sentiment_breakdown, ethical_highlights_on_platform, word_cloud_themes_on_platform, mentions_on_platform
    4. Return ONLY the JSON object, no markdown formatting, no explanations
    5. Ensure platform_name is exactly "Reddit"
    
    Return the clean JSON:
    """,
    output_key="final_reddit_results",
    output_schema=SinglePlatformAnalysisReport,
    # disallow_transfer_to_parent=True,
    # disallow_transfer_to_peers=True
    # generate_content_config=types.GenerateContentConfig(temperature=0.01)
)
# reddit_agent.planner = reddit_extract_agent.planner = BuiltInPlanner(
#     thinking_config=types.ThinkingConfig(
#         thinking_budget=0,
#     )
# )

reddit_sequential_agent = SequentialAgent(
    name="reddit_sequential_agent",
    description="Runs the reddit_agent and reddit_extract_agent sequentially",
    sub_agents=[reddit_agent, reddit_extract_agent]
)


# reddit_loop_agent = LoopAgent(
#     name="reddit_loop_agent",
#     description="Loop agent for Reddit search",
#     sub_agents=[reddit_agent],
#     max_iterations=2
# )

news_agent = LlmAgent(
    model=model_analysis,
    name='news_agent',
    description="Searches news sites for brand mentions and provides analysis",
    instruction="""
Search for exactly 3 news articles about the brand, then analyze and return structured data.

First, search major news sites and industry publications from reputable news sites only. Extract 10+ significant words for word_cloud_themes_on_platform.

CRITICAL: Return ONLY valid JSON in this EXACT structure (no markdown, no explanations):
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
      "sentiment": "positive",
      "ethical_context": "relevant theme",
      "url": "article link or news site domain"
    }
  ]
}

IMPORTANT: 
- sentiment must be exactly "positive", "negative", or "neutral"
- platform_name must be exactly "News"
- Return ONLY the JSON object, no other text
    """,
    tools=[MCPToolset(
            connection_params=StdioServerParameters(
                command='npx',
                args=["-y", "@brightdata/mcp", os.path.abspath(TARGET_FOLDER_PATH)],
                env={
                    "API_TOKEN": os.getenv("MCP_TOKEN"),
                    # "WEB_UNLOCKER_ZONE": "web_unlocker1",
                    # "BROWSER_AUTH": "SBR_USER:SBR_PASS"
                }
            )
        )],
    # output_schema=SinglePlatformAnalysisReport,
    output_key="news_results",
    # generate_content_config=types.GenerateContentConfig(temperature=0.01),
)

news_extract_agent = LlmAgent(
    name='news_extract_agent',
    model=model_extract,
    description="Extracts the results from the news_agent in the structured JSON format",
    instruction="""
    You will receive data from the news_agent. Your task is to extract and return ONLY valid JSON that matches the required schema.

    Input data: {news_results}

    IMPORTANT INSTRUCTIONS:
    1. If the input contains JSON wrapped in markdown (```json ... ```), extract only the JSON content
    2. If the input is already valid JSON, return it as-is
    3. Ensure all required fields are present: brand_name, platform_name, total_mentions_on_platform, platform_sentiment_breakdown, ethical_highlights_on_platform, word_cloud_themes_on_platform, mentions_on_platform
    4. Return ONLY the JSON object, no markdown formatting, no explanations
    5. Ensure platform_name is exactly "News"
    
    Return the clean JSON:
    """,
    output_key="final_news_results",
    output_schema=SinglePlatformAnalysisReport,
    # disallow_transfer_to_parent=True,
    # disallow_transfer_to_peers=True
    # generate_content_config=types.GenerateContentConfig(temperature=0.01)
)
# news_agent.planner = news_extract_agent.planner = BuiltInPlanner(
#     thinking_config=types.ThinkingConfig(
#         thinking_budget=0,
#     )
# )
news_sequential_agent = SequentialAgent(
    name="news_sequential_agent",
    description="Runs the news_agent and news_extract_agent sequentially",
    sub_agents=[news_agent, news_extract_agent]
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
        twitter_sequential_agent,
        linkedin_sequential_agent,
        reddit_sequential_agent,
        news_sequential_agent
    ]
)