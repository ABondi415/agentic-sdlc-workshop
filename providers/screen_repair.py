"""Literal-only proposal screening. Never print proposal bytes or credentials."""
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

CREDENTIALS = ('ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'OPENROUTER_API_KEY',
               'DATABRICKS_TOKEN', 'NEON_AI_GATEWAY_TOKEN', 'GH_TOKEN', 'GITHUB_TOKEN')


def safe_path(root, name):
    relative = Path(name)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Unsafe proposal path')
    path = root
    for part in relative.parts:
        path = path / part
        if path.is_symlink():
            raise ValueError('Symlink proposal path')
    if not path.resolve().is_relative_to(root):
        raise ValueError('Outside proposal path')
    if path.exists() and not stat.S_ISREG(path.stat().st_mode):
        raise ValueError('Nonregular proposal path')
    return path


def screen(workspace, environment):
    root = Path(workspace).resolve(strict=True)
    # No inherited Git helpers, traces, global configuration, pager or credentials.
    env = {'PATH': os.defpath, 'HOME': str(root), 'LC_ALL': 'C',
           'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull,
           'GIT_ATTR_NOSYSTEM': '1', 'GIT_TERMINAL_PROMPT': '0'}
    command = ['/usr/bin/git', '--no-pager', '-c', 'core.fsmonitor=false',
               '-c', 'core.attributesFile=' + os.devnull]

    def git(arguments):
        return subprocess.run(command + arguments, cwd=root, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              check=True).stdout

    # --no-textconv does NOT disable clean/process filters. Override every
    # configured filter driver without running it or printing its configuration.
    result = subprocess.run(command + ['config', '--null', '--name-only',
                            '--get-regexp', r'^filter\..*\.(clean|smudge|process|required)$'],
                            cwd=root, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    if result.returncode not in (0, 1):
        raise ValueError('Cannot resolve filter configuration')
    for raw in result.stdout.split(b'\0'):
        if not raw:
            continue
        key = raw.decode('utf-8')
        suffix = key.rsplit('.', 1)[-1]
        if not key.startswith('filter.') or suffix not in ('clean', 'smudge', 'process', 'required') or '=' in key:
            raise ValueError('Unsupported filter configuration')
        command += ['-c', key + ('=false' if suffix == 'required' else '=')]

    # Reject symlink/gitlink index entries and working-tree path components
    # BEFORE Git can read their contents. Missing (deleted) files are allowed.
    for entry in git(['ls-files', '--stage', '-z']).split(b'\0'):
        if not entry:
            continue
        metadata, name = entry.split(b'\t', 1)
        mode, oid, stage = metadata.split()
        if mode not in (b'100644', b'100755') or stage != b'0':
            raise ValueError('Unsafe tracked proposal entry')
        safe_path(root, os.fsdecode(name))

    proposal = safe_path(root, 'repair.json')
    present = proposal.exists()
    payloads = [proposal.read_bytes()] if present else []
    payloads.append(git(['diff', '--no-ext-diff', '--no-textconv', '--no-renames', '--text']))
    credentials = [environment[name].encode('utf-8') for name in CREDENTIALS if environment.get(name)]
    leaked = any(credential in payload for credential in credentials for payload in payloads)
    return {'repair_output_literal_screen_passed': not leaked,
            'repair_proposal_present': present}


if __name__ == '__main__':
    try:
        flags = screen(sys.argv[1], os.environ)
    except Exception:
        print(json.dumps({'repair_output_literal_screen_unavailable': True}))
        raise SystemExit(1)
    print(json.dumps(flags, sort_keys=True))
    raise SystemExit(0 if flags['repair_output_literal_screen_passed'] else 1)
