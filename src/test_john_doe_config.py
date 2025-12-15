"""
John Doe Configuration Test
Тест конфигурации John Doe
"""

from personalization_manager import PersonalizationManager
import os

from dotenv import load_dotenv

load_dotenv()

def test_john_doe_config():
    """Test the John Doe configuration"""
    
    print("="*70)
    print("JOHN DOE CONFIGURATION TEST")
    print("="*70)
    
    # Load John Doe config
    manager = PersonalizationManager('personalization_config_john_doe.yaml')
    
    # Display profile summary
    print("\n📋 Profile Summary:")
    print(manager.get_summary())
    
    # Show communication preferences
    print("\n💬 Communication Style:")
    for style in manager.get_communication_style():
        print(f"  • {style}")
    
    # Show code style preferences
    print("\n📐 Code Style:")
    for style in manager.get_code_style_preferences():
        print(f"  • {style}")
    
    # Show preferred tools
    print("\n🛠️  Preferred Tools:")
    tools = manager.get_preferred_tools()
    print(f"  IDE: {tools['ide']}")
    print(f"  State Management: {tools['state_management']}")
    print(f"  Packages:")
    for pkg in tools['preferred_packages']:
        print(f"    • {pkg}")
    
    # Show current context
    print("\n💼 Current Context:")
    context = manager.get_current_context()
    print(f"  Project: {context['work']['current_project']}")
    print(f"  Recent Challenges:")
    for challenge in context['recent_challenges']:
        print(f"    • {challenge}")
    
    # Show goals
    print("\n🎯 Goals:")
    goals = manager.get_goals()
    print("  Short-term:")
    for goal in goals['short_term']:
        print(f"    • {goal}")
    
    # Test optimization detection
    print("\n🔍 Optimization Detection Test:")
    test_cases = [
        "Here's my code with nested for loops",
        "Performance issue with database queries",
        "Simple hello world function"
    ]
    for case in test_cases:
        should_optimize = manager.should_suggest_optimization(case)
        status = "🔧 SUGGEST" if should_optimize else "  SKIP"
        print(f"  {status}: {case}")
    
    # Test package recommendations
    print("\n📦 Package Recommendations:")
    for task in ['networking', 'state', 'testing']:
        packages = manager.get_relevant_packages(task)
        print(f"  {task}: {', '.join(packages)}")
    
    print("\n" + "="*70)
    print("✅ Configuration test completed!")
    print("\nThis config represents a full-stack developer named John Doe who:")
    print("  • Works with Python/Django and JavaScript/React")
    print("  • Builds microservices architecture")
    print("  • Values clean code and performance")
    print("  • Is learning GraphQL and Kubernetes")
    print("="*70)


def test_with_api():
    """Test with Claude API if available"""
    
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\n⚠️  ANTHROPIC_API_KEY not set. Skipping API test.")
        print("To test with API, run:")
        print("  export ANTHROPIC_API_KEY='your-key'")
        print("  python test_john_doe_config.py")
        return
    
    print("\n" + "="*70)
    print("TESTING WITH CLAUDE API")
    print("="*70)
    
    try:
        # Import only if API key is available
        from personalized_claude_agent import PersonalizedClaudeAgent
        
        # Initialize agent with John Doe config
        agent = PersonalizedClaudeAgent(
            config_path='personalization_config_john_doe.yaml'
        )
        
        # Test question
        print("\n👤 John Doe: How should I optimize my Django API queries?")
        response = agent.chat("How should I optimize my Django API queries?")
        print(f"\n🤖 Claude: {response[:300]}...")
        
        print("\n✅ API test successful!")
        
    except Exception as e:
        print(f"\n❌ API test failed: {e}")


if __name__ == "__main__":
    # Run configuration test
    test_john_doe_config()
    
    # Try API test if key is available
    test_with_api()
    
    print("\n💡 Usage:")
    print("  # Use John Doe config in your code:")
    print("  agent = PersonalizedClaudeAgent(")
    print("      config_path='personalization_config_john_doe.yaml'")
    print("  )")
    print("  response = agent.chat('Your question')")
