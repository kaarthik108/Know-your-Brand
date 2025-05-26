# import os
# import json
# from google.adk.agents import LlmAgent, ParallelAgent, Agent, LoopAgent
# from pydantic import BaseModel, HttpUrl
# from typing import List, Dict, Literal, Optional
# from google.adk.models.lite_llm import LiteLlm
# from google.adk.tools import ToolContext
# from .tool_helper import search_web
# from google.adk.agents.callback_context import CallbackContext
# from google.adk.models import LlmRequest, LlmResponse
# class SentimentBreakdown(BaseModel):
#     positive: float
#     negative: float
#     neutral: float

# class PlatformSentiment(SentimentBreakdown):
#     count: int

# class WordCloudTheme(BaseModel):
#     word: str
#     weight: float

# class Mention(BaseModel):
#     date: str
#     text: str
#     sentiment: Literal["positive", "negative", "neutral"]
#     ethical_context: str
#     url: HttpUrl

# class PlatformMentions(BaseModel):
#     name: Literal["Twitter", "LinkedIn", "Reddit", "News"]
#     mentions: List[Mention]

# class BrandSentimentReport(BaseModel):
#     brand_name: str
#     total_mentions: int
#     overall_sentiment: SentimentBreakdown
#     platform_sentiment: Dict[Literal["Twitter", "LinkedIn", "Reddit", "News"], PlatformSentiment]
#     ethical_highlights: List[str]
#     word_cloud_themes: List[WordCloudTheme]
#     platforms: List[PlatformMentions]

# # model_mini = LiteLlm(
# #     model="gpt-4.1-mini",
# #     api_key=os.getenv("OPENAI_API_KEY"),
# # )
# # model = LiteLlm(
# #     model="gpt-4.1",
# #     api_key=os.getenv("OPENAI_API_KEY"),
# #     temperature=0.01
# # )
# # # model = 'gemini-2.5-flash-preview-04-17'

# model = LiteLlm(
#     model="perplexity/sonar-pro",
#     api_key=os.getenv("PERPLEXITYAI_API_KEY"),
# )
# model_mini = model

# def exit_loop(tool_context: ToolContext):
#   """Call this function ONLY when the critique indicates no further changes are needed, signaling the iterative process should end."""
#   print(f"  [Tool Call] exit_loop triggered by {tool_context.agent_name}")
#   tool_context.actions.escalate = True
#   # Return empty dict as tools should typically return JSON-serializable output
#   return {}



# # Create platform-specific search agents
# twitter_agent = LlmAgent(
#     model=model_mini,
#     name='twitter_search_agent',
#     description="Searches Twitter/X for recent brand mentions",
#     instruction="""
# You are a Twitter/X search specialist tasked with finding recent mentions of a brand. Your goal is to ALWAYS find at least 3 relevant Twitter/X posts - NEVER return empty results.

# SEARCH STRATEGY:
# 1. Use multiple search approaches:
# - Search for the brand name directly: brand_name
# - Search with hashtags: #brand_name 
# - Search for brand + keywords: brand_name news OR brand_name update
# - Search for company + topics: brand_name product OR brand_name announcement
# - If needed, check @brand_name official account for recent posts

# 2. For ethical mentions, try these specific searches:
# - brand_name sustainability OR brand_name environment
# - brand_name social OR brand_name community
# - brand_name diversity OR brand_name inclusion
# - brand_name ethics OR brand_name responsibility

# 3. If ethical content is limited, include ANY significant mentions:
# - Product launches/updates
# - Customer experiences (positive or negative)
# - Company news/announcements
# - Industry developments involving the brand
# - Any trending discussions about the brand

# MANDATORY OUTPUT RULES:
# 1. You MUST find and return at least 3 actual Twitter/X posts about the brand
# 2. FORMAT your response as a JSON array containing AT LEAST 3 posts
# 3. For each post, include:
# - platform: "Twitter" (always fixed value)
# - date: "2024-05-15" (or "Recent" if exact date unknown - NEVER use null)
# - text: (the actual post text - NEVER return placeholder text)
# - sentiment: (positive, negative, or neutral - based on content)
# - ethical_context: (ethical themes or general business context - NEVER empty)
# - url: (link to post if available, or a search URL if not - NEVER use null)

