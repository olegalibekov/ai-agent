"""
Personalized AI Agent with Claude API Integration
Персонализированный AI агент с интеграцией Claude API
"""

from anthropic import Anthropic
from personalization_manager import PersonalizationManager
from typing import List, Dict, Any, Optional
import os

from dotenv import load_dotenv

load_dotenv()

class PersonalizedClaudeAgent:
    """
    AI Agent with personalization capabilities using Claude API
    
    Features:
    - Personalized system prompts
    - Context-aware message enhancement
    - Conversation history management
    - Runtime context tracking
    """
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        config_path: str = "personalization_config_john_doe.yaml",
        model: str = "claude-sonnet-4-20250514"
    ):
        """
        Initialize the personalized Claude agent
        
        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            config_path: Path to personalization config file
            model: Claude model to use
        """
        self.client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        self.personalization = PersonalizationManager(config_path)
        self.conversation_history: List[Dict[str, str]] = []
        self.model = model
        
        # Build personalized system prompt
        self.system_prompt = self.personalization.build_system_prompt()
        
        print(f"✓ Initialized PersonalizedClaudeAgent")
        print(f"  Model: {self.model}")
        print(f"  User: {self.personalization.get_user_profile().name}")
    
    def chat(
        self, 
        user_message: str, 
        max_tokens: int = 4000,
        temperature: float = 1.0,
        stream: bool = False
    ) -> str:
        """
        Send a message and get personalized response
        
        Args:
            user_message: User's message
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-1)
            stream: Whether to stream the response
            
        Returns:
            Assistant's response text
        """
        
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Check if we should add context-specific instructions
        enhanced_message = self._enhance_message(user_message)
        
        # Prepare messages for API
        messages = []
        for msg in self.conversation_history:
            if msg["role"] == "user" and msg["content"] == user_message:
                messages.append({
                    "role": "user",
                    "content": enhanced_message
                })
            else:
                messages.append(msg)
        
        # Make API call
        if stream:
            return self._chat_stream(messages, max_tokens, temperature)
        else:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=self.system_prompt,
                messages=messages
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
    
    def _chat_stream(
        self, 
        messages: List[Dict[str, str]], 
        max_tokens: int, 
        temperature: float
    ) -> str:
        """Stream response from Claude API"""
        full_response = ""
        
        with self.client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=self.system_prompt,
            messages=messages
        ) as stream:
            for text in stream.text_stream:
                print(text, end="", flush=True)
                full_response += text
        
        print()  # New line after streaming
        
        # Add to history
        self.conversation_history.append({
            "role": "assistant",
            "content": full_response
        })
        
        return full_response
    
    def _enhance_message(self, message: str) -> str:
        """Enhance message with context-specific instructions"""
        enhancements = []
        
        # Check for code review request
        if any(keyword in message.lower() for keyword in ['review', 'check', 'look at', 'analyze']):
            guidelines = self.personalization.get_response_guidelines()
            code_prefs = self.personalization.get_code_style_preferences()
            enhancements.append(f"\n\n[Code review focus: {', '.join(code_prefs[:3])}]")
        
        # Check for optimization opportunity
        if self.personalization.should_suggest_optimization(message):
            enhancements.append("\n\n[Note: Feel free to suggest optimizations if you spot issues]")
        
        # Check for package recommendations needed
        if 'package' in message.lower() or 'library' in message.lower():
            tools = self.personalization.get_preferred_tools()
            preferred = tools.get('preferred_packages', [])
            if preferred:
                enhancements.append(f"\n\n[Preferred packages: {', '.join(preferred[:3])}]")
        
        return message + ''.join(enhancements)
    
    def _update_runtime_context(self, user_msg: str, assistant_msg: str) -> None:
        """Update runtime context based on conversation"""
        topics = []
        
        # Track topics discussed
        keywords = {
            'api': 'API development',
            'database': 'Database design',
            'performance': 'Performance optimization',
            'test': 'Testing',
            'deploy': 'Deployment',
            'refactor': 'Code refactoring',
            'bug': 'Bug fixing',
            'architecture': 'System architecture'
        }
        
        for keyword, topic in keywords.items():
            if keyword in user_msg.lower() or keyword in assistant_msg.lower():
                topics.append(topic)
        
        if topics:
            self.personalization.update_context('recent_topics', topics)
    
    def get_profile_summary(self) -> str:
        """Get personalization profile summary"""
        return self.personalization.get_summary()
    
    def reset_conversation(self) -> None:
        """Reset conversation history"""
        self.conversation_history = []
        print("✓ Conversation history reset")
    
    def suggest_next_steps(self, current_task: str) -> str:
        """Suggest next steps based on user's goals and context"""
        goals = self.personalization.get_goals()
        context = self.personalization.get_current_context()
        
        prompt = f"""Given the user's current task: "{current_task}"

And their goals:
- Short term: {', '.join(goals['short_term'])}
- Mid term: {', '.join(goals['mid_term'])}

Current focus areas: {', '.join(context['work']['focus_areas'])}

Suggest 2-3 concrete next steps that align with their goals and context."""
        
        return self.chat(prompt)
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get summary of current conversation"""
        return {
            "message_count": len(self.conversation_history),
            "user_messages": len([m for m in self.conversation_history if m["role"] == "user"]),
            "assistant_messages": len([m for m in self.conversation_history if m["role"] == "assistant"]),
            "total_chars": sum(len(m["content"]) for m in self.conversation_history)
        }
    
    def export_conversation(self, filepath: str) -> None:
        """Export conversation to file"""
        import json
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                "model": self.model,
                "user": self.personalization.get_user_profile().name,
                "conversation": self.conversation_history
            }, f, indent=2, ensure_ascii=False)
        print(f"✓ Conversation exported to {filepath}")


def demo_basic_usage():
    """Demo: Basic usage of PersonalizedClaudeAgent"""
    print("\n" + "="*70)
    print("DEMO: Basic Claude API Usage")
    print("="*70)
    
    # Check if API key is available
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\n⚠️  ANTHROPIC_API_KEY not found in environment")
        print("Set it with: export ANTHROPIC_API_KEY='your-key-here'")
        print("\nSkipping live API demo...\n")
        return
    
    try:
        # Initialize agent
        agent = PersonalizedClaudeAgent()
        
        # Show profile
        print("\n" + agent.get_profile_summary())
        
        # Example conversation
        print("\n" + "-"*70)
        print("Example Conversation:")
        print("-"*70)
        
        # First message
        print("\n👤 User: Explain recursion in simple terms")
        response = agent.chat("Explain recursion in simple terms")
        print(f"\n🤖 Claude: {response[:200]}...")
        
        # Follow-up
        print("\n👤 User: Give me a code example")
        response = agent.chat("Give me a code example")
        print(f"\n🤖 Claude: {response[:200]}...")
        
        # Conversation summary
        print("\n" + "-"*70)
        summary = agent.get_conversation_summary()
        print(f"Conversation Summary: {summary}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")


def demo_streaming():
    """Demo: Streaming responses"""
    print("\n" + "="*70)
    print("DEMO: Streaming Responses")
    print("="*70)
    
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\n⚠️  ANTHROPIC_API_KEY not found")
        return
    
    try:
        agent = PersonalizedClaudeAgent()
        
        print("\n👤 User: Write a short poem about coding")
        print("🤖 Claude: ", end="")
        agent.chat("Write a short poem about coding", stream=True)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")


def demo_advanced_features():
    """Demo: Advanced features"""
    print("\n" + "="*70)
    print("DEMO: Advanced Features")
    print("="*70)
    
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\n⚠️  ANTHROPIC_API_KEY not found")
        return
    
    try:
        agent = PersonalizedClaudeAgent()
        
        # Test context enhancement
        print("\n1. Context-Aware Code Review:")
        print("👤 User: Review this Python function")
        response = agent.chat("Review this simple Python function: def add(a, b): return a + b")
        print(f"🤖 Claude: {response[:150]}...")
        
        # Test package recommendations
        print("\n2. Smart Package Suggestions:")
        print("👤 User: What package should I use for HTTP requests?")
        response = agent.chat("What package should I use for HTTP requests?")
        print(f"🤖 Claude: {response[:150]}...")
        
        # Export conversation
        print("\n3. Export Conversation:")
        agent.export_conversation("conversation_export.json")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    print("\n" + "🤖 PERSONALIZED CLAUDE AGENT DEMO ".center(70, "="))
    
    # Run demos
    demo_basic_usage()
    demo_streaming()
    demo_advanced_features()
    
    print("\n" + "="*70)
    print("💡 Usage Examples:")
    print("""
    # Basic usage
    agent = PersonalizedClaudeAgent()
    response = agent.chat("Your question here")
    
    # Streaming
    response = agent.chat("Your question", stream=True)
    
    # Different model
    agent = PersonalizedClaudeAgent(model="claude-opus-4-20250514")
    
    # Adjust temperature
    response = agent.chat("Be creative!", temperature=1.5)
    
    # Get suggestions
    suggestions = agent.suggest_next_steps("Building a REST API")
    
    # Export conversation
    agent.export_conversation("my_chat.json")
    """)
    print("="*70)
