"""Fill in the trusted config from providers/models.yaml's selected reviewer."""
import os
from pathlib import Path

import yaml

path = Path(__file__).with_name("config.yaml")
config = yaml.safe_load(path.read_text())
reviewer = os.environ["REVIEWERS"].split()[0]
if reviewer == "claude_code":
    if os.getenv("OMNIGENT_STATIC_REPAIR") != "1":
        raise SystemExit("Neon repair requires the static tool-availability controls")
    settings_path = Path(os.environ["OMNIGENT_CONFIG_HOME"]) / "config.yaml"
    settings = yaml.safe_load(settings_path.read_text())
    if settings.get("harness", {}).get("claude-native", {}).get("args") != ['--tools', 'Read,Edit,Write,Glob,Grep', '--disallowedTools', 'mcp__omnigent__*', '--setting-sources', '', '--strict-mcp-config', '--disable-slash-commands']:
        raise SystemExit("Neon repair tool-availability configuration is missing or changed")
if reviewer == "claude_code":
    executor = {"harness": "claude-native", "permission_mode": "auto"}
elif reviewer == "codex":
    executor = {"harness": "codex-native", "yolo": True}
else:
    raise SystemExit(f"Unsupported repair reviewer: {reviewer}")
executor["model"] = os.environ["REVIEWER_MODEL"]
config["executor"]["config"] = executor
config["os_env"]["cwd"] = os.environ["GITHUB_WORKSPACE"]
path.write_text(yaml.safe_dump(config, sort_keys=False))