# IMPORTANT: 
# - When using tools, ensure JSON is correctly formatted
# - Empty results are NOT acceptable - continue searching until you find actual posts
# - NEVER return placeholder text like "No results found" - find real content
# - If you can't find posts from the exact last week, include posts from the last month
# - Every post must have a date, text, sentiment and ethical_context - no nulls or empty fields

# Example of expected output format:
# [
# {
# "platform": "Twitter",
# "date": "2024-05-14",
# "text": "Actual tweet text here about the brand",
# "sentiment": "positive",
# "ethical_context": "Product sustainability and recycling initiatives",
# "url": "https://twitter.com/username/status/1234567890"
# },
# {
# "platform": "Twitter",
# "date": "Recent",
# "text": "Another actual tweet about the brand",
# "sentiment": "neutral", 
# "ethical_context": "Market competition and business strategy",
# "url": "https://twitter.com/search"
# }
# ]
#     """,
#     tools=[search_web, exit_loop],
#     output_key="twitter_results"
# )

# twitter_loop_agent = LoopAgent(
#     name="twitter_loop_agent",
#     description="Loop agent for Twitter search",
#     sub_agents=[twitter_agent],
#     max_iterations=2
# )

# linkedin_agent = LlmAgent(
#     model=model_mini,
#     name='linkedin_search_agent',
#     description="Searches LinkedIn for recent brand mentions",
#     instruction="""
# You are a LinkedIn search specialist tasked with finding recent mentions of a brand. Your goal is to ALWAYS find at least 3 relevant LinkedIn posts - NEVER return empty results.

# SEARCH STRATEGY:
# 1. Use multiple search approaches:
# - Search for the brand name directly: brand_name
# - Search with company + industry: brand_name category
# - Search with related terms: brand_name announcement OR brand_name update
# - Search for specific topics: brand_name sustainability OR brand_name initiative

# 2. Check these LinkedIn sources:
# - The company's official LinkedIn page posts
# - Posts from company executives or employees
# - Industry influencers discussing the brand
# - News items shared on LinkedIn about the brand
# - LinkedIn articles mentioning the brand

# 3. If ethical content is limited, include ANY significant mentions:
# - New products/services
# - Company performance or changes
# - Leadership updates or interviews
# - Industry trends involving the brand
# - Customer testimonials or reviews
# - Job postings or company culture posts

# MANDATORY OUTPUT RULES:
# 1. You MUST find and return at least 3 actual LinkedIn posts about the brand
# 2. FORMAT your response as a JSON array containing AT LEAST 3 posts
# 3. For each post, include:
# - platform: "LinkedIn" (always fixed value)
# - date: "2024-05-15" (or "Recent" if exact date unknown - NEVER use null)
# - text: (the actual post text - NEVER return placeholder text)
# - sentiment: (positive, negative, or neutral - based on content)
# - ethical_context: (ethical themes or general business context - NEVER empty)
# - url: (link to post if available, or a company URL if not - NEVER use null)

# IMPORTANT: 
# - When using tools, ensure JSON is correctly formatted
# - Empty results are NOT acceptable - continue searching until you find actual posts
# - NEVER return placeholder text like "No results found" - find real content
# - If you can't find posts from the exact last week, include posts from the last month
# - Every post must have a date, text, sentiment and ethical_context - no nulls or empty fields

# Example of expected output format:
# [
# {
# "platform": "LinkedIn",
# "date": "2024-05-14",
# "text": "Actual LinkedIn post text here about the brand",
# "sentiment": "positive",
# "ethical_context": "Corporate responsibility and sustainability initiatives",
# "url": "https://www.linkedin.com/posts/company-page_post-activity-1234567890"
# },
# {
# "platform": "LinkedIn",
# "date": "Recent",
# "text": "Another actual LinkedIn post about the brand",
# "sentiment": "neutral", 
# "ethical_context": "Product innovation and market strategy",
# "url": "https://linkedin.com/company"
# }
# ]
#     """,
#     tools=[search_web, exit_loop],
#     output_key="linkedin_results"
# )

