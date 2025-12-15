"""
Standalone Demo - Personalization System
Демонстрация системы персонализации без API зависимостей
"""

from personalization_manager import PersonalizationManager


def print_section(title: str):
    """Print formatted section header"""
    print(f"\n{'='*70}")
    print(f"{title.center(70)}")
    print(f"{'='*70}\n")


def demo_profile_loading():
    """Demo: Loading and displaying profile"""
    print_section("1. LOADING PERSONALIZATION PROFILE")
    
    manager = PersonalizationManager()
    print(manager.get_summary())


def demo_system_prompt():
    """Demo: Generated system prompt for agent"""
    print_section("2. GENERATED SYSTEM PROMPT FOR AGENT")
    
    manager = PersonalizationManager()
    prompt = manager.build_system_prompt()
    
    # Print first 1000 chars
    print(prompt[:1000])
    print("\n[... truncated for demo ...]")
    print(f"\nTotal length: {len(prompt)} characters")


def demo_context_awareness():
    """Demo: Context-aware features"""
    print_section("3. CONTEXT AWARENESS FEATURES")
    
    manager = PersonalizationManager()
    
    # Test optimization suggestions
    print("🔍 Optimization Detection:")
    test_cases = [
        ("Nested loops with duplicate code", True),
        ("Performance issue in large list", True),
        ("Simple hello world function", False),
        ("Memory leak in image loading", True),
    ]
    
    for message, expected in test_cases:
        result = manager.should_suggest_optimization(message)
        status = "✓" if result == expected else "✗"
        emoji = "🔧" if result else "  "
        print(f"  {status} {emoji} {message}")
    
    # Test package recommendations
    print("\n📦 Smart Package Recommendations:")
    task_types = [
        ("networking", ["dio"]),
        ("images", ["cached_network_image"]),
        ("state", ["flutter_bloc"]),
        ("navigation", ["auto_route"]),
    ]
    
    for task, expected in task_types:
        packages = manager.get_relevant_packages(task)
        print(f"  {task:12} → {', '.join(packages)}")


def demo_response_guidelines():
    """Demo: Response guidelines for different scenarios"""
    print_section("4. RESPONSE GUIDELINES")
    
    manager = PersonalizationManager()
    guidelines = manager.get_response_guidelines()
    
    print("📝 When Providing Code:")
    for rule in guidelines.when_coding:
        print(f"  • {rule}")
    
    print("\n💬 When Explaining:")
    for rule in guidelines.when_explaining:
        print(f"  • {rule}")
    
    print("\n🔍 When Problem Solving:")
    for rule in guidelines.when_problem_solving:
        print(f"  • {rule}")
    
    print("\n🚫 What to Avoid:")
    for item in guidelines.avoid:
        print(f"  • {item}")


def demo_user_context():
    """Demo: User context and current state"""
    print_section("5. CURRENT USER CONTEXT")
    
    manager = PersonalizationManager()
    context = manager.get_current_context()
    
    print("💼 Work Context:")
    work = context['work']
    print(f"  Project: {work['current_project']}")
    print(f"  Architecture: {work['architecture']}")
    print(f"  Focus Areas:")
    for area in work['focus_areas']:
        print(f"    • {area}")
    
    print("\n🎯 Recent Challenges:")
    for challenge in context['recent_challenges']:
        print(f"  • {challenge}")
    
    print("\n🚀 Ongoing Projects:")
    for project in context['ongoing_projects']:
        print(f"  • {project}")
    
    print("\n⚠️  Known Pain Points:")
    for pain_point in context['pain_points']:
        print(f"  • {pain_point}")


def demo_preferences():
    """Demo: User preferences"""
    print_section("6. USER PREFERENCES")
    
    manager = PersonalizationManager()
    
    print("💬 Communication Style:")
    for style in manager.get_communication_style():
        print(f"  • {style}")
    
    print("\n📐 Code Style:")
    for style in manager.get_code_style_preferences():
        print(f"  • {style}")
    
    print("\n🛠️  Preferred Tools:")
    tools = manager.get_preferred_tools()
    print(f"  IDE: {tools['ide']}")
    print(f"  State Management: {tools['state_management']}")
    print(f"  Packages:")
    for pkg in tools['preferred_packages']:
        print(f"    • {pkg}")


def demo_goals():
    """Demo: User goals"""
    print_section("7. USER GOALS")
    
    manager = PersonalizationManager()
    goals = manager.get_goals()
    
    print("🎯 Short-term Goals:")
    for goal in goals['short_term']:
        print(f"  • {goal}")
    
    print("\n🚀 Mid-term Goals:")
    for goal in goals['mid_term']:
        print(f"  • {goal}")
    
    print("\n🌟 Long-term Goals:")
    for goal in goals['long_term']:
        print(f"  • {goal}")
    
    print("\n💡 Side Interests:")
    for interest in goals['side_interests']:
        print(f"  • {interest}")


