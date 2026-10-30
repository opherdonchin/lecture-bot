# Lecture Package Handshake

**Handshake version: 1.** This is how an agent, or an instructor by hand, works with a course's lecture-bot instance to get a lecture installed: ask what's expected, send a package, get a result. It stays the same as the way of reaching an instance improves; only the route changes. [Decision 0003](../HILD/decisions/0003-lecture-package-handshake.md) records why.

A preparing agent needs its course's materials and a way to reach the instance. It does not need a lecture-bot clone or the instance's directory structure. For what a package holds, see the [package contracts](lecture_package_contract.md); for background, see [Concept-lecture-handshake](https://github.com/opherdonchin/lecture-bot/wiki/Concept-lecture-handshake).

## Operations

| Operation | Takes | Gives |
|---|---|---|
| `contract` | A course | What's expected: the contract and its name, the shared rules, and the preparation instructions |
| `check` | A course, a lecture ID, a package archive | A result. Installs nothing |
| `install` | The same, and optionally `replace` | A result. Installs the lecture switched off |

`install` refuses a lecture that is already installed unless asked to replace it, and never replaces one whose config does not say `"active": false`, because the app treats a missing setting as on. A replaced lecture moves to the instance's `lecture_backups/` folder. No operation switches a lecture on.

## The package archive

A `.zip` with the package's files at its top level. It holds only the files the app reads: `lecture_config.json`, `rubric.md` and the course's context files. The server refuses other files, subfolders, links, and archives over 20 MB or 50 files.

## Results

`contract` gives:

```json
{"handshake": 1, "ok": true, "errors": [], "package_contract": "pml-brief-1",
 "contract": "...", "shared_rules": "...", "instructions": "..."}
```

`check` and `install` give:

```json
{"handshake": 1, "ok": true, "lecture_id": "lecture_03", "package_contract": "pml-brief-1",
 "files": ["lecture_config.json", "rubric.md", "bot_notes.md"],
 "topics": [{"topic_id": "T1", "label": "..."}],
 "load_bearing": ["- **Load-bearing:** ..."],
 "errors": [], "installed": false, "message": ""}
```

When `ok` is false, `errors` says why, and an operation may leave out the other fields if it could not get that far.

`ok` means the package loads and declares the right contract. It does not mean the content is good: [the researcher's review is the only check on content](../HILD/decisions/0002-lecture-package-contract.md).

## Routes

| Route | Who | How |
|---|---|---|
| **SSH** | An agent or person with SSH access to the server | The command below |
| **Admin page** | The instructor by hand | *Lecture packages* in the admin app |

```bash
ssh <host> /srv/lecture-bot/code/scripts/lecture-package contract <course>
ssh <host> /srv/lecture-bot/code/scripts/lecture-package check <course> <lecture_id> < package.zip
ssh <host> /srv/lecture-bot/code/scripts/lecture-package install <course> <lecture_id> [--replace] < package.zip
```

The command prints one result and exits 0 if `ok` is true, 1 if not. It reads the instance's `LECTURES_DIR` and `TUTOR_PROMPT_TEMPLATE` from its settings, and nothing else there.

**The route is available only after it is deployed,** and what `contract` serves is what the deployed code and prompt use.

## What a course needs

In the course's repository:

- **A recipe,** `lecture_recipe.md`: where the course's sources are, and what it emphasises. It is entirely local to the course.
- **A pointer in its `AGENTS.md`,** for example:

  ```markdown
  To prepare a lecture for the tutor, run
  `ssh lecture-bot-bme /srv/lecture-bot/code/scripts/lecture-package contract pml`
  and follow the instructions it returns. The recipe is `lecture_recipe.md`.
  ```

An agent that cannot reach the instance, such as one on GitHub, prepares the package and hands it to someone who can.

## Changing the handshake

Any change to the operations, the archive or the results gets a new handshake version, here and in [`app/lecture_packages.py`](../app/lecture_packages.py).