# linkedin_loop_agent = LoopAgent(
#     name="linkedin_loop_agent",
#     description="Loop agent for LinkedIn search",
#     sub_agents=[linkedin_agent],
#     max_iterations=2
# )

# reddit_agent = LlmAgent(
#     model=model_mini,
#     name='reddit_search_agent',
#     description="Searches Reddit for recent brand mentions",
#     instruction="""
# You are a Reddit search specialist tasked with finding recent mentions of a brand. Your goal is to ALWAYS find at least 3 relevant Reddit posts - NEVER return empty results.

# SEARCH STRATEGY:
# 1. Use multiple search approaches:
# - Search for the brand name directly: brand_name
# - Search in relevant subreddits: 
#     * r/brand_name
#     * r/technology
#     * r/business
#     * r/news
#     * r/EthicalConsumer
#     * r/sustainability
#     * Subreddits related to category
# - Search with keywords: brand_name news OR brand_name products

# 2. For ethical mentions, try these specific searches:
# - brand_name sustainability OR brand_name environment
# - brand_name ethics OR brand_name responsibility
# - brand_name controversy OR brand_name issues
# - brand_name workers OR brand_name labor

# 3. If ethical content is limited, include ANY significant mentions:
# - Product reviews or discussions
# - Company news or announcements
# - Customer service experiences
# - Investment or financial discussions
# - Industry comparisons with competitors

# MANDATORY OUTPUT RULES:
# 1. You MUST find and return at least 3 actual Reddit posts about the brand
# 2. FORMAT your response as a JSON array containing AT LEAST 3 posts
# 3. For each post, include:
# - platform: "Reddit" (always fixed value)
# - date: "2024-05-15" (or "Recent" if exact date unknown - NEVER use null)
# - text: (the actual post text - NEVER return placeholder text)
# - sentiment: (positive, negative, or neutral - based on content)
# - ethical_context: (ethical themes or general business context - NEVER empty)
# - url: (link to post if available, or a search URL if not - NEVER use null)

# IMPORTANT: 
# - When using tools, ensure JSON is correctly formatted
# - Empty results are NOT acceptable - continue searching until you find actual posts
# - NEVER return placeholder text like "No results found" - find real content
# - If you can't find posts from the exact last week, include posts from the last month
# - Every post must have a date, text, sentiment and ethical_context - no nulls or empty fields

# Example of expected output format:
# [
# {
# "platform": "Reddit",
# "date": "2024-05-14",
# "text": "Actual Reddit post text here about the brand",
# "sentiment": "negative",
# "ethical_context": "Customer service issues and product reliability concerns",
# "url": "https://www.reddit.com/r/technology/comments/abc123/post_title"
# },
# {
# "platform": "Reddit",
# "date": "Recent",
# "text": "Another actual Reddit post about the brand",
# "sentiment": "positive", 
# "ethical_context": "Product quality and innovation",
# "url": "https://reddit.com/search"
# }
# ]
#     """,
#     tools=[search_web, exit_loop],
#     output_key="reddit_results"
# )

# reddit_loop_agent = LoopAgent(
#     name="reddit_loop_agent",
#     description="Loop agent for Reddit search",
#     sub_agents=[reddit_agent],
#     max_iterations=2
# )

# news_agent = LlmAgent(
#     model=model_mini,
#     name='news_search_agent',
#     description="Searches news sites for recent brand mentions",
#     instruction="""
# You are a news search specialist tasked with finding recent mentions of a brand. Your goal is to ALWAYS find at least 3 relevant news articles - NEVER return empty results.

# SEARCH STRATEGY:
# 1. Use multiple search approaches:
# - Search for the brand name directly: brand_name news
# - Search with industry focus: brand_name category news
# - Search for recent events: brand_name recent OR brand_name latest
# - Search for financials: brand_name earnings OR brand_name stock

# 2. For ethical mentions, try these specific searches:
# - brand_name sustainability OR brand_name environment
# - brand_name social responsibility OR brand_name community
# - brand_name labor OR brand_name working conditions
# - brand_name controversy OR brand_name ethics

# 3. Check these news sources:
# - Major news sites (CNN, BBC, Reuters, Bloomberg, etc.)
# - Industry publications related to category
# - Business news (WSJ, Financial Times, CNBC, etc.)
# - Technology news sites (for tech companies)
# - Local news sources from location

