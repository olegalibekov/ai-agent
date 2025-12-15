"""
Interactive Config Tracing Demo
Интерактивная демонстрация отслеживания конфига
"""

from personalization_manager import PersonalizationManager
import os


def trace_config_flow():
    """Trace how config flows through the system"""
    
    print("\n" + "="*70)
    print("🔍 CONFIG FLOW TRACING")
    print("="*70)
    
    print("\n" + "STEP 1: Loading Configuration File".center(70, "─"))
    print("\n📂 File: personalization_config_john_doe.yaml")
    
    # Show raw config excerpt
    print("\n📄 Raw YAML Content (excerpt):")
    print("""
user_profile:
  name: "John Doe"
  role: "Full-Stack Software Developer"
  experience:
    primary: "Python/Django, JavaScript/React"
    secondary: "Docker, PostgreSQL, AWS, REST APIs"

work_context:
  current_project: "ecommerce_platform"
  architecture: "Microservices with REST APIs"
  focus_areas:
    - "Backend API development"
    - "Database optimization"

preferences:
  code_style:
    - "Clean code principles"
    - "Minimal code duplication"
    - "Performance-conscious"
  
  tools_and_tech:
    preferred_packages:
      - "requests (for HTTP in Python)"
      - "pytest (for testing)"
      - "axios (for HTTP in JavaScript)"

context_awareness:
  recent_challenges:
    - "Optimizing database queries for large datasets"
    - "Implementing JWT authentication"

goals_and_interests:
  short_term:
    - "Master GraphQL APIs"
    - "Learn Kubernetes"
    """)
    
    print("\n" + "STEP 2: PersonalizationManager Processing".center(70, "─"))
    
    manager = PersonalizationManager('personalization_config_john_doe.yaml')
    
    print("\n⚙️  PersonalizationManager loaded config:")
    print("   ✓ Parsed YAML structure")
    print("   ✓ Validated all sections")
    print("   ✓ Built internal data structures")
    
    print("\n" + "STEP 3: Extracting User Profile".center(70, "─"))
    
    profile = manager.get_user_profile()
    print(f"\n👤 UserProfile Object:")
    print(f"   name: '{profile.name}'")
    print(f"   role: '{profile.role}'")
    print(f"   experience.primary: '{profile.experience['primary']}'")
    print(f"   education: '{profile.education}'")
    
    print("\n   🔗 Config Path: user_profile → name/role/experience")
    
    print("\n" + "STEP 4: Building System Prompt".center(70, "─"))
    
    prompt = manager.build_system_prompt()
    
    print("\n📋 System Prompt Generation:")
    print("   ✓ Inserted user profile")
    print("   ✓ Added work context")
    print("   ✓ Included preferences")
    print("   ✓ Listed response guidelines")
    
    print("\n📝 Generated Prompt (first 400 chars):")
    print("─" * 70)
    print(prompt[:400])
    print("...")
    print("─" * 70)
    
    print("\n   🔗 Config Sections Used:")
    print("      • user_profile → 'You are assisting John Doe'")
    print("      • work_context → 'Working on: ecommerce_platform'")
    print("      • preferences → 'Communication style, Code preferences'")
    print("      • response_guidelines → 'When coding/explaining...'")
    
    print("\n" + "STEP 5: Demonstrating Query Processing".center(70, "─"))
    
    demo_queries = [
        {
            "query": "Review my Python code",
            "triggers": ["code", "review", "Python"],
            "config_sections": {
                "user_profile.experience.primary": "Knows you use Python/Django",
                "preferences.code_style": "Applies clean code focus",
                "preferences.communication_style": "Direct and concise",
                "response_guidelines.when_coding": "Provide working examples"
            }
        },
        {
            "query": "What HTTP library should I use?",
            "triggers": ["library", "HTTP"],
            "config_sections": {
                "user_profile.experience.primary": "Python + JavaScript stack",
                "preferences.tools_and_tech.preferred_packages": "requests, axios",
                "work_context.architecture": "Microservices context"
            }
        },
        {
            "query": "Help me optimize database queries",
            "triggers": ["optimize", "database", "performance"],
            "config_sections": {
                "context_awareness.recent_challenges": "Recent DB optimization work",
                "work_context.focus_areas": "Database optimization focus",
                "preferences.code_style": "Performance-conscious",
                "user_profile.experience": "PostgreSQL experience"
            }
        },
        {
            "query": "Teach me GraphQL",
            "triggers": ["teach", "learn", "GraphQL"],
            "config_sections": {
                "goals_and_interests.short_term": "Master GraphQL APIs",
                "user_profile.experience.primary": "Django + React stack",
                "habits_and_patterns.learning_style": "Hands-on experimentation",
                "work_context.architecture": "Microservices fit"
            }
        }
    ]
    
    for i, demo in enumerate(demo_queries, 1):
        print(f"\n{'─'*70}")
        print(f"QUERY EXAMPLE {i}: \"{demo['query']}\"")
        print(f"{'─'*70}")
        
        print(f"\n🔍 Detected Keywords: {', '.join(demo['triggers'])}")
        
        print(f"\n📋 Config Sections Activated:")
        for section, influence in demo['config_sections'].items():
            print(f"   • {section}")
            print(f"     → {influence}")
        
        print(f"\n🎯 Personalization Impact:")
        if "review" in demo['query'].lower() or "code" in demo['query'].lower():
            print("   ✓ Code review preferences applied")
            print("   ✓ Language-specific focus (Python/Django)")
            print("   ✓ Style guidelines (clean code, performance)")
        
        if "library" in demo['query'].lower() or "package" in demo['query'].lower():
            print("   ✓ Preferred packages highlighted")
            print("   ✓ Stack-specific recommendations")
        
        if "optimize" in demo['query'].lower() or "performance" in demo['query'].lower():
            print("   ✓ Recent challenges considered")
            print("   ✓ Project-specific context applied")
            print("   ✓ Performance focus activated")
        
        if "learn" in demo['query'].lower() or "teach" in demo['query'].lower():
            print("   ✓ Learning goals recognized")
            print("   ✓ Learning style applied (hands-on)")
            print("   ✓ Stack-relevant examples")
    
    print("\n" + "="*70)


