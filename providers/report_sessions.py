"""Allowlisted session + bound agent harness evidence, never raw config/transcripts."""
import json
import os
from pathlib import Path
import re
import sys
import tarfile

import yaml
from sqlalchemy import create_engine, select
from omnigent.db.db_models import SqlAgent, SqlConversation, SqlConversationLabel, SqlConversationMetadata

HARNESSES = {"claude-sdk", "claude-native", "codex-native"}


def safe(value):
    return value if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_./:-]{1,160}", value) else None


def bound_harness(artifacts, key, subagent=None):
    """Read only config.yaml from the registered agent's in-memory bundle."""
    if not isinstance(key, str) or ".." in Path(key).parts:
        return None
    path = (artifacts / key).resolve()
    if not path.is_relative_to(artifacts.resolve()) or not path.is_file():
        return None
    try:
        with tarfile.open(path, "r:gz") as archive:
            if subagent is not None and not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", subagent):
                return None
            member_name = f"agents/{subagent}/config.yaml" if subagent else "config.yaml"
            members = [m for m in archive.getmembers() if m.name.removeprefix("./") == member_name]
            if len(members) != 1 or not members[0].isfile() or members[0].size > 1024 * 1024:
                return None
            config = yaml.safe_load(archive.extractfile(members[0]).read())
        if subagent and config.get("name") != subagent:
            return None
        harness = config.get("executor", {}).get("config", {}).get("harness")
        return harness if harness in HARNESSES else None
    except (OSError, ValueError, tarfile.TarError, yaml.YAMLError, AttributeError):
        return None


def screened_json(row):
    message = json.dumps(row, sort_keys=True)
    for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY",
                "DATABRICKS_TOKEN", "NEON_AI_GATEWAY_TOKEN"):
        credential = os.getenv(key)
        if credential and credential in message:
            raise SystemExit("Refusing credential-bearing runtime metadata")
    return message


def report(root):
    count = 0
    for db in Path(root).glob("ap-chat-data-*/chat.db"):
        engine = create_engine(f"sqlite:///file:{db}?mode=ro&uri=true")
        try:
            with engine.connect() as connection:
                query = select(SqlConversation.id, SqlConversation.parent_conversation_id,
                    SqlConversation.agent_id, SqlAgent.name, SqlAgent.bundle_location,
                    SqlConversation.session_overrides, SqlConversationMetadata.inference_snapshot,
                    SqlConversationMetadata.sub_agent_name).join(SqlConversationMetadata,
                        SqlConversation.id == SqlConversationMetadata.id).join(SqlAgent,
                        SqlConversation.agent_id == SqlAgent.id)
                for sid, parent, aid, name, bundle, overrides, snapshot, subagent in connection.execute(query):
                    settings, inference = json.loads(overrides or "{}"), json.loads(snapshot or "{}")
                    executor = bound_harness(db.parent / "artifacts", bundle, subagent)
                    override = settings.get("harness_override")
                    harness = (override if override in HARNESSES else None) if override else executor
                    bridge_bound = connection.execute(select(SqlConversationLabel.value).where(
                        SqlConversationLabel.conversation_id == sid,
                        SqlConversationLabel.key == "omnigent.claude_native.bridge_id")).scalar_one_or_none() is not None
                    print("Runtime session: " + screened_json({
                        "session": safe(sid), "parent": safe(parent), "agent_id": safe(aid),
                        "agent_name": safe(name), "reviewer": safe(subagent),
                        "bound_executor_harness": executor, "harness": harness,
                        "claude_native_bridge_bound": bridge_bound,
                        "selected_model": safe(settings.get("model_override")),
                        "reported_model": safe(settings.get("reported_model")),
                        "inference_model": safe(inference.get("model")),
                    }))
                    count += 1
        finally:
            engine.dispose()
    if not count:
        print("Runtime session evidence unavailable; no native success established")


if __name__ == "__main__":
    report(sys.argv[1])