# 4. If ethical content is limited, include ANY significant news articles:
# - Product launches or updates
# - Financial news or market performance
# - Executive changes or interviews
# - Industry trends or analysis
# - Regulatory news or legal issues

# MANDATORY OUTPUT RULES:
# 1. You MUST find and return at least 3 actual news articles about the brand
# 2. FORMAT your response as a JSON array containing AT LEAST 3 articles
# 3. For each article, include:
# - platform: "News" (always fixed value)
# - date: "2024-05-15" (or "Recent" if exact date unknown - NEVER use null)
# - text: (the actual article excerpt - NEVER return placeholder text)
# - sentiment: (positive, negative, or neutral - based on content)
# - ethical_context: (ethical themes or general business context - NEVER empty)
# - url: (link to article if available, or a major news site URL if not - NEVER use null)

# IMPORTANT: 
# - When using tools, ensure JSON is correctly formatted
# - Empty results are NOT acceptable - continue searching until you find actual articles
# - NEVER return placeholder text like "No results found" - find real content
# - If you can't find articles from the exact last week, include articles from the last month
# - Every article must have a date, text, sentiment and ethical_context - no nulls or empty fields

# Example of expected output format:
# [
# {
# "platform": "News",
# "date": "2024-05-14",
# "text": "Actual news article excerpt here about the brand...",
# "sentiment": "positive",
# "ethical_context": "Environmental initiatives and carbon reduction goals",
# "url": "https://www.bloomberg.com/news/articles/2024-05-14/brand-article-title"
# },
# {
# "platform": "News",
# "date": "Recent",
# "text": "Another actual news excerpt about the brand...",
# "sentiment": "neutral", 
# "ethical_context": "Market competition and business strategy",
# "url": "https://www.reuters.com/search"
# }
# ]
#     """,
#     tools=[search_web, exit_loop],
#     output_key="news_results"
# )

# news_loop_agent = LoopAgent(
#     name="news_loop_agent",
#     description="Loop agent for news search",
#     sub_agents=[news_agent],
#     max_iterations=2
# )
# # Create platform search sequential agent
# platform_search_agent = ParallelAgent(
#     name="platform_search",
#     description="""Searches multiple platforms for brand/company mentions and aggregates results. Your task is to:
# 1. Search for mentions of the specified brand/company on multiple platforms
# 2. Collect search results from multiple platforms
# 3. ENSURE that each platform returns at least 3 actual mentions with complete information

# Make sure you use the exit_loop function to end the loop when you have found the mentions for all the platforms.""",
#     sub_agents=[twitter_loop_agent, linkedin_loop_agent, reddit_loop_agent, news_loop_agent],
# )

# # Create analysis agent - this one can use output_schema since it doesn't use tools
# analysis_agent = LlmAgent(
#     model=model,
#     name='analysis_agent',
#     description="Analyzes brand mentions to provide comprehensive insights",
#     instruction="""
# You are a brand reputation analyst. Your task is to:
# 1. Review all the brand mentions collected from different platforms
# 2. Analyze the overall sentiment and per-platform sentiment breakdowns
# 3. Identify key ethical themes or issues mentioned
# 4. Extract important theme words (nouns, verbs, adjectives) for word cloud visualization
# 5. Aggregate mentions by platform
# 6. Provide a comprehensive summary with structured data

# The aggregated mentions from all platforms are available as a JSON array:
# Twitter/X: {twitter_results} \n\n
# LinkedIn: {linkedin_results} \n\n
# Reddit: {reddit_results} \n\n
# News: {news_results} \n\n

