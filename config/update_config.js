const fs = require("fs");

const config = {
    models: {
        providers: {
            ollama: {
                baseUrl: "http://locus-ollama:11434",
                apiKey: "ollama-local",
                api: "ollama",
                models: []
            }
        }
    },
    agents: {
        defaults: {
            model: {
                primary: "ollama/llama3.1:8b"
            }
        }
    }
};

const configPath = "/home/node/.openclaw/openclaw.json";
const existing = JSON.parse(fs.readFileSync(configPath, "utf8"));

Object.assign(existing, config);

fs.writeFileSync(configPath, JSON.stringify(existing, null, 2));

console.log("Config updated");
