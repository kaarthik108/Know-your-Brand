import asyncio
import argparse
import json
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from web_search_agent.agent import create_agent
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def main():
    parser = argparse.ArgumentParser(description='Brand Mention Monitoring Tool')
    parser.add_argument('--brand', required=True, help='Brand or company name to monitor')
    parser.add_argument('--category', help='Business category or industry')
    parser.add_argument('--location', help='Geographic location of interest')
    args = parser.parse_args()
    
    # Create agent
    agent, exit_stack = await create_agent()
    
    try:
        # Set up session
        session_service = InMemorySessionService()
        app_name = "brand_monitor"
        user_id = "user_1"
        session_id = f"brand_monitor_{args.brand.lower().replace(' ', '_')}"
        
        session_service.create_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id
        )
        
        # Create runner for agent execution
        runner = Runner(
            agent=agent,
            app_name=app_name,
            session_service=session_service
        )
        
        # Prepare input message
        input_data = {
            "brand_name": args.brand,
            "category": args.category,
            "location": args.location
        }
        input_json = json.dumps(input_data)
        
        print(f"\nStarting brand mention monitoring for: {args.brand}")
        print(f"Category: {args.category if args.category else 'Not specified'}")
        print(f"Location: {args.location if args.location else 'Not specified'}")
        print("This may take a few minutes...\n")
        
        # Run agent with input
        user_content = types.Content(
            role='user',
            parts=[types.Part(text=input_json)]
        )
        
        # Process events and display results
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=user_content
        ):
            if event.is_final_response() and event.content and event.content.parts:
                print("Brand Mention Analysis:")
                print("-" * 50)
                # print(event.content.parts[0].text)
                
                # Get the complete analysis from state
                session = session_service.get_session(
                    app_name=app_name,
                    user_id=user_id,
                    session_id=session_id
                )
                
                analysis = session.state.get("analysis_results")
                print(analysis)
                # if analysis:
                #     try:
                #         analysis_data = json.loads(analysis)
                #         print("\nDetailed Analysis:")
                #         print("-" * 50)
                #         print(f"Total Mentions: {analysis_data.get('total_mentions', 0)}")
                        
                #         # Print sentiment breakdown
                #         print("\nSentiment Breakdown:")
                #         sentiment = analysis_data.get('sentiment_breakdown', {})
                #         for key, value in sentiment.items():
                #             print(f"  {key}: {value}")
                        
                #         # Print ethical highlights
                #         print("\nEthical Highlights:")
                #         highlights = analysis_data.get('ethical_highlights', [])
                #         for highlight in highlights:
                #             print(f"  • {highlight}")
                            
                #         # Print sample mentions
                #         print("\nSample Mentions:")
                #         mentions = analysis_data.get('detailed_mentions', [])
                #         for i, mention in enumerate(mentions[:5]):  # Show first 5 mentions
                #             print(f"\n[{i+1}] Platform: {mention.get('platform')}")
                #             print(f"    Date: {mention.get('date')}")
                #             print(f"    Sentiment: {mention.get('sentiment')}")
                #             if mention.get('url'):
                #                 print(f"    URL: {mention.get('url')}")
                #             print(f"    Text: {mention.get('text')[:200]}...")
                #     except json.JSONDecodeError:
                #         print("Could not parse analysis results as JSON")
                
    finally:
        # Clean up resources
        await exit_stack.aclose()

if __name__ == "__main__":
    asyncio.run(main())