def show_config_to_response_mapping():
    """Show exact mapping from config to response elements"""
    
    print("\n" + "="*70)
    print("🗺️  CONFIG → RESPONSE MAPPING")
    print("="*70)
    
    mappings = [
        {
            "config_line": "user_profile.name: 'John Doe'",
            "system_prompt": "You are a personalized AI assistant for John Doe.",
            "response_impact": "Claude addresses you by name and remembers identity"
        },
        {
            "config_line": "experience.primary: 'Python/Django, JavaScript/React'",
            "system_prompt": "Primary expertise: Python/Django, JavaScript/React",
            "response_impact": "Code examples in Python/Django and JavaScript/React"
        },
        {
            "config_line": "current_project: 'ecommerce_platform'",
            "system_prompt": "Working on: ecommerce_platform",
            "response_impact": "Advice tailored to e-commerce domain and scale"
        },
        {
            "config_line": "architecture: 'Microservices with REST APIs'",
            "system_prompt": "Architecture: Microservices with REST APIs",
            "response_impact": "Suggests microservice-appropriate patterns"
        },
        {
            "config_line": "code_style: 'Clean code principles'",
            "system_prompt": "WHEN PROVIDING CODE: Follow clean code principles",
            "response_impact": "Reviews code for readability and maintainability"
        },
        {
            "config_line": "preferred_packages: 'requests, pytest, axios'",
            "system_prompt": "[Context enhancement when relevant]",
            "response_impact": "Recommends these packages first"
        },
        {
            "config_line": "recent_challenges: 'Optimizing database queries'",
            "system_prompt": "[Added to context awareness]",
            "response_impact": "Asks if performance issues are DB-related"
        },
        {
            "config_line": "short_term goals: 'Master GraphQL APIs'",
            "system_prompt": "[Included in user context]",
            "response_impact": "Excited to help with GraphQL, provides extra detail"
        },
        {
            "config_line": "communication_style: 'Direct and concise'",
            "system_prompt": "COMMUNICATION STYLE: Direct and concise",
            "response_impact": "Skips pleasantries, gets to technical point"
        },
        {
            "config_line": "learning_style: 'Hands-on experimentation'",
            "system_prompt": "[Learning preferences noted]",
            "response_impact": "Provides working code examples, not just theory"
        }
    ]
    
    for i, mapping in enumerate(mappings, 1):
        print(f"\n{i}. CONFIG LINE:")
        print(f"   📝 {mapping['config_line']}")
        print(f"\n   TRANSFORMS TO SYSTEM PROMPT:")
        print(f"   📋 {mapping['system_prompt']}")
        print(f"\n   IMPACTS RESPONSE:")
        print(f"   💬 {mapping['response_impact']}")
        print()
    
    print("="*70)


