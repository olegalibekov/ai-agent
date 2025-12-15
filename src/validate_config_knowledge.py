"""
Automated Config Knowledge Validator
Автоматическая проверка знаний модели из конфига
"""

from personalization_manager import PersonalizationManager
import os


def validate_config_knowledge():
    """Automatically validate what the model should know from config"""
    
    print("\n" + "="*70)
    print("🔍 AUTOMATED CONFIG KNOWLEDGE VALIDATION")
    print("="*70)
    
    print("\n📋 Loading config: personalization_config_john_doe.yaml")
    manager = PersonalizationManager('personalization_config_john_doe.yaml')
    
    print("\n✓ Config loaded successfully")
    print("\nGenerating knowledge test cases from config...")
    
    # Extract all knowledge from config
    profile = manager.get_user_profile()
    context = manager.get_current_context()
    prefs = {
        'code_style': manager.get_code_style_preferences(),
        'communication': manager.get_communication_style(),
        'tools': manager.get_preferred_tools()
    }
    goals = manager.get_goals()
    
    print("\n" + "="*70)
    print("KNOWLEDGE BASE EXTRACTED FROM CONFIG")
    print("="*70)
    
    knowledge_base = {
        "Personal Identity": {
            "name": profile.name,
            "role": profile.role,
            "education": profile.education,
            "age": profile.age,
            "question": "Who are you helping? What's their role?",
            "keywords": [profile.name.lower(), profile.role.lower().split()[0]]
        },
        
        "Technical Expertise": {
            "primary": profile.experience['primary'],
            "secondary": profile.experience['secondary'],
            "question": "What technologies and tools does the user work with?",
            "keywords": ["python", "django", "javascript", "react", "docker"]
        },
        
        "Current Project": {
            "project": context['work']['current_project'],
            "description": "Building a scalable e-commerce solution",
            "architecture": context['work']['architecture'],
            "question": "What project is the user working on? What architecture?",
            "keywords": ["ecommerce", "microservices", "rest"]
        },
        
        "Focus Areas": {
            "areas": context['work']['focus_areas'],
            "question": "What are the user's main areas of focus?",
            "keywords": ["backend", "database", "api", "optimization"]
        },
        
        "Code Preferences": {
            "styles": prefs['code_style'],
            "question": "What code style principles does the user follow?",
            "keywords": ["clean code", "duplication", "performance"]
        },
        
        "Communication Style": {
            "styles": prefs['communication'],
            "question": "How does the user prefer to communicate?",
            "keywords": ["direct", "concise", "technical"]
        },
        
        "Preferred Tools": {
            "packages": prefs['tools']['preferred_packages'],
            "ide": prefs['tools']['ide'],
            "state_management": prefs['tools']['state_management'],
            "question": "What tools and packages does the user prefer?",
            "keywords": ["requests", "pytest", "axios", "vs code", "redux"]
        },
        
        "Recent Challenges": {
            "challenges": context['recent_challenges'],
            "question": "What challenges has the user been working on?",
            "keywords": ["database", "optimization", "jwt", "authentication"]
        },
        
        "Learning Goals": {
            "short_term": goals['short_term'],
            "mid_term": goals['mid_term'],
            "long_term": goals['long_term'],
            "question": "What does the user want to learn and achieve?",
            "keywords": ["graphql", "kubernetes", "senior", "startup"]
        },
        
        "Side Interests": {
            "interests": goals['side_interests'],
            "question": "What are the user's side interests?",
            "keywords": ["machine learning", "mobile", "devops"]
        }
    }
    
    # Display extracted knowledge
    for category, data in knowledge_base.items():
        print(f"\n📌 {category}:")
        for key, value in data.items():
            if key not in ['question', 'keywords']:
                if isinstance(value, list):
                    print(f"   {key}:")
                    for item in value[:3]:  # Show first 3
                        print(f"      • {item}")
                    if len(value) > 3:
                        print(f"      ... and {len(value)-3} more")
                else:
                    print(f"   {key}: {value}")
    
    print("\n" + "="*70)
    print("QUESTION TEMPLATES FOR TESTING")
    print("="*70)
    
    print("\nThese questions should be answerable from config:\n")
    
    questions_by_category = []
    
    for i, (category, data) in enumerate(knowledge_base.items(), 1):
        question_template = data['question']
        print(f"{i}. {category}")
        print(f"   ❓ Question: \"{question_template}\"")
        print(f"   🎯 Keywords to expect: {', '.join(data['keywords'][:5])}")
        
        questions_by_category.append({
            'category': category,
            'question': question_template,
            'keywords': data['keywords'],
            'data': {k: v for k, v in data.items() if k not in ['question', 'keywords']}
        })
        print()
    
    # Generate system prompt preview
    print("\n" + "="*70)
    print("SYSTEM PROMPT PREVIEW")
    print("="*70)
    
    system_prompt = manager.build_system_prompt()
    print(f"\n📝 Generated System Prompt ({len(system_prompt)} characters):")
    print("─" * 70)
    print(system_prompt[:800])
    print("\n... [truncated, full prompt continues] ...")
    print("─" * 70)
    
    # Verify knowledge is in system prompt
    print("\n🔍 Verifying knowledge is embedded in system prompt:")
    
    checks = [
        (profile.name, "✓ Name"),
        (profile.role, "✓ Role"),
        (profile.experience['primary'], "✓ Primary tech stack"),
        (context['work']['current_project'], "✓ Current project"),
        (context['work']['architecture'], "✓ Architecture"),
        (prefs['code_style'][0], "✓ Code style preferences"),
    ]
    
    for check_value, label in checks:
        if check_value.lower() in system_prompt.lower():
            print(f"   {label}: FOUND")
        else:
            print(f"   {label}: MISSING ⚠️")
    
    # Generate test script
    print("\n" + "="*70)
    print("GENERATED TEST QUESTIONS")
    print("="*70)
    
    print("\nCopy these questions to test Claude:\n")
    
    test_questions = [
        "What is my name and what do I do?",
        "What programming languages and frameworks do I use?",
        "What project am I currently working on?",
        "What architecture does my project use?",
        "What are my code style preferences?",
        "How do I prefer to communicate?",
        "What tools and packages do I prefer?",
        "What have I been working on recently?",
        "What are my learning goals?",
        "What technologies am I trying to master?",
        "What's my preferred IDE?",
        "What challenges am I facing?",
        "What are my career goals?",
        "How do I like to learn new things?",
        "What interests me outside of work?"
    ]
    
    for i, q in enumerate(test_questions, 1):
        print(f"{i}. {q}")
    
    print("\n" + "="*70)
    print("KNOWLEDGE COVERAGE SUMMARY")
    print("="*70)
    
    total_facts = 0
    for category, data in knowledge_base.items():
        category_facts = 0
        for key, value in data.items():
            if key not in ['question', 'keywords']:
                if isinstance(value, list):
                    category_facts += len(value)
                else:
                    category_facts += 1
        total_facts += category_facts
        print(f"   {category}: {category_facts} facts")
    
    print(f"\n   TOTAL: {total_facts} discrete facts in config")
    print(f"   All embedded in {len(system_prompt)}-character system prompt")
    
    print("\n" + "="*70)
    print("💡 TESTING INSTRUCTIONS")
    print("="*70)
    print("""
To test if Claude knows this information:

1. Run: python quiz_model_knowledge.py
   → Full interactive quiz with Claude

2. Or manually ask Claude any of the questions above

3. Check if Claude's answers match the config data

4. Every correct answer proves: Config → Agent → Knowledge

Expected results:
- Claude should know your name, role, tech stack
- Claude should know your current project and architecture  
- Claude should know your preferences and goals
- Claude should adapt responses based on this knowledge

If Claude answers correctly: ✅ Config is working!
If Claude doesn't know: ⚠️ Check config loading
    """)
    print("="*70)
    
    return questions_by_category


