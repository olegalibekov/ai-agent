# 🚀 Quick Start Guide

## Setup in 3 minutes

### 1️⃣ Copy and fill config
```bash
cp personalization_config_john_doe.yaml personalization_config_john_doe.yaml
```

Edit `personalization_config_john_doe.yaml` with your information:
- Your name, role, tech stack
- Current project details
- Code style preferences
- Goals and interests

### 2️⃣ Install dependencies
```bash
pip install anthropic pyyaml
```

### 3️⃣ Set API key
```bash
export ANTHROPIC_API_KEY="your-key-here"
```

### 4️⃣ Use the agent
```python
from personalized_agent_example import PersonalizedAgent

agent = PersonalizedAgent()
response = agent.chat("Help me with this code")
print(response)
```

## What makes it personalized?

The agent will:
- ✅ Know your tech stack and preferences
- ✅ Remember your recent challenges
- ✅ Suggest packages you prefer
- ✅ Match your communication style
- ✅ Focus on your priorities (performance, clean code, etc.)

## Example interaction

**Without personalization:**
```
User: Review my code
Agent: Here's a generic review...
```

**With personalization:**
```
User: Review my code
Agent: [Checks your architecture patterns]
       [Looks for code duplication - your priority]
       [Suggests your preferred packages]
       [Matches your direct communication style]
```

## Test without API

Run the standalone demo to see personalization in action:

```bash
python demo_standalone.py
```

This shows how the system loads your profile, generates prompts, and makes context-aware decisions.

## Next steps

1. **Fill the config** with as much detail as you want
2. **Run demo** to verify it loads correctly
3. **Use PersonalizedAgent** for real conversations
4. **Update config** as your preferences evolve

The more detailed your config, the better the personalization!

---

**Full documentation:** See [README.md](README.md) for complete guide and examples.
