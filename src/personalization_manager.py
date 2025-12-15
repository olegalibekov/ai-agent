"""
Personalization Manager for AI Agent
Менеджер персонализации для AI агента
"""

import yaml
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class UserProfile:
    """User profile data"""
    name: str
    role: str
    experience: Dict[str, str]
    education: str
    age: int
    location: str


@dataclass
class ResponseGuidelines:
    """Guidelines for agent responses"""
    when_coding: List[str]
    when_explaining: List[str]
    when_problem_solving: List[str]
    avoid: List[str]


class PersonalizationManager:
    """Manages user personalization and context for the agent"""
    
    def __init__(self, config_path: str = "personalization_config_john_doe.yaml"):
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.load_config()
    
    def load_config(self) -> None:
        """Load personalization config from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
    
    def get_user_profile(self) -> UserProfile:
        """Get user profile information"""
        profile = self.config['user_profile']
        return UserProfile(
            name=profile['name'],
            role=profile['role'],
            experience=profile['experience'],
            education=profile['education'],
            age=profile['age'],
            location=profile['location']
        )
    
    def get_communication_style(self) -> List[str]:
        """Get preferred communication style"""
        return self.config['preferences']['communication_style']
    
    def get_code_style_preferences(self) -> List[str]:
        """Get code style preferences"""
        return self.config['preferences']['code_style']
    
    def get_preferred_tools(self) -> Dict[str, Any]:
        """Get preferred tools and technologies"""
        return self.config['preferences']['tools_and_tech']
    
    def get_response_guidelines(self) -> ResponseGuidelines:
        """Get response guidelines for the agent"""
        guidelines = self.config['response_guidelines']
        return ResponseGuidelines(
            when_coding=guidelines['when_coding'],
            when_explaining=guidelines['when_explaining'],
            when_problem_solving=guidelines['when_problem_solving'],
            avoid=guidelines['avoid']
        )
    
    def get_current_context(self) -> Dict[str, Any]:
        """Get current work context and recent challenges"""
        return {
            'work': self.config['work_context'],
            'recent_challenges': self.config['context_awareness']['recent_challenges'],
            'ongoing_projects': self.config['context_awareness']['ongoing_projects'],
            'pain_points': self.config['context_awareness']['known_pain_points']
        }
    
    def get_goals(self) -> Dict[str, List[str]]:
        """Get user's short/mid/long term goals"""
        return self.config['goals_and_interests']
    
    def build_system_prompt(self) -> str:
        """Build a personalized system prompt for the agent"""
        profile = self.get_user_profile()
        comm_style = self.get_communication_style()
        code_style = self.get_code_style_preferences()
        guidelines = self.get_response_guidelines()
        context = self.get_current_context()
        
        prompt = f"""You are a personalized AI assistant for {profile.name}.

USER CONTEXT:
- Role: {profile.role}
- Primary expertise: {profile.experience['primary']}
- Secondary skills: {profile.experience['secondary']}
- Education: {profile.education}

CURRENT PROJECT:
- Working on: {context['work']['current_project']}
- Architecture: {context['work']['architecture']}
- Focus areas: {', '.join(context['work']['focus_areas'])}

COMMUNICATION STYLE (adapt to this):
{chr(10).join(f"- {style}" for style in comm_style)}

CODE PREFERENCES:
{chr(10).join(f"- {pref}" for pref in code_style)}

WHEN PROVIDING CODE:
{chr(10).join(f"- {rule}" for rule in guidelines.when_coding)}

WHEN EXPLAINING:
{chr(10).join(f"- {rule}" for rule in guidelines.when_explaining)}

WHEN PROBLEM SOLVING:
{chr(10).join(f"- {rule}" for rule in guidelines.when_problem_solving)}

AVOID:
{chr(10).join(f"- {item}" for item in guidelines.avoid)}

KNOWN CHALLENGES (be aware of these):
{chr(10).join(f"- {challenge}" for challenge in context['recent_challenges'])}

Remember: Be direct, technical, and practical. Focus on clean, maintainable code.
Prefer showing over telling. Consider performance and architecture implications.
"""
        return prompt
    
    def should_suggest_optimization(self, code_context: str) -> bool:
        """Determine if agent should proactively suggest optimizations"""
        agent_behavior = self.config['agent_behavior']['proactivity']
        
        # Check for common optimization triggers
        triggers = ['duplicate', 'performance', 'memory', 'loop', 'nested']
        return any(trigger in code_context.lower() for trigger in triggers)
    
    def get_relevant_packages(self, task_type: str) -> List[str]:
        """Get relevant package suggestions based on task type"""
        preferred = self.config['preferences']['tools_and_tech']['preferred_packages']
        
        task_packages = {
            'networking': ['dio'],
            'images': ['cached_network_image'],
            'immutability': ['freezed'],
            'navigation': ['auto_route'],
            'state': ['flutter_bloc']
        }
        
        return task_packages.get(task_type.lower(), preferred)
    
    def update_context(self, key: str, value: Any) -> None:
        """Update context awareness with new information"""
        if 'runtime_context' not in self.config:
            self.config['runtime_context'] = {}
        
        self.config['runtime_context'][key] = value
    
    def save_config(self) -> None:
        """Save updated config back to file"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, allow_unicode=True, sort_keys=False)
    
    def get_summary(self) -> str:
        """Get a human-readable summary of personalization settings"""
        profile = self.get_user_profile()
        context = self.get_current_context()
        
        summary = f"""
╔══════════════════════════════════════════════════════════╗
║           PERSONALIZATION PROFILE SUMMARY                ║
╚══════════════════════════════════════════════════════════╝

👤 USER: {profile.name}
📋 Role: {profile.role}
🎓 Education: {profile.education}

💼 CURRENT PROJECT:
   {context['work']['current_project']}
   Architecture: {context['work']['architecture']}

🎯 RECENT FOCUS:
   {chr(10).join(f"   • {challenge}" for challenge in context['recent_challenges'][:3])}

⚙️ PREFERENCES:
   • Communication: Direct and technical
   • Code style: Clean, minimal duplication
   • State management: flutter_bloc
   
🚀 GOALS:
   • Master ML/AI technologies
   • Launch startup within 2 years
   • Build local LLM systems
        """
        return summary


def main():
    """Example usage"""
    manager = PersonalizationManager()
    
    # Display profile summary
    print(manager.get_summary())
    
    # Get system prompt for agent
    print("\n" + "="*60)
    print("SYSTEM PROMPT FOR AGENT:")
    print("="*60)
    print(manager.build_system_prompt())
    
    # Example: Check if should suggest optimization
    code_sample = "for loop with nested loop and duplicate code"
    should_optimize = manager.should_suggest_optimization(code_sample)
    print(f"\nShould suggest optimization for '{code_sample}': {should_optimize}")
    
    # Get relevant packages for a task
    packages = manager.get_relevant_packages('images')
    print(f"Recommended packages for image handling: {packages}")


if __name__ == "__main__":
    main()
