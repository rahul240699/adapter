#!/usr/bin/env python3
import os
from ..core.nanda import NANDA
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_anthropic import ChatAnthropic

def create_seafood_expert_improvement():
    """Create a LangChain-powered seafood expert improvement function"""

    # Initialize the LLM
    llm = ChatAnthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        model="claude-3-haiku-20240307"
    )

    # Create a prompt template for seafood expert transformation
    prompt = PromptTemplate(
        input_variables=["message"],
        template="""You are a knowledgeable seafood expert with 20+ years of experience in marine biology, 
sustainable fishing, and seafood preparation. Transform the following message by adding relevant seafood 
expertise, facts, and recommendations while maintaining the original intent.

Guidelines:
- Add scientific names when mentioning seafood
- Include sustainability information
- Mention preparation techniques when relevant
- Share interesting facts about marine life
- Recommend seasonal availability
- Discuss flavor profiles and pairings
- Keep the core message intact but enhance it with seafood knowledge

Original message: {message}

Enhanced seafood expert response:"""
    )

    # Create the chain
    chain = prompt | llm | StrOutputParser()

    def seafood_expert_improvement(message_text: str) -> str:
        """Transform message with seafood expertise"""
        try:
            result = chain.invoke({"message": message_text})
            return result.strip()
        except Exception as e:
            print(f"Error in seafood expert improvement: {e}")
            return f"As a seafood expert, I'd say: {message_text} - Speaking of which, did you know that sustainable fishing practices are crucial for maintaining healthy ocean ecosystems?"

    return seafood_expert_improvement

def main():
    """Main function to start the seafood expert agent"""

    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Please set your ANTHROPIC_API_KEY environment variable")
        return

    # Create seafood expert improvement function
    seafood_logic = create_seafood_expert_improvement()

    # Initialize NANDA with seafood expert logic
    nanda = NANDA(seafood_logic)

    # Start the server
    print("Starting Seafood Expert Agent with LangChain...")
    print("All messages will be enhanced with seafood expertise!")

    domain = os.getenv("DOMAIN_NAME", "localhost")

    if domain != "localhost":
        # Production with SSL
        nanda.start_server_api(os.getenv("ANTHROPIC_API_KEY"), domain)
    else:
        # Development server
        nanda.start_server()

if __name__ == "__main__":
    main()