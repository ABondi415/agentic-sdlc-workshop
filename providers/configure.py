"""Write Omnigent's Neon AI Gateway config and reviewer.env from models.yaml."""
import os
from pathlib import Path
import shlex
import sys

import yaml

host = os.getenv("NEON_AI_GATEWAY_BASE_URL", "").strip().rstrip("/")
if not os.getenv("NEON_AI_GATEWAY_TOKEN", "").strip() or not host:
    sys.exit("Add NEON_AI_GATEWAY_TOKEN and NEON_AI_GATEWAY_BASE_URL in Settings → Secrets and variables → Actions")

# One Neon credential serves both APIs. Only its name is written; the token stays in the environment.
key = "env:NEON_AI_GATEWAY_TOKEN"
endpoints = {"anthropic": {"base_url": f"{host}/anthropic", "api_key_ref": key},
             "openai": {"base_url": f"{host}/openai/v1", "api_key_ref": key, "wire_api": "responses"}}
models = yaml.safe_load(Path(__file__).with_name("models.yaml").read_text())["neon"]
reviewers = models["reviewers"]
for reviewer in reviewers:
    family = "anthropic" if reviewer["agent"] == "claude_code" else "openai"
    endpoints[family].setdefault("models", {"default": reviewer["model"]})
if "polly_model" in models:
    endpoints["anthropic"].setdefault("models", {"default": models["polly_model"]})
settings = {"providers": {"workshop": {"kind": "gateway", "default": list(endpoints), **endpoints}}}
if os.getenv("OMNIGENT_STATIC_REPAIR") == "1":
    # Availability restriction, not preapproval or an OS sandbox. Keep stock hooks.
    settings["harness"] = {"claude-native": {"args": ['--tools', 'Read,Edit,Write,Glob,Grep', '--disallowedTools', 'mcp__omnigent__*', '--setting-sources', '', '--strict-mcp-config', '--disable-slash-commands']}}
config = Path(os.environ.get("OMNIGENT_CONFIG_HOME", str(Path.home() / ".omnigent"))) / "config.yaml"
config.parent.mkdir(parents=True, exist_ok=True)
config.write_text(yaml.safe_dump(settings))
instructions = " and ".join(
    f"{r['agent']} with model {r['model']} (title review-{i})"
    for i, r in enumerate(reviewers, 1)
)
values = {"POLLY_HARNESS": models["polly"], "POLLY_MODEL": models.get("polly_model", reviewers[0]["model"]),
          "REVIEWER_MODEL": reviewers[0]["model"], "REVIEWERS": instructions}
Path("reviewer.env").write_text("\n".join(f"{k}={shlex.quote(v)}" for k, v in values.items()) + "\n")
message = f"Using Neon: found NEON_AI_GATEWAY_TOKEN. Reviewers: {', '.join(r['model'] for r in reviewers)}."
print(message)
with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as summary:
    summary.write(message + "\n")
