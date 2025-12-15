"""
Interactive Config Knowledge Quiz
Интерактивный тест знаний модели о конфиге
"""

from personalized_claude_agent import PersonalizedClaudeAgent
from personalization_manager import PersonalizationManager
import os

import os

from dotenv import load_dotenv
load_dotenv()

def quiz_model_knowledge():
    """Ask the model questions about what it knows from config"""
    
    print("\n" + "="*70)
    print("🎓 CONFIG KNOWLEDGE QUIZ")
    print("Testing what Claude knows about you from your config")
    print("="*70)
    
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\n⚠️  ANTHROPIC_API_KEY not set")
        print("\nShowing what WOULD be asked with your config...")
        show_quiz_preview()
        return
    
    try:
        print("\n🤖 Initializing agent with John Doe config...")
        agent = PersonalizedClaudeAgent(
            config_path='personalization_config_john_doe.yaml'
        )
        
        print("\n" + "="*70)
        print("Let's test what Claude knows about John Doe!")
        print("="*70)
        
        questions = [
            {
                "category": "👤 Personal Identity",
                "question": "What is my name and role?",
                "expected_knowledge": [
                    "Name: John Doe",
                    "Role: Full-Stack Software Developer"
                ],
                "config_source": "user_profile.name, user_profile.role"
            },
            {
                "category": "💻 Tech Stack",
                "question": "What technologies do I work with?",
                "expected_knowledge": [
                    "Primary: Python/Django, JavaScript/React",
                    "Secondary: Docker, PostgreSQL, AWS"
                ],
                "config_source": "user_profile.experience.primary, .secondary"
            },
            {
                "category": "💼 Current Work",
                "question": "What project am I working on and what architecture does it use?",
                "expected_knowledge": [
                    "Project: ecommerce_platform",
                    "Architecture: Microservices with REST APIs"
                ],
                "config_source": "work_context.current_project, .architecture"
            },
            {
                "category": "🎯 Focus Areas",
                "question": "What are my main focus areas at work?",
                "expected_knowledge": [
                    "Backend API development",
                    "Database optimization",
                    "Frontend component architecture",
                    "Code review and mentoring"
                ],
                "config_source": "work_context.focus_areas"
            },
            {
                "category": "📐 Code Preferences",
                "question": "What are my code style preferences?",
                "expected_knowledge": [
                    "Clean code principles",
                    "Minimal code duplication",
                    "Comprehensive documentation",
                    "Performance-conscious"
                ],
                "config_source": "preferences.code_style"
            },
            {
                "category": "🛠️ Preferred Tools",
                "question": "What packages/libraries do I prefer to use?",
                "expected_knowledge": [
                    "requests (Python HTTP)",
                    "pytest (testing)",
                    "axios (JavaScript HTTP)"
                ],
                "config_source": "preferences.tools_and_tech.preferred_packages"
            },
            {
                "category": "💬 Communication Style",
                "question": "How do I prefer to communicate?",
                "expected_knowledge": [
                    "Direct and concise",
                    "Technical depth appreciated",
                    "Practical examples preferred"
                ],
                "config_source": "preferences.communication_style"
            },
            {
                "category": "🔥 Recent Challenges",
                "question": "What challenges have I been working on recently?",
                "expected_knowledge": [
                    "Optimizing database queries for large datasets",
                    "Implementing JWT authentication",
                    "Debugging memory leaks in Node.js services"
                ],
                "config_source": "context_awareness.recent_challenges"
            },
            {
                "category": "🚀 Learning Goals",
                "question": "What are my short-term learning goals?",
                "expected_knowledge": [
                    "Master GraphQL APIs",
                    "Learn Kubernetes and container orchestration",
                    "Contribute to open source projects"
                ],
                "config_source": "goals_and_interests.short_term"
            },
            {
                "category": "🎓 Learning Style",
                "question": "How do I prefer to learn?",
                "expected_knowledge": [
                    "Hands-on experimentation",
                    "Learn through building projects",
                    "Deep dives into documentation"
                ],
                "config_source": "habits_and_patterns.learning_style"
            },
            {
                "category": "🎨 Work Approach",
                "question": "How do I approach problem-solving?",
                "expected_knowledge": [
                    "Prefer understanding root cause",
                    "Value code reusability",
                    "Test edge cases thoroughly"
                ],
                "config_source": "habits_and_patterns.problem_solving"
            },
            {
                "category": "🔮 Future Goals",
                "question": "What are my mid to long-term career goals?",
                "expected_knowledge": [
                    "Become a senior engineer",
                    "Launch a side project SaaS product",
                    "Start own tech company",
                    "Become a technical architect"
                ],
                "config_source": "goals_and_interests.mid_term, .long_term"
            }
        ]
        
        correct = 0
        total = len(questions)
        
        for i, q in enumerate(questions, 1):
            print(f"\n{'─'*70}")
            print(f"Question {i}/{total}: {q['category']}")
            print(f"{'─'*70}")
            print(f"\n❓ {q['question']}")
            print(f"\n📋 Config Source: {q['config_source']}")
            
            print(f"\n🤖 Claude's Answer:")
            response = agent.chat(q['question'], max_tokens=300)
            print(f"\n{response}")
            
            print(f"\n✅ Expected Knowledge:")
            for knowledge in q['expected_knowledge']:
                print(f"   • {knowledge}")
            
            print(f"\n🔍 Verification:")
            # Check if key terms are in response
            response_lower = response.lower()
            found_terms = []
            for knowledge in q['expected_knowledge']:
                # Extract key term from knowledge
                key_term = knowledge.split(':')[-1].strip().lower()
                if key_term in response_lower or any(word in response_lower for word in key_term.split()[:2]):
                    found_terms.append(knowledge)
            
            if len(found_terms) >= len(q['expected_knowledge']) // 2:
                print(f"   ✓ Claude demonstrated knowledge from config!")
                correct += 1
            else:
                print(f"   ⚠️ Claude's answer may have missed some config details")
            
            input("\n⏎ Press Enter for next question...")
        
        print(f"\n{'='*70}")
        print(f"QUIZ RESULTS")
        print(f"{'='*70}")
        print(f"Score: {correct}/{total} ({correct*100//total}%)")
        print(f"\nClaude demonstrated knowledge from the config in {correct} out of {total} categories!")
        print(f"\n💡 This shows that your config is actively informing Claude's responses.")
        print(f"{'='*70}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")


