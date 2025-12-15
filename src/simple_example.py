"""
Simple Usage Example - Personalized Claude Agent
Простой пример использования персонализированного агента
"""

from personalized_claude_agent import PersonalizedClaudeAgent
import os

from dotenv import load_dotenv

load_dotenv()

def main():
    """Simple example of using PersonalizedClaudeAgent"""
    
    print("="*70)
    print("Personalized Claude Agent - Simple Example")
    print("="*70)
    
    # Check API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\n❌ Error: ANTHROPIC_API_KEY not found")
        print("\nPlease set your API key:")
        print("  export ANTHROPIC_API_KEY='your-api-key-here'")
        print("\nOr in Python:")
        print("  import os")
        print("  os.environ['ANTHROPIC_API_KEY'] = 'your-api-key-here'")
        return
    
    # Initialize agent with your personalization config
    print("\n1. Initializing agent...")
    agent = PersonalizedClaudeAgent(
        config_path="personalization_config_john_doe.yaml",
        model="claude-sonnet-4-20250514"  # or claude-opus-4-20250514 for more powerful
    )
    
    # Show your profile
    print("\n2. Your Profile:")
    print(agent.get_profile_summary())
    
    # Have a conversation
    print("\n3. Starting conversation...")
    print("-"*70)
    
    # Example 1: Ask a technical question
    print("\n👤 You: What's the best way to handle errors in my code?")
    response = agent.chat("What's the best way to handle errors in my code?")
    print(f"\n🤖 Claude: {response}\n")
    
    # Example 2: Code review (context-aware)
    print("\n👤 You: Review this code snippet")
    code = """
def process_data(items):
    result = []
    for item in items:
        result.append(item * 2)
    return result
    """
    response = agent.chat(f"Review this code:\n{code}")
    print(f"\n🤖 Claude: {response}\n")
    
    # Example 3: Get personalized suggestions
    print("\n👤 You: What should I learn next?")
    response = agent.suggest_next_steps("Currently working on backend APIs")
    print(f"\n🤖 Claude: {response}\n")
    
    # Show conversation stats
    print("-"*70)
    stats = agent.get_conversation_summary()
    print(f"\n📊 Conversation Stats:")
    print(f"   Total messages: {stats['message_count']}")
    print(f"   Your messages: {stats['user_messages']}")
    print(f"   Claude's messages: {stats['assistant_messages']}")
    print(f"   Total characters: {stats['total_chars']:,}")
    
    # Export conversation (optional)
    # agent.export_conversation("my_conversation.json")
    
    print("\n" + "="*70)
    print("✅ Example completed!")
    print("\nTips:")
    print("  • Edit personalization_config_john_doe.yaml to customize")
    print("  • Use stream=True for streaming responses")
    print("  • Call agent.reset_conversation() to start fresh")
    print("="*70)


if __name__ == "__main__":
    main()
