"""
Visual Demo: How Config Influences Agent Responses
Визуальная демонстрация: Как конфиг влияет на ответы агента
"""

from personalization_manager import PersonalizationManager
import os

from dotenv import load_dotenv

# default directory for .env file is the current directory
# if you set .env in different directory, put the directory address load_dotenv("directory_of_.env)
load_dotenv()

def show_config_influence():
    """Visual demonstration of config influence on agent behavior"""
    
    print("\n" + "="*70)
    print("VISUAL DEMO: CONFIG → AGENT → RESPONSES")
    print("="*70)
    
    # Load John Doe config
    manager = PersonalizationManager('personalization_config_john_doe.yaml')
    profile = manager.get_user_profile()
    
    # Show config details
    print("\n📋 CONFIGURATION LOADED:")
    print("-"*70)
    print(f"Name: {profile.name}")
    print(f"Role: {profile.role}")
    print(f"Tech Stack: {profile.experience['primary']}")
    print()
    
    # Show how config influences different aspects
    scenarios = [
        {
            "user_query": "Review my Python code",
            "config_influence": [
                ("Tech Stack", profile.experience['primary'], "Agent knows you use Python/Django"),
                ("Code Style", manager.get_code_style_preferences()[0], "Agent focuses on clean code"),
                ("Communication", manager.get_communication_style()[0], "Agent will be direct and concise"),
            ],
            "agent_behavior": [
                "✓ Reviews code with Django best practices in mind",
                "✓ Checks for clean code principles",
                "✓ Provides direct, technical feedback",
                "✓ Uses Python/Django-specific terminology"
            ]
        },
        {
            "user_query": "What package should I use for HTTP?",
            "config_influence": [
                ("Preferred Packages", "requests, axios", "Agent knows your preferences"),
                ("Tech Stack", "Python + JavaScript", "Agent suggests for both languages"),
            ],
            "agent_behavior": [
                "✓ Recommends 'requests' for Python backend",
                "✓ Suggests 'axios' for JavaScript frontend",
                "✓ Explains why these match your stack",
                "✓ Gives practical examples in your context"
            ]
        },
        {
            "user_query": "I have performance issues",
            "config_influence": [
                ("Recent Challenges", "Database query optimization", "Agent remembers your context"),
                ("Current Project", "ecommerce_platform", "Agent considers your architecture"),
                ("Code Style", "Performance-conscious", "Agent prioritizes performance"),
            ],
            "agent_behavior": [
                "✓ Asks if it's database-related (your recent challenge)",
                "✓ Suggests microservice-specific solutions",
                "✓ Provides Django optimization techniques",
                "✓ Focuses on scalability for e-commerce"
            ]
        },
        {
            "user_query": "Help me learn GraphQL",
            "config_influence": [
                ("Goals", "Master GraphQL APIs", "Agent knows this is your goal"),
                ("Tech Stack", "Django + React", "Agent tailors examples"),
                ("Learning Style", "Hands-on experimentation", "Agent provides code"),
            ],
            "agent_behavior": [
                "✓ Excited to help (knows it's your goal)",
                "✓ Shows GraphQL with Django (graphene-django)",
                "✓ Provides React client examples (Apollo)",
                "✓ Includes hands-on exercises",
                "✓ Relates to your microservices architecture"
            ]
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{'─'*70}")
        print(f"SCENARIO {i}: {scenario['user_query']}")
        print(f"{'─'*70}")
        
        print(f"\n👤 User Query:")
        print(f"   \"{scenario['user_query']}\"")
        
        print(f"\n⚙️  Config Influence:")
        for aspect, value, explanation in scenario['config_influence']:
            print(f"   • {aspect}: {value}")
            print(f"     → {explanation}")
        
        print(f"\n🤖 Agent Behavior:")
        for behavior in scenario['agent_behavior']:
            print(f"   {behavior}")
    
    print("\n" + "="*70)
    print("COMPARISON: Generic vs Personalized")
    print("="*70)
    
    comparisons = [
        {
            "query": "How do I optimize my code?",
            "generic": "Use caching, optimize loops, minimize database queries...",
            "personalized": """Given your Django/PostgreSQL stack:
1. Use select_related() and prefetch_related()
2. Add Redis caching (you're building microservices)
3. Database indexes on frequently queried fields
4. Consider your ecommerce use case - product catalog caching

Here's a Django example for your project..."""
        },
        {
            "query": "What testing framework should I use?",
            "generic": "pytest, unittest, Jest are popular options...",
            "personalized": """For your stack:
- Backend: pytest (already in your preferred packages)
- Frontend: Jest with React Testing Library
- E2E: Cypress for your microservices

I see you value comprehensive testing (from your code style), 
so also consider coverage.py for Python and Istanbul for JS."""
        }
    ]
    
    for comp in comparisons:
        print(f"\n📝 Query: \"{comp['query']}\"")
        print(f"\n❌ Generic Response:")
        print(f"   {comp['generic']}")
        print(f"\n✅ Personalized Response (John Doe config):")
        for line in comp['personalized'].strip().split('\n'):
            print(f"   {line}")
        print()
    
    print("="*70)
    print("KEY TAKEAWAYS")
    print("="*70)
    print("""
1. 🎯 Config → Context
   Your profile, tech stack, and preferences become the agent's context

2. 🧠 Context → Understanding
   Agent understands your specific situation and constraints

3. 💡 Understanding → Relevant Advice
   Agent provides advice tailored to YOUR project, not generic tips

4. 🚀 Relevant Advice → Better Results
   You get actionable solutions faster because they fit your context

FORMULA: Good Config + Personalized Agent = 10x Better Responses
    """)
    print("="*70)


def show_system_prompt_preview():
    """Show how config becomes system prompt"""
    
    print("\n" + "="*70)
    print("HOW CONFIG BECOMES SYSTEM PROMPT")
    print("="*70)
    
    manager = PersonalizationManager('personalization_config_john_doe.yaml')
    
    print("\n1️⃣  YAML Config (Input):")
    print("-"*70)
    print("""
user_profile:
  name: "John Doe"
  role: "Full-Stack Software Developer"
  experience:
    primary: "Python/Django, JavaScript/React"
    
work_context:
  current_project: "ecommerce_platform"
  architecture: "Microservices with REST APIs"
  focus_areas:
    - "Backend API development"
    - "Database optimization"
    """)
    
    print("\n2️⃣  PersonalizationManager (Processing):")
    print("-"*70)
    print("   📝 Loads YAML config")
    print("   🔄 Processes user profile")
    print("   🏗️  Builds system prompt")
    print("   ✓ Ready for agent")
    
    print("\n3️⃣  System Prompt (Output):")
    print("-"*70)
    prompt = manager.build_system_prompt()
    print(prompt[:600])
    print("\n   ... (full prompt is ~1800 characters)")
    
    print("\n4️⃣  Agent Uses Prompt:")
    print("-"*70)
    print("   🤖 Every message to Claude includes this system prompt")
    print("   🎯 Claude understands who you are and what you need")
    print("   💬 Responses are personalized automatically")
    
    print("\n" + "="*70)


def interactive_demo():
    """Interactive demo showing config influence"""
    
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\n⚠️  ANTHROPIC_API_KEY not set")
        print("This would show live API responses with personalization")
        print("\nFor now, showing config influence analysis...")
        return
    
    print("\n" + "="*70)
    print("INTERACTIVE DEMO")
    print("="*70)
    
    try:
        from personalized_claude_agent import PersonalizedClaudeAgent
        
        print("\n✨ Initializing agent with John Doe config...")
        print("(Watch for config details on initialization)")
        
        agent = PersonalizedClaudeAgent(
            config_path='personalization_config_john_doe.yaml'
        )
        
        print("\n💬 Asking: 'What HTTP library should I use?'")
        print("(Watch for applied personalizations)")
        
        response = agent.chat("What HTTP library should I use?", max_tokens=300)
        
        print(f"\n🤖 Response Preview:")
        print(f"{response[:200]}...")
        
        print("\n📊 Notice how the response:")
        print("   ✓ Mentions your preferred packages (requests, axios)")
        print("   ✓ Considers both Python and JavaScript")
        print("   ✓ Relates to your project context")
        print("   ✓ Matches your communication style")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nBut the config influence would still apply!")


if __name__ == "__main__":
    print("\n" + "🎯 CONFIG → AGENT → RESPONSES DEMO ".center(70, "="))
    
    # Show config influence
    show_config_influence()
    
    # Show system prompt generation
    show_system_prompt_preview()
    
    # Interactive demo (if API key available)
    interactive_demo()
    
    print("\n" + "="*70)
    print("🎓 SUMMARY")
    print("="*70)
    print("""
The connection is clear:

personalization_config_john_doe.yaml
         ↓
PersonalizationManager (loads and processes)
         ↓
System Prompt (personalized instructions)
         ↓
PersonalizedClaudeAgent (uses prompt)
         ↓
Claude API (receives context)
         ↓
Personalized Responses (tailored to you)

Your config IS the agent's knowledge about you!
    """)
    print("="*70)
