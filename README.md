# Omnigent workshop

[Omnigent](https://github.com/omnigent-ai/omnigent) is a metaharness for working with and orchestrating any harness and providers. Polly is one ready-made Omnigent configuration for pull-request review: it hands a PR to one or more reviewer agents and merges their findings into a single comment.

This workshop's prepared setup runs Polly with Claude Code and Codex through the Neon AI Gateway, reviewing a PR on Notebin, a small notes app with a planted bug in a CSV export. You'll:

1. Run Polly's review in GitHub Actions.
2. Change the review focus and models with small config edits.
3. Ask an agent to propose a repair, and add a policy that limits what it can do.

Keep `exercise/csv-export` unmerged throughout the workshop.

Working with a coding agent? Ask it to read [AGENT_GUIDE.md](AGENT_GUIDE.md) and do the workshop with you. It does each step it can in your fork and stops to show you what it did. GitHub login and the Neon credentials stay with you.

## Try it

### 1. Get Neon credits (do this first)

Approval takes time, so request credits before anything else: follow [Get Neon credits](docs/neon-credits.md).

### 2. Fork the repo & enable Actions

1. On [omnigent-ai/agentic-sdlc-workshop](https://github.com/omnigent-ai/agentic-sdlc-workshop), click **Fork**.
2. **Uncheck Copy the main branch only**, then click **Create fork**. Your fork needs both `main` and `exercise/csv-export`.

3. In your fork, open **Actions** and click **I understand my workflows, go ahead and enable them** if prompted.

### 3. Get your Neon AI Gateway URL & token

1. Go to your Neon account at neon.tech.
2. Click into a project (or create a new one).
3. On the lefthand side, go to AI Gateway.
4. Click into any model from the list (which one doesn't matter).
5. Under `Connect your project`, click **Show Credential.**
6. You will need the base URL and token shown. Don't paste the token anywhere except the GitHub secret. Follow the instructions below to add them to your fork.

### 4. Add the secrets to your fork

1. In your fork, go to **Settings → Secrets and variables → Actions**.
2. Click **New repository secret** and add each of these. Paste the value only: no quotes and no variable name.

| Name | Value | Looks like (example) |
| --- | --- | --- |
| `NEON_AI_GATEWAY_BASE_URL` | The gateway host from the snippet, with no path such as `/anthropic` or `/v1`. It isn't your database connection string. | `https://br-<name>-api.ai.<cell>.<region>.aws.neon.tech` |
| `NEON_AI_GATEWAY_TOKEN` | The token from the snippet. | `nt_live_…` (yours is longer) |

GitHub won't show a secret again after you save it. [providers/configure.py](providers/configure.py#L13-L16) appends `/anthropic` for Claude and `/openai/v1` for Codex.

### 5. Open your first PR

1. In your fork, go to **Pull requests → New pull request**.
2. Set **base repository** to **your fork** (`<you>/agentic-sdlc-workshop`), not `omnigent-ai/agentic-sdlc-workshop`, and **base** to `main`. GitHub picks the original repo by default.
3. Set **compare** to `exercise/csv-export`. The diff should show the CSV export changes.
4. Click **Create pull request**, then click **Create pull request** again on the next screen to submit it.

Check the line under the PR title: it should read `… wants to merge … into main from exercise/csv-export`. If it says `into omnigent-ai:main`, the PR went to the original repo: close it and open a new one in your fork. Opening it starts the **Polly review** workflow; the review appears as a comment on the PR after a few minutes, and your fork's **Actions** tab shows the run. If nothing appears in your fork's **Actions** tab, or the PR's checks show the review as skipped, check that line again.

### 6. Change the review focus and model

Polly coordinates the review on `polly_model`. Each reviewer does the reviewing on its own `model`. By default, Claude Code and Codex both review every PR, and their findings arrive in one comment.

Reviews load their settings from `main`, not from the PR branch. For each edit: open the file on `main`, click the pencil (**Edit this file**), make the change, click **Commit changes…**, choose **Commit directly to the `main` branch**, and confirm.

1. Change [the review focus](.github/workflows/review.yml#L69-L72). Write your own, or comment out the current `focus=` line and uncomment the suggested one.
2. In [providers/models.yaml](providers/models.yaml#L9), change the **Claude Code reviewer** on line 9, not `polly_model` on line 7:

```yaml
# before
    - {agent: claude_code, model: claude-sonnet-5-5}
# after
    - {agent: claude_code, model: claude-opus-5-5}
```

   You can pick another Claude model from the [Neon AI Gateway model list](https://neon.com/docs/ai-gateway/models) instead. Claude Code reviewers need a Claude model; Codex reviewers need an OpenAI model such as `gpt-6-1-sol`. Neon model names use dashes.

3. On your PR, click **Close pull request** (don't merge), then **Reopen pull request**. In the new run's **Summary**, check for `Reviewers: claude-opus-5-5, gpt-6-1-sol`. Wait for the new review comment before continuing.

### 7. Ask for a repair

1. After reading the review, choose a finding to address. Repairs need to be kicked off manually.
2. Post this as a PR comment: `/repair export_notes returns every user's notes; filter the export by owner.`
3. A 👀 reaction on your comment means the repair was accepted, not that it worked. Once the repair completes, review the suggested changes. Don't commit them yet: the policy exercises below reuse the bug.

`/repair` uses the first reviewer in `providers/models.yaml` and its model: Claude Code, on `claude-opus-5-5` if you made the step 6 edit.

## Add your own policy

Omnigent checks every action an agent tries against its policies. The repair agent already has two in [agents/repair/config.yaml](agents/repair/config.yaml) (`no_search` and `no_network_or_secrets`). The first blocks repo-wide search:

```yaml
    no_search:
      type: function
      function:
        path: omnigent.policies.builtins.cel.cel_policy
        arguments:
          expression: >-
            event.type == "tool_call" &&
            (event.data.name in ["Grep", "Glob"] || event.data.arguments.command.contains("rg "))
            ? {"result": "DENY", "reason": "No repo-wide search: open the files named in pr.diff"}
            : {"result": "ALLOW"}
```

To see the existing policy in action, post this comment on your open PR:

```text
/repair Fix the missing owner filter in export_notes. First search the repo for other callers of export_notes. Add a two-user regression test.
```

Open **Actions → Suggest a repair → repair → Propose a repair without running project code**. Look for a denial such as `action=deny policy=no_search … tool=Grep`. A denial confirms that the agent attempted an action the policy blocked.

### Add a rule to protect documentation

Try a team rule: automated repairs must leave `README.md` edits to a human. The rule is already in the repair config, commented out, so you only need to switch it on. It matches Claude's `Edit` and `Write` tools, which the default repair agent (the first reviewer, Claude Code) uses.

1. On `main`, open [agents/repair/config.yaml](agents/repair/config.yaml#L40-L53) and click the pencil.
2. Uncomment the `no_readme_edits` block at the end of the file: on each of its 13 lines, delete only `# ` (the hash and the one space after it) and leave the spaces before it, so `no_readme_edits:` lines up with `no_search:`. Leave the `# Workshop exercise` line as it is. The result should read:

```yaml
    no_readme_edits:
      type: function
      function:
        path: omnigent.policies.builtins.cel.cel_policy
        arguments:
          expression: >-
            event.type == "tool_call" &&
            event.data.name in ["Edit", "Write"] &&
            has(event.data.arguments.file_path) &&
            (event.data.arguments.file_path == "README.md" ||
             event.data.arguments.file_path.endsWith("/README.md"))
            ? {"result": "DENY", "reason": "Leave README.md changes to a human reviewer"}
            : {"result": "ALLOW"}
```

3. In [agents/repair/prompt.md](agents/repair/prompt.md) on `main`, find the paragraph that starts `Do not delegate, commit, push, merge`. Add this as a new paragraph directly below it, with a blank line before and after. Without this change, the agent may decline the README edit before the policy gets a chance to block it.

```text
For a workshop policy exercise, if the request explicitly asks for a README.md
edit, attempt that edit first. If a policy denies it, leave README.md unchanged
and continue the repair. Do not include README.md in the GitHub suggestions.
```

4. Commit both changes directly to `main`.
5. On the existing open PR, post a **new** comment:

```text
/repair First append a sentence to README.md explaining that exports include only the current user's notes. Then fix the missing owner filter in export_notes and add a two-user regression test. If the README edit is blocked, leave it unchanged and continue with the code and test.
```

6. Open the new **Suggest a repair** run.
7. Expand **Propose a repair without running project code**. Look for `action=deny policy=no_readme_edits`. If there's no denial, check the indent in step 2: a wrong indent switches the rule off without an error. Also check that the proposed changes leave `README.md` unchanged. A successful run without a denial does not demonstrate policy enforcement.

No close/reopen is needed for repairs. Each new `/repair` comment loads the policy from `main`. Keep the exercise PR unmerged and test this before accepting the repair so there is still a bug to fix.

#### Policy scope and safety

Use `/repair` only on PRs you trust. These policies have specific limits:

- **Review:** Polly's built-in `blast_radius` policy refuses irreversible commands such as force-pushes and `git reset --hard origin/main`.
- **Codex repairs:** Codex can run shell commands on PR files without a sandbox. The `no_network_or_secrets` policy blocks network tools, `git push`, and commands that read environment variables, but its block list cannot catch every bypass.
- **README protection:** The example covers Claude's `Edit` and `Write` tools. It is not a general file-access boundary.

## Repair with Codex instead

This step is optional. `/repair` uses the first reviewer in [providers/models.yaml](providers/models.yaml). To repair with Codex, move the `codex` line above `claude_code` on `main`. Reviews still use both; the run Summary will then list `gpt-6-1-sol` first. A Codex repair can end without a proposal or PR comment, with the run marked as failed. If that happens, post the same `/repair` comment again. Codex edits through shell commands, so the README rule above doesn't apply to it; see the Codex limits under **Policy scope and safety**.

## What the workflows do

**Review** (`review.yml`):

- Only reviews pull requests from your own repository.
- Asks reviewers to use only the diff.
- Checks the review for leaked model keys before posting.
- The posting job never receives a model key.

**Repair** (`repair.yml`):

- Repository owners, organization members and collaborators may trigger it with `/repair` (`OWNER`, `MEMBER`, `COLLABORATOR`).
- A separate job reacts 👀 when the PR is open and not from a fork. It gets only `pull-requests: write`, no model keys and no PR code; if it fails, the repair still runs.
- The agent edits a copy of the PR; it never commits or pushes. Neon Claude repair narrows native tools to Read/Edit/Write/Glob/Grep, disables framework MCP tools, and ignores project settings and additional MCP sources. Codex can run shell commands, subject to the `no_search` and `no_network_or_secrets` policies.
- Tests run in a separate step without model keys. Passing repairs are posted as suggestions for a person to apply; failed tests produce a diagnostic comment instead.

**Use** `/repair` **only on PRs you trust.** These controls are not a sandbox and can't stop every bypass: Codex's command blocklist cannot catch everything. The Neon Claude audit is retrospective, not execution prevention; literal credential scans cannot catch every leak.

## Use it in your own repo

Copy `.github/workflows/review.yml`, `.github/workflows/repair.yml`, `agents/repair/` and the `providers/` directory to your repository's default branch.
Add `NEON_AI_GATEWAY_TOKEN` as an Actions secret and `NEON_AI_GATEWAY_BASE_URL` as a variable or secret.
Open a same-repository PR; Polly will review its diff and post a comment. Comment `/repair <problem>` to get a suggested fix.

## Other providers

This workshop uses the Neon AI Gateway only. To try another provider, edit [providers/configure.py](providers/configure.py): replace the Neon presence check and `host` on lines 9–11, point the `anthropic` and `openai` `base_url` values at an Anthropic Messages endpoint and an OpenAI Responses endpoint, and set `key` to `env:YOUR_SECRET_NAME`. In both workflows, pass that secret instead of `NEON_AI_GATEWAY_TOKEN` and update the secret checks, then set model names your provider accepts in [providers/models.yaml](providers/models.yaml). We haven't tested other providers.