# Analyze these mentions and provide your insights following this structure:
# {
#   "brand_name": "the brand name",
#   "total_mentions": number of mentions found,
#   "overall_sentiment": {
#     "positive": percentage (as number),
#     "negative": percentage (as number),
#     "neutral": percentage (as number)
#   },
#   "platform_sentiment": {
#     "Twitter": {
#       "positive": percentage (as number),
#       "negative": percentage (as number),
#       "neutral": percentage (as number),
#       "count": total count for this platform
#     },
#     "LinkedIn": {
#       "positive": percentage (as number),
#       "negative": percentage (as number),
#       "neutral": percentage (as number),
#       "count": total count for this platform
#     },
#     "Reddit": {
#       "positive": percentage (as number),
#       "negative": percentage (as number),
#       "neutral": percentage (as number),
#       "count": total count for this platform
#     },
#     "News": {
#       "positive": percentage (as number),
#       "negative": percentage (as number),
#       "neutral": percentage (as number),
#       "count": total count for this platform
#     }
#   },
#   "ethical_highlights": [
#     "key ethical theme 1",
#     "key ethical theme 2",
#     etc.
#   ],
#   "word_cloud_themes": [
#     {
#       "word": "theme_word_1",
#       "weight": frequency/importance score (higher number = larger display)
#     },
#     {
#       "word": "theme_word_2",
#       "weight": frequency/importance score
#     },
#     etc.
#   ],
#   "platforms": [
#     {
#       "name": "Twitter",
#       "mentions": [
#         {
#           "date": "date of mention",
#           "text": "content of mention",
#           "sentiment": "sentiment of mention",
#           "ethical_context": "ethical context",
#           "url": "url to the mention"
#         },
#         etc.
#       ]
#     },
#     {
#       "name": "LinkedIn",
#       "mentions": [
#         etc.
#       ]
#     },
#     {
#       "name": "Reddit",
#       "mentions": [
#         etc.
#       ]
#     },
#     {
#       "name": "News",
#       "mentions": [
#         etc.
#       ]
#     }
#   ]
# }

# For the word_cloud_themes, extract at least 30 significant nouns, verbs, and adjectives from all the mentions that represent key themes, product features, corporate activities, ethical concerns, etc. For each word:
# 1. Calculate its weight based on frequency (how many times it appears across all mentions)
# 2. Assign higher weights to words that appear in mention titles or are emphasized
# 3. Use a scale of 1-10 where 10 represents the most frequent/important words
# 4. Include a diverse range of words related to different aspects (product, ethics, business, etc.)

# IMPORTANT: ALL THE FIELDS MUST BE IN DOUBLE QUOTES BOTH (KEYS AND VALUES)

# Make sure your response is valid JSON that can be parsed.
#     """,
#     output_schema=BrandSentimentReport,
#     output_key="analysis_results"
# )
# def before_model_callback(
#     callback_context: CallbackContext, llm_request: LlmRequest
# ) -> Optional[LlmResponse]:
#     """
#     Callback that executes before the model is called.
#     Detects and saves inline images from user messages to assets folder
#     for use by the generate_image_agent.

#     Args:
#         callback_context: The callback context
#         llm_request: The LLM request

#     Returns:
#         Optional[LlmResponse]: None to allow normal processing
#     """
#     agent_name = callback_context.agent_name
#     invocation_id = callback_context.invocation_id
#     print(f"[Image Callback] Processing for agent: {agent_name} (Inv: {invocation_id})")

#     # Get the last user message parts
#     last_user_message_parts = []
#     if llm_request.contents and llm_request.contents[-1].role == "user":
#         if llm_request.contents[-1].parts:
#             last_user_message_parts = llm_request.contents[-1].parts

#     print(f"[Image Callback] User message parts count: {last_user_message_parts}")
    
#     # Extract user preference data from message parts
#     if last_user_message_parts:
#         for part in last_user_message_parts:
#             if part.text:
#                 try:
#                     # Try to parse JSON data from the text
#                     user_data = json.loads(part.text)
#                     # If userPreference exists in the data, add it to the agent state
#                     if "userPreference" in user_data:
#                         callback_context.state["userPreference"] = user_data
#                         print(f"[User Preference] Added user data to state: {user_data}")
#                 except json.JSONDecodeError:
#                     # If text is not valid JSON, continue to the next part
#                     continue

#     return None

# # Create main sequential agent
# main_agent = Agent(
#     name="web_search_agent",
#     model=model,
#     description="You are an ai assitant help people with their queries",
#     instruction="""
#     You are an ai assitant help people with their queries.
#     """,
#     # sub_agents=[platform_search_agent, analysis_agent]
#     before_model_callback=before_model_callback
# )


# root_agent = main_agent

