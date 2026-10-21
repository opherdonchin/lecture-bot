# Provenance of lecture-bot's HILD build

Lecture-bot's HILD files were derived on 2026-10-21 from
[Motor-Learning-Lab/HILD@92de97e](https://github.com/Motor-Learning-Lab/HILD/tree/92de97e84bd1c6b61f9e1c997765e361dc7cd458),
the head of draft [HILD PR #13](https://github.com/Motor-Learning-Lab/HILD/pull/13),
which builds on draft [PR #11](https://github.com/Motor-Learning-Lab/HILD/pull/11).
Neither PR was merged upstream at the time. Lecture-bot owns its copy and does
not track upstream for upgrades ([decision 0001](decisions/0001-independent-hild-build.md)).
Upstream is MIT-licensed; its notice is kept in [LICENSE](LICENSE).

Work was done under [scope #14](https://github.com/opherdonchin/lecture-bot/issues/14)
in [PR #15](https://github.com/opherdonchin/lecture-bot/pull/15). The commit
[1e6462b](https://github.com/opherdonchin/lecture-bot/commit/1e6462b64c93f7f821d48343384f01c5e7f65878)
copies the chosen files **verbatim**, so `git diff 1e6462b` shows every local
change.

## Taken and adapted

| Lecture-bot file | Upstream source | Local change |
|---|---|---|
| [process.md](process.md) | `HILD/process.md` | Describes lecture-bot's process: concrete authority table, the lecture-bot wiki, six skills, keep-rule for `prompts/archive/` and `docs/archive/`. Install, integration and onboarding text removed. |
| [README.md](README.md) | `HILD/README.md` | Rewritten as lecture-bot's entry page; onboarding prompt replaced by a session-start prompt. |
| [templates/](templates/) (6 Markdown templates) | `HILD/templates/` | Unchanged except one comment in `wiki-code-page.md`. |
| [.claude/settings.json](../.claude/settings.json) | `HILD/templates/claude-settings.json` | Unchanged; moved to where Claude Code reads it. |
| [.codex/hooks.json](../.codex/hooks.json) | `HILD/templates/codex-hooks.json` | Unchanged; moved to where Codex reads it. |
| [scripts/session_context.sh](scripts/session_context.sh), [scripts/wiki_status.py](scripts/wiki_status.py) | `HILD/scripts/` | Unchanged. |
| [tests/hild/](../tests/hild/) | `tests/test_session_context.py`, `tests/test_wiki_status.py` | Repository-root path adjusted for the deeper directory. |
| [.agents/skills/](../.agents/skills/) `hild-orient`, `hild-scope`, `hild-explain`, `hild-journal`, `hild-understood` (with `new-wiki.md`), `hild-digest` | `.agents/skills/` | References to a host, installer, onboarding companion and upstream origin replaced by lecture-bot paths. |
| [AGENTS.md](../AGENTS.md), [CLAUDE.md](../CLAUDE.md) | upstream `CLAUDE.md` pattern | `AGENTS.md` is lecture-bot's own, absorbing `.instructions.md`; `CLAUDE.md` follows upstream's import pattern. |

## Not taken

- `install_hild.py`, `agent-setup.md`, `hild-integrate` and the onboarding
  companion: they exist to install HILD into other repositories or onboard new
  users.
- The Copilot hook template: lecture-bot uses Claude Code and Codex.
- Upstream's plan, journal and decision records: they describe HILD's own
  development. Lecture-bot keeps its own; upstream decisions remain readable
  at the pinned commit.
- Upstream CI workflows: lecture-bot's own `pixi run test` runs the copied
  script tests.
