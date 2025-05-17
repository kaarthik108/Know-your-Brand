import asyncio
import argparse
import json
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from web_search_agent.agent import root_agent
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def main():
    parser = argparse.ArgumentParser(description='Brand Mention Monitoring Tool')
    parser.add_argument('--brand', required=True, help='Brand or company name to monitor')
    parser.add_argument('--category', help='Business category or industry')
    parser.add_argument('--location', help='Geographic location of interest')
    args = parser.parse_args()
    
    agent = root_agent
    session_service = InMemorySessionService()
    app_name = "brand_monitor"
    user_id = "user_1"
    session_id = f"brand_monitor_{args.brand.lower().replace(' ', '_')}"
    
    session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id
    )
    runner = Runner(
        agent=agent,
        app_name=app_name,
        session_service=session_service
    )
    
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
    
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=user_content
    ):
        if event.is_final_response() and event.content and event.content.parts:
            print("Brand Mention Analysis:")
            print("-" * 50)
            response_text = event.content.parts[0].text
            
            try:
                final_response = json.loads(response_text)
                output_file = f"output_{args.brand.lower().replace(' ', '_')}.json"
                with open(output_file, 'w') as f:
                    json.dump(final_response, f, indent=4)
                print(f"Results saved to {output_file}")
            except json.JSONDecodeError:
                print(f"Agent did not return valid JSON: {response_text}")
                final_response = {"answerText": response_text}
            print("final_response\n\n", final_response)

if __name__ == "__main__":
    asyncio.run(main())