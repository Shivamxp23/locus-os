import json

config = {
    "models": {
        "providers": {
            "ollama": {
                "baseUrl": "http://locus-ollama:11434",
                "apiKey": "ollama-local",
                "api": "ollama",
            }
        }
    },
    "agents": {"defaults": {"model": {"primary": "ollama/llama3.1:8b"}}},
}

with open("/home/node/.openclaw/openclaw.json", "r") as f:
    existing = json.load(f)

existing.update(config)

with open("/home/node/.openclaw/openclaw.json", "w") as f:
    json.dump(existing, f, indent=2)

print("Config updated")
