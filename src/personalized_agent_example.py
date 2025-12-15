"""
Example: Personalized AI Agent Integration
Пример интеграции персонализированного AI агента
"""

from anthropic import Anthropic
from personalization_manager import PersonalizationManager
from typing import List, Dict, Any
import os

from dotenv import load_dotenv

load_dotenv()

class PersonalizedAgent:
    """AI Agent with personalization capabilities"""
    
    def __init__(self, api_key: str = None, config_path: str = "personalization_config_john_doe.yaml"):
        self.client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        self.personalization = PersonalizationManager(config_path)
        self.conversation_history: List[Dict[str, str]] = []
        
        # Build personalized system prompt
        self.system_prompt = self.personalization.build_system_prompt()
    
    def chat(self, user_message: str, model: str = "claude-sonnet-4-20250514") -> str:
        """Send a message and get personalized response"""
        
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Check if we should add context-specific instructions
        enhanced_message = self._enhance_message(user_message)
        
        # Make API call
        response = self.client.messages.create(
            model=model,
            max_tokens=4000,
            system=self.system_prompt,
            messages=[{
                "role": msg["role"],
                "content": msg["content"] if msg["role"] == "user" and msg["content"] != user_message 
                         else (enhanced_message if msg["content"] == user_message else msg["content"])
            } for msg in self.conversation_history]
        )
        
        assistant_message = response.content[0].text
        
        # Add assistant response to history
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_message
        })
        
        # Update runtime context
        self._update_runtime_context(user_message, assistant_message)
        
        return assistant_message
    
    def _enhance_message(self, message: str) -> str:
        """Enhance message with context-specific instructions"""
        enhancements = []
        
        # Check for code review request
        if any(keyword in message.lower() for keyword in ['review', 'check', 'look at']):
            guidelines = self.personalization.get_response_guidelines()
            code_prefs = self.personalization.get_code_style_preferences()
            enhancements.append(f"\n\nCode review focus: {', '.join(code_prefs[:3])}")
        
        # Check for optimization opportunity
        if self.personalization.should_suggest_optimization(message):
            enhancements.append("\n\n[Note: Feel free to suggest optimizations if you spot issues]")
        
        # Check for package recommendations needed
        if 'package' in message.lower() or 'library' in message.lower():
            tools = self.personalization.get_preferred_tools()
            preferred = tools.get('preferred_packages', [])
            enhancements.append(f"\n\n[Preferred packages: {', '.join(preferred)}]")
        
        return message + ''.join(enhancements)
    
    def _update_runtime_context(self, user_msg: str, assistant_msg: str) -> None:
        """Update runtime context based on conversation"""
        # Track topics discussed
        topics = []
        
        if 'bloc' in user_msg.lower() or 'bloc' in assistant_msg.lower():
            topics.append('BLoC pattern')
        if 'scroll' in user_msg.lower():
            topics.append('Scrolling behavior')
        if 'performance' in user_msg.lower() or 'optimize' in user_msg.lower():
            topics.append('Performance optimization')
        
        if topics:
            self.personalization.update_context('recent_topics', topics)
    
    def get_profile_summary(self) -> str:
        """Get personalization profile summary"""
        return self.personalization.get_summary()
    
    def reset_conversation(self) -> None:
        """Reset conversation history"""
        self.conversation_history = []
    
    def suggest_next_steps(self, current_task: str) -> str:
        """Suggest next steps based on user's goals and context"""
        goals = self.personalization.get_goals()
        context = self.personalization.get_current_context()
        
        prompt = f"""Given the user's current task: "{current_task}"
And their goals:
- Short term: {', '.join(goals['short_term'])}
- Mid term: {', '.join(goals['mid_term'])}

Suggest 2-3 concrete next steps that align with their goals and current context."""
        
        return self.chat(prompt)


def demo_personalized_interaction():
    """Demonstrate personalized agent interaction"""
    
    print("="*70)
    print("PERSONALIZED AI AGENT DEMO")
    print("="*70)
    
    # Initialize agent
    agent = PersonalizedAgent()
    
    # Show profile
    print("\n" + agent.get_profile_summary())
    print("\n" + "="*70)
    
    # Example interactions
    examples = [
        {
            "scenario": "Flutter Code Review",
            "message": "Review this code:\n\n```dart\nclass UserList extends StatelessWidget {\n  @override\n  Widget build(BuildContext context) {\n    return ListView.builder(\n      itemCount: users.length,\n      itemBuilder: (context, index) {\n        final user = users[index];\n        return ListTile(title: Text(user.name));\n      },\n    );\n  }\n}\n```"
        },
        {
            "scenario": "Architecture Question",
            "message": "Should I use BLoC or Provider for state management in a new feature?"
        },
        {
            "scenario": "Performance Issue",
            "message": "My list is lagging when scrolling. It has 1000+ items with images."
        }
    ]
    
    for example in examples:
        print(f"\n{'─'*70}")
        print(f"SCENARIO: {example['scenario']}")
        print(f"{'─'*70}")
        print(f"\n📝 User: {example['message'][:100]}...")
        
        # In real usage, would call agent.chat() here
        # response = agent.chat(example['message'])
        # print(f"\n🤖 Agent: {response}\n")
        
        print(f"\n[Agent would respond with personalized, technical answer]")
        print(f"[Following guidelines: direct, code-focused, BLoC-aware]")
    
    print("\n" + "="*70)
    print("Demo complete!")


def demo_context_awareness():
    """Demonstrate context awareness features"""
    
    manager = PersonalizationManager()
    
    print("\n" + "="*70)
    print("CONTEXT AWARENESS DEMO")
    print("="*70)
    
    # Test optimization suggestions
    test_cases = [
        "Here's my code with nested for loops",
        "I have duplicate code in three places",
        "Simple hello world function",
        "Performance issue with large dataset"
    ]
    
    print("\nOptimization Suggestion Tests:")
    for case in test_cases:
        should_suggest = manager.should_suggest_optimization(case)
        status = "✓ SUGGEST" if should_suggest else "○ SKIP"
        print(f"{status}: {case}")
    
    # Test package recommendations
    print("\n\nPackage Recommendations:")
    task_types = ['networking', 'images', 'state', 'unknown']
    for task in task_types:
        packages = manager.get_relevant_packages(task)
        print(f"  {task}: {', '.join(packages)}")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    # Run demos
    demo_personalized_interaction()
    demo_context_awareness()
    
    print("\n\n💡 USAGE EXAMPLES:")
    print("""
    # Initialize personalized agent
    agent = PersonalizedAgent()
    
    # Chat with context awareness
    response = agent.chat("Help me optimize this Flutter code")
    
    # Get profile summary
    print(agent.get_profile_summary())
    
    # Get personalized suggestions
    suggestions = agent.suggest_next_steps("Building image gallery")
    
    # Reset conversation if needed
    agent.reset_conversation()
    """)