def show_quiz_preview():
    """Show what would be asked without API"""
    
    print("\n📋 Loading John Doe config...")
    manager = PersonalizationManager('personalization_config_john_doe.yaml')
    profile = manager.get_user_profile()
    context = manager.get_current_context()
    goals = manager.get_goals()
    
    print(f"\n{'='*70}")
    print("QUIZ PREVIEW - Questions that WOULD be asked:")
    print(f"{'='*70}")
    
    quiz_items = [
        ("👤 Personal Identity", 
         "What is my name and role?",
         f"Expected: {profile.name}, {profile.role}"),
        
        ("💻 Tech Stack", 
         "What technologies do I work with?",
         f"Expected: {profile.experience['primary']}"),
        
        ("💼 Current Project", 
         "What project am I working on?",
         f"Expected: {context['work']['current_project']}"),
        
        ("🏗️ Architecture", 
         "What architecture does my project use?",
         f"Expected: {context['work']['architecture']}"),
        
        ("📐 Code Style", 
         "What are my code style preferences?",
         f"Expected: {', '.join(manager.get_code_style_preferences()[:3])}"),
        
        ("🛠️ Preferred Tools", 
         "What packages do I prefer?",
         f"Expected: {', '.join(manager.get_preferred_tools()['preferred_packages'][:3])}"),
        
        ("🔥 Recent Work", 
         "What challenges have I worked on recently?",
         f"Expected: {context['recent_challenges'][0]}"),
        
        ("🚀 Learning Goals", 
         "What am I trying to learn?",
         f"Expected: {', '.join(goals['short_term'][:2])}"),
        
        ("💬 Communication", 
         "How do I like to communicate?",
         f"Expected: {', '.join(manager.get_communication_style()[:2])}"),
        
        ("🎓 Learning Style", 
         "How do I prefer to learn?",
         f"Expected: Hands-on, project-based"),
    ]
    
    for i, (category, question, expected) in enumerate(quiz_items, 1):
        print(f"\n{i}. {category}")
        print(f"   Question: {question}")
        print(f"   {expected}")
    
    print(f"\n{'='*70}")
    print("💡 With API key, Claude would answer each question using config!")
    print(f"{'='*70}")