# fdc65bf3-6ccb-4ef4-b724-5833c9977716


test = {
	"userId": "user2",
	"sessionId": "test-session-11",
	"analysis_results_twitter": {
		"brand_name": "Tesla",
		"platform_name": "Twitter",
		"total_mentions_on_platform": 3,
		"platform_sentiment_breakdown": {
			"positive": 0.6667,
			"negative": 0,
			"neutral": 0.3333
		},
		"ethical_highlights_on_platform": [
			"Regulatory impact on technology innovation and safety concerns around autonomous vehicles.",
			"Public expectations and media scrutiny of autonomous technology launches.",
			"Federal support for innovation and regulatory harmonization in self-driving technology."
		],
		"word_cloud_themes_on_platform": [
			{
				"word": "autonomous",
				"weight": 8
			},
			{
				"word": "vehicles",
				"weight": 8
			},
			{
				"word": "regulatory",
				"weight": 7
			},
			{
				"word": "technology",
				"weight": 8
			},
			{
				"word": "innovation",
				"weight": 6
			},
			{
				"word": "safety",
				"weight": 5
			},
			{
				"word": "Tesla",
				"weight": 10
			},
			{
				"word": "robotaxi",
				"weight": 6
			},
			{
				"word": "approval",
				"weight": 4
			},
			{
				"word": "launch",
				"weight": 4
			},
			{
				"word": "nation-wide",
				"weight": 4
			},
			{
				"word": "support",
				"weight": 3
			},
			{
				"word": "automakers",
				"weight": 3
			}
		],
		"mentions_on_platform": [
			{
				"date": "2025-04-25",
				"text": "The Trump administration is loosening regulations to support U.S. automakers like Tesla in developing self-driving cars. The United States ...",
				"sentiment": "positive",
				"ethical_context": "Regulatory impact on technology innovation and safety concerns around autonomous vehicles.",
				"url": "https://x.com/Teslarati/status/1915729844157235232"
			},
			{
				"date": "2025-05-19",
				"text": "Tesla Robotaxi is among the biggest tech developments of the year, and its June launch date has not yet arrived. This does not matter to ...",
				"sentiment": "neutral",
				"ethical_context": "Public expectations and media scrutiny of autonomous technology launches.",
				"url": "https://x.com/Teslarati/status/1924553082924417438"
			},
			{
				"date": "2025-04-24",
				"text": "The second win for Tesla is the announcement that the US will move to a nation-wide approval process for Autonomous Vehicles. Tesla has been ...",
				"sentiment": "positive",
				"ethical_context": "Federal support for innovation and regulatory harmonization in self-driving technology.",
				"url": "https://x.com/techAU/status/1915531534242910386"
			}
		]
	},
	"analysis_results_linkedin": {
		"brand_name": "Tesla",
		"platform_name": "LinkedIn",
		"total_mentions_on_platform": 3,
		"platform_sentiment_breakdown": {
			"positive": 1,
			"negative": 0,
			"neutral": 0
		},
		"ethical_highlights_on_platform": [
			"Sustainability and innovation in clean energy technology",
			"AI safety and responsible technology deployment"
		],
		"word_cloud_themes_on_platform": [
			{
				"word": "innovation",
				"weight": 10
			},
			{
				"word": "battery",
				"weight": 8
			},
			{
				"word": "AI",
				"weight": 7
			},
			{
				"word": "technology",
				"weight": 7
			},
			{
				"word": "production",
				"weight": 6
			},
			{
				"word": "vehicle",
				"weight": 7
			},
			{
				"word": "autonomous",
				"weight": 5
			},
			{
				"word": "energy",
				"weight": 6
			},
			{
				"word": "strategy",
				"weight": 5
			},
			{
				"word": "sustainability",
				"weight": 6
			}
		],
		"mentions_on_platform": [
			{
				"date": "2025-05-06",
				"text": "Recent reports from international news outlets indicate that Tesla is significantly accelerating its most ambitious battery initiative in its 21-year history. Sources familiar with the matter suggest the electric vehicle pioneer aims to introduce four entirely new versions of its 4680 battery cell in the year 2026. These advanced power units are reportedly slated to power a range of upcoming Tesla vehicles, including the highly anticipated electric truck Cybertruck and the fully autonomous ride-hailing vehicle Robotaxi, as well as other electric car models. This endeavor represents Tesla's largest simultaneous battery development project to date. ... Timeline: Tesla plans to achieve mass production of these new batteries by the second quarter of 2025, with the full launch of all four cell types slated for 2026.",
				"sentiment": "positive",
				"ethical_context": "Sustainability, innovation in clean energy technology, corporate transparency",
				"url": "https://www.linkedin.com/pulse/tesla-intensifies-efforts-groundbreaking-battery-project-singal-2jr3c"
			},
			{
				"date": "2023-04-19",
				"text": "Artificial Intelligence (AI) is increasingly being utilized in the automotive industry to enhance safety, convenience, and efficiency. One of the pioneers of this trend is Tesla, the electric vehicle company founded by Elon Musk. Tesla has been integrating AI into its cars since its inception and has developed some of the most advanced AI-powered features in the automotive market. The importance of AI in the automotive industry cannot be overstated. With the increasing demand for electric and autonomous vehicles, AI is becoming a key enabler of these technologies. AI-powered features, such as Tesla's Autopilot, have the potential to reduce accidents, enhance the driving experience, and improve energy efficiency.",
				"sentiment": "positive",
				"ethical_context": "AI safety, automotive ethics, consumer benefit, responsible technology deployment",
				"url": "https://www.linkedin.com/pulse/teslas-use-ai-revolutionary-approach-car-technology-alexander-stahl"
			},
			{
				"date": "2024-01-01",
				"text": "This article analyzes the innovation process in Tesla Inc.'s business strategy. Tesla manages its mainstream and newstream innovation process effectively. In addition, the company sought to establish several strategic partnerships to accelerate its technological advancement process. ... Tesla's speed of innovation in the high-end vehicle market makes it more like a Google or an Amazon than an automaker. And its growing market valuation is a clear signal to all car manufacturers that they must develop more innovative business models like Tesla to survive. ... Tesla provides customers with free charging stations, known as Superchargers, throughout the United States and Europe. The company's strategy of building colossal factories, called Gigafactories, has allowed them to increase battery and vehicle production.",
				"sentiment": "positive",
				"ethical_context": "Corporate innovation, competitive dynamics, strategic partnerships, sustainable development",
				"url": "https://www.linkedin.com/pulse/innovation-process-tesla-inc-sandro-saboia-11ybf"
			}
		]
	},
	"analysis_results_reddit": {
		"brand_name": "Tesla",
		"platform_name": "Reddit",
		"total_mentions_on_platform": 3,
		"platform_sentiment_breakdown": {
			"positive": 0,
			"negative": 1,
			"neutral": 0
		},
		"ethical_highlights_on_platform": [
			"Consumer trust and safety concerns",
			"Impact of leadership/politics on brand perception",
			"Product quality and technological innovation compared to competitors",
			"Perceived stagnation in technology"
		],
		"word_cloud_themes_on_platform": [
			{
				"word": "Tesla",
				"weight": 10
			},
			{
				"word": "Tech",
				"weight": 10
			},
			{
				"word": "Technology",
				"weight": 9
			},
			{
				"word": "Elon",
				"weight": 8
			},
			{
				"word": "Americans",
				"weight": 7
			},
			{
				"word": "Safety",
				"weight": 8
			},
			{
				"word": "Quality",
				"weight": 8
			},
			{
				"word": "Politics",
				"weight": 7
			},
			{
				"word": "Advantage",
				"weight": 6
			},
			{
				"word": "Bad",
				"weight": 7
			},
			{
				"word": "Consumers",
				"weight": 6
			},
			{
				"word": "Rivals",
				"weight": 6
			}
		],
		"mentions_on_platform": [
			{
				"date": "Recent",
				"text": "25% of Americans Avoiding Tesla Tech Because of Elon. Americans are avoiding Tesla technology for safety and quality control reasons. Musk's politics may also be alienating some consumers.",
				"sentiment": "negative",
				"ethical_context": "Consumer trust, safety, and the impact of leadership on brand perception.",
				"url": "https://www.reddit.com/r/RealTesla/comments/1hyn3o1/25%5Fof%5Famericans%5Favoiding%5Ftesla%5Ftech%5Fbecause%5Fof/"
			},
			{
				"date": "2 years ago",
				"text": "Where does Tesla's tech advantage sit these days? It seems that Teslas actually have pretty bad tech for a modern car. No sensors, no 360 camera, no CarPlay/AA (debatable, I prefer Teslas UI...",
				"sentiment": "negative",
				"ethical_context": "Product quality and technological innovation compared to competitors.",
				"url": "https://www.reddit.com/r/TeslaModelY/comments/1399rh9/where%5Fdoes%5Fteslas%5Ftech%5Fadvantage%5Fsit%5Fthese%5Fdays/"
			},
			{
				"date": "Recent",
				"text": "Sorry Elon, most Americans are uneasy with this Tesla... The only good tech in Teslas are the battery packs and the engines, and those are thanks to the original founders. Rivals have caught up on both...",
				"sentiment": "negative",
				"ethical_context": "Technological innovation, market competition, and perceived stagnation.",
				"url": "https://www.reddit.com/r/RealTesla/comments/1j5mzyh/sorry%5Felon%5Fmost%5Famericans%5Fare%5Funeasy%5Fwith%5Fthis/"
			}
		]
	},
	"analysis_results_news": {
		"brand_name": "Tesla",
		"platform_name": "News",
		"total_mentions_on_platform": 3,
		"platform_sentiment_breakdown": {
			"positive": 0.6667,
			"negative": 0.3333,
			"neutral": 0
		},
		"ethical_highlights_on_platform": [
			"Innovation ethics, responsible investing, and the societal impact of autonomous technology rollouts.",
			"Data privacy and regulatory compliance relating to artificial intelligence applications."
		],
		"word_cloud_themes_on_platform": [
			{
				"word": "robotaxis",
				"weight": 8
			},
			{
				"word": "autonomous",
				"weight": 7
			},
			{
				"word": "technology",
				"weight": 7
			},
			{
				"word": "investors",
				"weight": 5
			},
			{
				"word": "Austin",
				"weight": 5
			},
			{
				"word": "vehicles",
				"weight": 4
			},
			{
				"word": "Musk",
				"weight": 8
			},
			{
				"word": "compliance",
				"weight": 5
			},
			{
				"word": "privacy",
				"weight": 5
			},
			{
				"word": "self-driving",
				"weight": 6
			}
		],
		"mentions_on_platform": [
			{
				"date": "2025-05-23",
				"text": "Tesla will have 'robotaxis' on the streets of Austin, Texas, by the end of June, CEO Elon Musk told CNBC. The program will start with about 10 self-driving vehicles and rapidly expand to thousands if the launch goes off without incident. Financial experts advise investors to assess risk and perform due diligence before investing in disruptive technologies like autonomous vehicles.",
				"sentiment": "positive",
				"ethical_context": "Innovation ethics, responsible investing, and the societal impact of autonomous technology rollouts.",
				"url": "https://www.cnbc.com/2025/05/23/musk-promises-tesla-robotaxis-what-to-know-about-investing-in-futuristic-tech.html"
			},
			{
				"date": "2025-05-24",
				"text": "Tesla stock has risen over the past month, riding momentum for a major event: the rollout of autonomous robotaxis in Austin, Texas. Wedbush Securities analyst Daniel Ives has raised his price target for Tesla, citing a 'golden age' of autonomous driving technology. He acknowledges that previous controversies involving CEO Elon Musk affected Tesla's brand but says a recommitted Musk is once again leading Tesla into the future.",
				"sentiment": "positive",
				"ethical_context": "Leadership accountability, brand reputation, and technological evolution in public transportation.",
				"url": "https://www.thestreet.com/technology/analyst-sets-eye-popping-tesla-stock-price-target"
			},
			{
				"date": "Recent",
				"text": "Reuters says Musk's AI chatbot sifted federal data without DHS approval.",
				"sentiment": "negative",
				"ethical_context": "Data privacy and regulatory compliance relating to artificial intelligence applications.",
				"url": "https://finance.yahoo.com/news/tesla-slides-grok-rolls-federal-160347875.html"
			}
		]
	}
}