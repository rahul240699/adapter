#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Ensure local checkout of nanda_adapter is used before any installed package
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nanda_adapter.core.nanda import NANDA
from crewai import Agent, Task, Crew
from langchain_anthropic import ChatAnthropic

def create_chef_improvement():
    """Create a CrewAI-powered chef improvement function"""
    
    # Initialize the LLM
    llm = ChatAnthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        model="claude-3-haiku-20240307"
    )
    
    # Create a professional chef agent
    chef_agent = Agent(
        role="Professional Chef and Culinary Expert",
        goal="Transform messages by adding culinary expertise, cooking techniques, and food knowledge while maintaining the original message intent",
        backstory="""You are a world-renowned chef with expertise in multiple cuisines, advanced cooking techniques, 
        food science, and restaurant management. You have trained in Michelin-starred kitchens and understand 
        both traditional and modern culinary arts. You excel at connecting any topic to food, cooking, or culinary culture, 
        and you love sharing cooking tips, ingredient knowledge, and culinary techniques.""",
        verbose=True,
        allow_delegation=False,
        llm=llm
    )
    
    def chef_improvement(message_text: str) -> str:
        """Transform message with culinary expertise"""
        try:
            # Create a task for the culinary transformation
            chef_task = Task(
                description=f"""Transform the following message by enhancing it with culinary expertise and knowledge.
                
                Guidelines:
                - Add relevant cooking techniques, ingredients, or food science when applicable
                - Include flavor profiles, seasonings, or cooking methods
                - Mention kitchen tools or equipment when relevant
                - Share culinary traditions or cultural food connections
                - Suggest recipes, pairings, or preparation methods
                - Keep the original message intent but enhance with culinary wisdom
                - Be passionate and knowledgeable about food
                
                Original message: {message_text}
                
                Provide the enhanced message with culinary expertise integrated naturally.""",
                expected_output="A message enhanced with culinary knowledge and chef expertise",
                agent=chef_agent
            )
            
            # Create and run the crew
            crew = Crew(
                agents=[chef_agent],
                tasks=[chef_task],
                verbose=True
            )
            
            result = crew.kickoff()
            return str(result).strip()
            
        except Exception as e:
            print(f"Error in chef improvement: {e}")
            return f"As a chef, I'd say: {message_text} - You know, this reminds me of the importance of mise en place in the kitchen - having everything prepared and in its place leads to success!"
    
    return chef_improvement

def main():
    """Main function to start the chef agent"""
    
    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Please set your ANTHROPIC_API_KEY environment variable")
        return
    
    # Create chef improvement function
    chef_logic = create_chef_improvement()
    
    # Initialize NANDA with chef logic
    nanda = NANDA(chef_logic)
    
    # Start the server
    print("Starting Chef Agent with CrewAI...")
    print("All messages will be enhanced with culinary expertise!")
    
    domain = os.getenv("DOMAIN_NAME", "localhost")
    
    if domain != "localhost":
        # Production with SSL
        nanda.start_server_api(os.getenv("ANTHROPIC_API_KEY"), domain)
    else:
        # Development server
        nanda.start_server()

if __name__ == "__main__":
    main()