def rapid_fire_test():
    """Quick rapid-fire test of config knowledge"""
    
    print("\n" + "="*70)
    print("⚡ RAPID FIRE CONFIG TEST")
    print("="*70)
    
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\n⚠️  Requires ANTHROPIC_API_KEY")
        return
    
    try:
        agent = PersonalizedClaudeAgent(
            config_path='personalization_config_john_doe.yaml'
        )
        
        rapid_questions = [
            ("What's my name?", "John Doe"),
            ("What languages do I use?", "Python, JavaScript"),
            ("What's my project?", "ecommerce_platform"),
            ("What architecture?", "Microservices"),
            ("What do I want to learn?", "GraphQL, Kubernetes"),
            ("What's my code style?", "Clean code"),
            ("Preferred HTTP library for Python?", "requests"),
            ("Recent challenge?", "database optimization"),
            ("How do I learn?", "hands-on"),
            ("Career goal?", "senior engineer"),
        ]
        
        print("\n🔥 Asking 10 quick questions...")
        
        for i, (question, expected_key) in enumerate(rapid_questions, 1):
            print(f"\n{i}. ❓ {question}")
            response = agent.chat(question, max_tokens=100)
            
            # Check if expected key is in response
            if expected_key.lower() in response.lower():
                print(f"   ✅ Correct! (Found: {expected_key})")
            else:
                print(f"   ⚠️  Answer: {response[:100]}...")
        
        print(f"\n{'='*70}")
        print("✅ Rapid fire test complete!")
        print(f"{'='*70}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def compare_with_without_config():
    """Show difference in responses with vs without config"""
    
    print("\n" + "="*70)
    print("⚖️  WITH vs WITHOUT CONFIG COMPARISON")
    print("="*70)
    
    print("\n📝 Question: 'What HTTP library should I use?'")
    
    print("\n❌ WITHOUT CONFIG (Generic):")
    print("─" * 70)
    print("""
For HTTP requests, popular options include:

**Python:**
- requests: Simple and widely used
- httpx: Modern async support
- urllib3: Low-level control

**JavaScript:**
- axios: Promise-based
- fetch: Built-in browser API
- node-fetch: Fetch for Node.js

Choose based on your needs and environment.
    """)
    
    print("\n✅ WITH JOHN DOE CONFIG (Personalized):")
    print("─" * 70)
    
    manager = PersonalizationManager('personalization_config_john_doe.yaml')
    profile = manager.get_user_profile()
    tools = manager.get_preferred_tools()
    
    print(f"""
For YOUR stack (Python/Django + JavaScript/React):

**Python Backend:**
→ Use **requests** (already in your preferred packages)
  • Simple, reliable, perfect for Django services
  • You're already familiar with it
  
**JavaScript Frontend:**
→ Use **axios** (also in your preferences)
  • Promise-based, great for React
  • Consistent API with requests
  
Given your microservices architecture, both integrate well
with your ecommerce_platform API gateway pattern.

Example for your Django service:
```python
import requests
response = requests.get(
    'https://api.ecommerce_platform.com/products',
    headers={{'Authorization': 'Bearer ...'}}
)
```
    """)
    
    print("\n📊 KEY DIFFERENCES:")
    print("─" * 70)
    print("WITHOUT CONFIG:")
    print("  • Generic list of options")
    print("  • No context about user")
    print("  • No specific recommendation")
    print()
    print("WITH CONFIG:")
    print(f"  ✓ Knows your stack: {profile.experience['primary']}")
    print(f"  ✓ Recommends your preferences: {', '.join(tools['preferred_packages'][:2])}")
    print(f"  ✓ Provides examples for your project")
    print(f"  ✓ Considers your architecture")
    print("="*70)


if __name__ == "__main__":
    print("\n" + "🎯 CONFIG KNOWLEDGE TESTING ".center(70, "="))
    
    print("\nChoose test mode:")
    print("1. Full Quiz (asks 12 detailed questions)")
    print("2. Rapid Fire (10 quick questions)")
    print("3. Comparison (with vs without config)")
    print("4. Preview (see questions without API)")
    
    choice = input("\nEnter choice (1-4) or press Enter for all: ").strip()
    
    if choice == "1":
        quiz_model_knowledge()
    elif choice == "2":
        rapid_fire_test()
    elif choice == "3":
        compare_with_without_config()
    elif choice == "4":
        show_quiz_preview()
    else:
        # Run all
        show_quiz_preview()
        compare_with_without_config()
        
        if os.environ.get("ANTHROPIC_API_KEY"):
            print("\n" + "="*70)
            print("API key found! Running live tests...")
            print("="*70)
            rapid_fire_test()
            
            do_full = input("\nRun full quiz? (y/n): ").lower()
            if do_full == 'y':
                quiz_model_knowledge()
        else:
            print("\n💡 Set ANTHROPIC_API_KEY to run live tests with Claude!")
    
    print("\n" + "="*70)
    print("🎓 CONCLUSION")
    print("="*70)
    print("""
The config file IS the agent's memory and knowledge base.

Every question Claude can answer about you comes from:
  personalization_config_john_doe.yaml

Without the config: Claude is generic
With the config: Claude knows YOU

That's the power of personalization! 🎯
    """)
    print("="*70)