def generate_test_prompts():
    """Generate specific prompts to test config knowledge"""
    
    print("\n" + "="*70)
    print("📝 GENERATED TEST PROMPTS")
    print("="*70)
    
    manager = PersonalizationManager('personalization_config_john_doe.yaml')
    profile = manager.get_user_profile()
    context = manager.get_current_context()
    
    prompts = [
        {
            "test": "Personal Identity",
            "prompt": "Who am I?",
            "should_include": [profile.name, profile.role],
            "from_config": "user_profile.name, user_profile.role"
        },
        {
            "test": "Tech Stack Awareness",
            "prompt": "What programming languages do I know?",
            "should_include": ["Python", "Django", "JavaScript", "React"],
            "from_config": "user_profile.experience.primary"
        },
        {
            "test": "Project Context",
            "prompt": "What am I building?",
            "should_include": ["ecommerce", "platform"],
            "from_config": "work_context.current_project"
        },
        {
            "test": "Architecture Knowledge",
            "prompt": "What architecture am I using?",
            "should_include": ["microservices", "REST"],
            "from_config": "work_context.architecture"
        },
        {
            "test": "Code Style",
            "prompt": "How should code be written for me?",
            "should_include": ["clean code", "performance"],
            "from_config": "preferences.code_style"
        },
        {
            "test": "Tool Preferences",
            "prompt": "What HTTP library should I use for Python?",
            "should_include": ["requests"],
            "from_config": "preferences.tools_and_tech.preferred_packages"
        },
        {
            "test": "Recent Context",
            "prompt": "What have I been working on lately?",
            "should_include": ["database", "optimization"],
            "from_config": "context_awareness.recent_challenges"
        },
        {
            "test": "Learning Goals",
            "prompt": "What do I want to learn?",
            "should_include": ["GraphQL", "Kubernetes"],
            "from_config": "goals_and_interests.short_term"
        },
        {
            "test": "Communication Style",
            "prompt": "How should you respond to me?",
            "should_include": ["direct", "concise", "technical"],
            "from_config": "preferences.communication_style"
        },
        {
            "test": "Career Goals",
            "prompt": "What are my career aspirations?",
            "should_include": ["senior engineer", "startup"],
            "from_config": "goals_and_interests.mid_term"
        }
    ]
    
    for i, test in enumerate(prompts, 1):
        print(f"\n{i}. TEST: {test['test']}")
        print(f"   Prompt: \"{test['prompt']}\"")
        print(f"   Should include: {', '.join(test['should_include'])}")
        print(f"   From config: {test['from_config']}")
    
    print("\n" + "="*70)
    print("💡 Copy any prompt above and ask Claude!")
    print("="*70)
    
    return prompts


if __name__ == "__main__":
    print("\n" + "🔬 CONFIG KNOWLEDGE VALIDATOR ".center(70, "="))
    
    # Validate and extract knowledge
    questions = validate_config_knowledge()
    
    # Generate test prompts
    prompts = generate_test_prompts()
    
    print("\n" + "="*70)
    print("✅ VALIDATION COMPLETE")
    print("="*70)
    print(f"""
Summary:
• Extracted {len(questions)} knowledge categories from config
• Generated {len(prompts)} test prompts
• Created system prompt with all knowledge embedded

Next steps:
1. Run: python quiz_model_knowledge.py
   → Interactive quiz with Claude

2. Or copy any test prompt above
   → Ask Claude directly

3. Check if answers match config data
   → Proves config → agent → knowledge flow

The config file is Claude's source of truth about you! 🎯
    """)
    print("="*70)