def demonstrate_with_comparison():
    """Show side-by-side comparison"""
    
    print("\n" + "="*70)
    print("⚖️  SIDE-BY-SIDE COMPARISON")
    print("="*70)
    
    scenarios = [
        {
            "query": "How do I handle errors in my code?",
            "without_config": """
Generic Response (No Config):
─────────────────────────────
Error handling best practices:
1. Use try-except blocks
2. Log errors appropriately
3. Return meaningful messages
4. Handle edge cases

Example:
try:
    result = some_function()
except Exception as e:
    print(f"Error: {e}")
""",
            "with_config": """
John Doe Response (With Config):
──────────────────────────────────
For your Django/React stack:

Backend (Python/Django):
```python
# Django REST Framework error handling
from rest_framework.views import exception_handler
from rest_framework.response import Response

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    
    if response is not None:
        # Add your ecommerce context
        response.data['project'] = 'ecommerce_platform'
    
    return response
```

Frontend (React):
```javascript
// Error boundary for your React components
class ErrorBoundary extends React.Component {
  // Handle errors in your microservices calls
}
```

Given your focus on clean code and comprehensive 
error handling, also implement:
- Structured logging (python-json-logger)
- Error tracking (Sentry for microservices)
- Graceful degradation for your e-commerce flow
""",
            "config_sections_used": [
                "✓ user_profile.experience → Python/Django + React examples",
                "✓ work_context.project → ecommerce_platform context",
                "✓ work_context.architecture → microservices patterns",
                "✓ preferences.code_style → comprehensive error handling",
                "✓ preferences.tools_and_tech → relevant package suggestions"
            ]
        },
        {
            "query": "What should I learn next?",
            "without_config": """
Generic Response (No Config):
─────────────────────────────
Popular technologies to learn:
- Cloud platforms (AWS, Azure, GCP)
- Container orchestration (Kubernetes, Docker Swarm)
- Frontend frameworks (React, Vue, Angular)
- Backend frameworks (Express, Django, Spring)
- Databases (PostgreSQL, MongoDB, Redis)

Choose based on your career goals.
""",
            "with_config": """
John Doe Response (With Config):
──────────────────────────────────
Perfect timing! I see you're aiming to master GraphQL
and Kubernetes - let me help you tackle these:

**GraphQL** (Aligns with your short-term goal):
Since you're working on ecommerce_platform with 
microservices, GraphQL is excellent for:
- Unified API gateway for your services
- Flexible queries for your React frontend
- Reducing over-fetching in product catalogs

Start with:
1. graphene-django for your Django services
2. Apollo Client for your React app
3. Hands-on: Build a product search API

**Kubernetes** (Your other goal):
Crucial for your microservices architecture:
- Deploy your ecommerce services
- Auto-scaling for traffic spikes
- Service mesh for inter-service communication

Recommended path:
1. Docker compose → Kubernetes (you know Docker)
2. Deploy one service first
3. Gradually migrate your microservices

Also consider: AWS EKS (since you use AWS) for 
managed Kubernetes in your production environment.
""",
            "config_sections_used": [
                "✓ goals_and_interests.short_term → GraphQL, Kubernetes",
                "✓ work_context.project → ecommerce use cases",
                "✓ work_context.architecture → microservices fit",
                "✓ user_profile.experience.secondary → Docker, AWS",
                "✓ habits_and_patterns.learning_style → hands-on approach"
            ]
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{'▬'*70}")
        print(f"SCENARIO {i}: \"{scenario['query']}\"")
        print(f"{'▬'*70}")
        
        print(scenario['without_config'])
        print(scenario['with_config'])
        
        print("\n📋 Config Sections Used:")
        for section in scenario['config_sections_used']:
            print(f"   {section}")
        print()
    
    print("="*70)
    print("KEY INSIGHT:")
    print("="*70)
    print("""
WITHOUT CONFIG: Generic advice that could apply to anyone
WITH CONFIG: Specific guidance tailored to:
  • Your tech stack (Python/Django, React)
  • Your project (ecommerce_platform)
  • Your architecture (microservices)
  • Your goals (GraphQL, Kubernetes)
  • Your learning style (hands-on)
  • Your context (recent challenges, focus areas)

The config makes the difference between:
❌ "Here are some options..."
✅ "For YOUR situation, do THIS..."
    """)
    print("="*70)


if __name__ == "__main__":
    print("\n" + "🔬 DETAILED CONFIG TRACING DEMO ".center(70, "="))
    
    # Trace complete flow
    trace_config_flow()
    
    # Show exact mappings
    show_config_to_response_mapping()
    
    # Show comparisons
    demonstrate_with_comparison()
    
    print("\n" + "="*70)
    print("🎓 SUMMARY")
    print("="*70)
    print("""
Every part of your config has a purpose:

1. user_profile → Tells Claude WHO you are
2. work_context → Tells Claude WHAT you're working on
3. preferences → Tells Claude HOW you like to work
4. goals_and_interests → Tells Claude WHERE you're heading
5. context_awareness → Tells Claude your CURRENT situation
6. response_guidelines → Tells Claude HOW to respond

All of this flows through:
  Config File → Manager → System Prompt → Agent → Claude API

Result: Claude doesn't just know programming.
        Claude knows YOUR programming.

That's the power of personalization! 🎯
    """)
    print("="*70)