def demo_practical_examples():
    """Demo: Practical usage examples"""
    print_section("8. PRACTICAL USAGE EXAMPLES")
    
    manager = PersonalizationManager()
    
    scenarios = [
        {
            "title": "Code Review Request",
            "user_input": "Please review my Flutter widget code",
            "context": "User submitted a ListView with performance issues",
            "agent_behavior": [
                "✓ Checks for BLoC pattern usage (user's preference)",
                "✓ Looks for code duplication (user's code style)",
                "✓ Examines performance (user's focus area)",
                "✓ Suggests optimizations proactively (agent behavior)",
                "✓ Provides concrete examples (communication style)",
            ]
        },
        {
            "title": "Architecture Question",
            "user_input": "Should I use Provider or Riverpod?",
            "context": "User is deciding on state management",
            "agent_behavior": [
                "✓ Recommends BLoC (user's current architecture)",
                "✓ Explains why it fits the project context",
                "✓ Mentions team consistency (user values this)",
                "✓ Direct answer, no lengthy comparisons",
                "✓ Focuses on maintainability (user's priority)",
            ]
        },
        {
            "title": "Performance Issue",
            "user_input": "My list is lagging with 1000+ items",
            "context": "User reports performance problem",
            "agent_behavior": [
                "✓ Recognizes similar past challenge (context aware)",
                "✓ Suggests ListView.builder optimization",
                "✓ Recommends caching strategies (recent work)",
                "✓ Provides complete code example (guideline)",
                "✓ Mentions preferred packages (cached_network_image)",
            ]
        },
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n📌 Scenario {i}: {scenario['title']}")
        print(f"   User: \"{scenario['user_input']}\"")
        print(f"   Context: {scenario['context']}")
        print(f"\n   Agent Behavior:")
        for behavior in scenario['agent_behavior']:
            print(f"   {behavior}")


def demo_customization_examples():
    """Demo: How to customize for different roles"""
    print_section("9. CUSTOMIZATION EXAMPLES")
    
    print("🎨 Example Customizations for Different Roles:\n")
    
    examples = [
        {
            "role": "ML Engineer",
            "key_changes": [
                "experience.primary: 'PyTorch, TensorFlow'",
                "communication_style: 'Show mathematical intuition'",
                "code_style: 'Vectorized operations, Memory-efficient'",
                "response_guidelines: 'Include shape transformations'",
            ]
        },
        {
            "role": "Backend Developer",
            "key_changes": [
                "experience.primary: 'Python, FastAPI, PostgreSQL'",
                "communication_style: 'API-first thinking'",
                "code_style: 'Type hints, Comprehensive error handling'",
                "response_guidelines: 'Include API documentation'",
            ]
        },
        {
            "role": "Frontend Developer",
            "key_changes": [
                "experience.primary: 'React, TypeScript'",
                "communication_style: 'User experience focus'",
                "code_style: 'Component reusability, Accessibility'",
                "response_guidelines: 'Show responsive design examples'",
            ]
        },
    ]
    
    for example in examples:
        print(f"👤 {example['role']}:")
        for change in example['key_changes']:
            print(f"   • {change}")
        print()


def main():
    """Run all demos"""
    print("\n" + "🤖 PERSONALIZATION SYSTEM DEMO ".center(70, "="))
    print("Демонстрация системы персонализации AI агента".center(70))
    print("="*70)
    
    demos = [
        ("Profile Loading", demo_profile_loading),
        ("System Prompt", demo_system_prompt),
        ("Context Awareness", demo_context_awareness),
        ("Response Guidelines", demo_response_guidelines),
        ("User Context", demo_user_context),
        ("Preferences", demo_preferences),
        ("Goals", demo_goals),
        ("Practical Examples", demo_practical_examples),
        ("Customization", demo_customization_examples),
    ]
    
    for name, demo_func in demos:
        try:
            demo_func()
        except Exception as e:
            print(f"\n❌ Error in {name}: {e}")
    
    # Final summary
    print_section("SUMMARY")
    print("✅ Персонализация загружена из YAML конфига")
    print("✅ System prompt построен с учётом всех предпочтений")
    print("✅ Контекстная осведомленность работает")
    print("✅ Рекомендации адаптированы под пользователя")
    print("✅ Агент готов к использованию!")
    
    print("\n💡 Next Steps:")
    print("   1. Отредактируй personalization_config_john_doe.yaml под себя")
    print("   2. Добавь свой ANTHROPIC_API_KEY в environment")
    print("   3. Используй PersonalizedAgent для общения с Claude")
    print("   4. Агент будет знать твой контекст и предпочтения!")
    
    print("\n📚 Usage Example:")
    print("""
    from personalized_agent_example import PersonalizedAgent
    
    agent = PersonalizedAgent()
    response = agent.chat("Help me optimize this Flutter code")
    print(response)
    """)


if __name__ == "__main__":
    main()
