import json
import random
import uuid
from datetime import datetime

def generate_messy_chunk(size_kb=5):
    """Generates synthetic terminal/Jira/GitHub noise."""
    types = ["JIRA_ISSUE", "GH_PR", "TERMINAL_LOG", "CLI_NOTE"]
    log_noise = [
        "ERROR: NullPointerException at 0x4f22a",
        "DEBUG: [NLP] Tokenizer context window saturated",
        "WARN: Auth provider timeout, retrying in 5s...",
        "GIT: merge conflict in backend/app/main.py"
    ]
    
    payload = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),
        "type": random.choice(types),
        "content": " ".join(random.choices(log_noise, k=size_kb * 10)),
        "metadata": {
            "branch": "feat/nlp-tuning",
            "repo": "komorebi-core",
            "user": "operator-01"
        }
    }
    return payload

if __name__ == "__main__":
    # Generate 50 chunks for the "Hammer" test
    hammer_data = [generate_messy_chunk(random.randint(2, 20)) for _ in range(50)]
    with open("hammer_test_data.json", "w") as f:
        json.dump(hammer_data, f, indent=2)
    print(f"Generated 50 chunks in hammer_test_data.json")
