# Architecture

How the personal layout for the Herdr app works.
All diagrams are Mermaid and render on GitHub.

## 1. System overview

```mermaid
flowchart TB
    subgraph External["External services"]
        GH["GitHub<br/>(gh CLI, GraphQL)"]
    end

    subgraph Hub["Local hub (Python, detached process)"]
        HS["cockpit_hub.py<br/>TCP server 127.0.0.1:port, token auth"]
        GI["github_inbox.py<br/>InboxSource, 55 s cache"]
        GS["github_start.py<br/>issue to agent: plan, worktree"]
        AP["agent_profiles.py<br/>agents' set-up, switches"]
        HS --- GI
        HS --- GS
        HS --- AP
    end

    subgraph Mods["Mods (gpui-kit JS, hot reload)"]
        HJ["personal/hub.js<br/>hub client"]
        PG["personal (other apps)<br/>pages: inbox, agents, home, work ..."]
        SB["personal (app: sidebar)<br/>sidebar page"]
        WC["workspace-chrome-swiss<br/>header, shortcuts button, footer"]
        PG --> HJ
        SB --> HJ
    end

    subgraph Herdr["Herdr app (~/.config/herdr-app)"]
        LY["layouts/personal.json<br/>window tree"]
        AG["agents() and terminals"]
        CFG["cockpit.json, brand.json,<br/>keys.json, settings.json"]
    end

    GH --> GI
    CLI["Agent CLIs<br/>claude, codex, copilot"] --> AP
    HJ <-->|"JSON lines over TCP"| HS
    LY --> PG
    LY --> SB
    LY --> WC
    AG --> SB
    CFG --> HJ
    CFG --> WC
```

## 2. Layout structure

```mermaid
flowchart LR
    ROOT["root row"] --> SIDEBAR["sidebar column<br/>268 px"]
    ROOT --> MAIN["main-area column"]
    SIDEBAR --> BRAND["brand block<br/>workspace-chrome-swiss"]
    SIDEBAR --> SPAGE["sidebar page<br/>personal, app sidebar"]
    SIDEBAR --> FOOT["footer<br/>workspace-chrome-swiss"]
    MAIN --> TOP["topbar row<br/>tabs, bell, shortcuts button"]
    MAIN --> CENTER["center stack"]
    MAIN --> STATUS["status bar"]
    CENTER --> P1["home"]
    CENTER --> P2["work (terminals)"]
    CENTER --> P3["inbox"]
    CENTER --> P4["agents"]
    CENTER --> P5["mail, monitor,<br/>routines"]
    ROOT -.-> DRAWER["floating queue drawer"]
```

## 3. Hub startup and discovery

```mermaid
sequenceDiagram
    participant M as Mod (hub.js)
    participant C as cockpit.json / cache/hub.json
    participant L as Launcher (cockpit-hub)
    participant H as Hub process

    M->>C: read bin and cached {port, token}
    M->>H: connect 127.0.0.1:port with token
    alt hub reachable
        H-->>M: stream ready
    else hub down
        M->>L: hub start (Windows: direct, else env)
        L->>H: spawn detached server
        L-->>M: one JSON line {port, token}, then exits
        M->>H: connect
        H-->>M: stream ready
    end
```

## 4. Protocol operations

```mermaid
sequenceDiagram
    participant UI as Page or sidebar
    participant HC as hub.js
    participant H as Hub

    UI->>HC: need views inbox, agents
    HC->>H: subscribe [inbox, agents]
    H-->>HC: view updates (pushed)
    HC-->>UI: model
    UI->>HC: hover a PR
    HC->>H: fetch review_threads / pr_merge / ticket_card / start_plan / issue_draft / agent_profiles
    H-->>HC: top-level reply object
    UI->>HC: click an action
    HC->>H: act request_refresh / file_issue / submit_review / merge / start / open_url, toggle (agents)
    H-->>HC: result
```

A failing view is isolated, so the other subscribed views keep streaming.

## 5. Inbox data flow

```mermaid
flowchart LR
    GHAPI["gh api graphql"] --> SRC["InboxSource<br/>cache 55 s, error retry 30 s,<br/>warm-up at startup"]
    SRC --> BUILD["build_inbox()"]
    BUILD --> SEC["sections:<br/>alerts, reviews, work"]
    SEC --> ROWS["rows: pr, review, ticket, alert<br/>acts, text spans, item payload"]
    ROWS --> VIEW["inbox view"]
    VIEW --> SIDE["sidebar counts and list"]
    VIEW --> PAGE["Inbox page"]
    PAGE -->|"hover"| FETCH["fetch: checks, reviewers,<br/>review threads"]
    FETCH --> GHAPI
```

### The inbox's grouping

```mermaid
flowchart LR
    GQ["gh api graphql<br/>PRs, reviews, issues, repos"] --> B["build_inbox()"]
    RUNS["gh api actions/runs<br/>12 repos side by side"] --> B
    B -->|"rows by kind, each with its repo"| M["inbox model"]
    M --> G{"inbox-groups.js"}
    G -->|"byRepo (default)"| R["one heading per repo<br/>failing first, summary, folded if tickets only"]
    G -->|"byKind (w)"| K["alerts, reviews, PRs, runs, tickets"]
```

## 6. Reviewing and merging a pull request

```mermaid
sequenceDiagram
    participant R as Inbox row
    participant W as prreview.js (review window)
    participant H as Hub (github_pulls.py)
    participant G as GitHub (gh)

    R->>W: r (openPrReview)
    W->>H: fetch pr_diff {repo, number}
    H->>G: pull, changed files (paged), head again
    Note over H,G: read again once if the head moved while reading
    H-->>W: files as diff lines, head_sha, checks, threads, my last review
    W->>W: read, comment on lines (DiffView)
    W->>W: a / x / m opens the confirm dialog
    Note over W: lists failing checks, unresolved threads, drafts, stale comments
    W->>H: act submit_review {head_sha, event, body, comments}
    H->>G: read the pull request now
    alt closed, own approval, or head is not head_sha
        H-->>W: error (the window offers to read the new commits)
    else still the commit that was read
        H->>G: POST reviews with commit_id = head_sha
        H-->>W: note, and the inbox refreshes
    end
```

A merge takes the same path with `act merge [{repo, number, head_sha}, method]`.
The hub checks that the pull request is open, not a draft and still at `head_sha`, then calls the merge endpoint with `sha = head_sha`, so GitHub refuses it too if the branch moved in between.
The methods offered come from `merge_choices`: none unless GitHub says the pull request is ready, then the ones the repository allows.

### Checks

```mermaid
flowchart LR
    T["Checks tab (prchecks.js)"] -->|"fetch pr_checks"| H["github_checks.py"]
    H --> R["check runs + commit statuses<br/>of the head, failing first"]
    T -->|"select an Actions job: fetch check_log"| H
    H --> L["job log, cut to the failing step<br/>(header to last error), else the end"]
    T -->|"Re-run failed: confirm, then act rerun_failed"| H
    H -->|"only runs of the same head_sha"| G["gh api POST rerun-failed-jobs"]
```

## 7. Agents list with fallback

```mermaid
flowchart TD
    A["Sidebar needs agent rows"] --> B{"Hub up and value.agents<br/>is an array?"}
    B -->|yes| C["Use the hub's rows"]
    B -->|no| D["Use Herdr's own agents()"]
    C --> E["Render cards with critter art"]
    D --> E
```

The bundled hub serves a stub for `agents`, so in practice Herdr's own agents are used.

## 8. Branding

```mermaid
flowchart LR
    INST["install.py --brand-name --brand-logo"] --> BJ["brand.json"]
    INST --> BD["brand/logo-hash.png"]
    HAND["manual edit"] --> BJ
    BJ -->|"read every 4 s"| WC["workspace-chrome-swiss"]
    BD --> WC
    WC --> HDR["header: logo and name"]
    WC --> BTN["top-right shortcuts button"]
    NONE["no brand.json"] -.-> DEF["Workspace + initial tile, '?' button"]
```

Logo paths must stay inside the Herdr home, and file names carry a content hash because Herdr caches images by path.

## 9. Install flow

```mermaid
flowchart TD
    S["python install.py"] --> P["check Python 3.9+, gh signed in"]
    P --> LM["copy layout and 3 mods<br/>(skip identical, back up replaced)"]
    LM --> HUBI["copy hub into cockpit-hub/"]
    HUBI --> CJ{"cockpit.json exists and<br/>points elsewhere?"}
    CJ -->|"no or --force-hub"| W["write cockpit.json"]
    CJ -->|yes| K1["leave alone, print note"]
    W --> K["merge layout:personal into keys.json"]
    K1 --> K
    K --> BR["apply brand flags if given"]
    BR --> V["herdr-app check per mod,<br/>hub start, optional layout.switch"]
```

Replaced files go to `<home>/.install-backups/<time>/`.

## 10. Repository map

```mermaid
flowchart LR
    R["repo"] --> L["layouts/<br/>personal.json, .svg"]
    R --> MD["mods/"]
    R --> HB["hub/"]
    R --> TS["tests/"]
    R --> KJ["keys.layout-personal.json"]
    R --> IN["install.py"]
    R --> DOCS["README.md, RECIPE.md, ARCHITECTURE.md"]
    MD --> M1["personal<br/>+ critters/art"]
    MD --> M3["workspace-chrome-swiss"]
    HB --> H1["cockpit_hub.py, github_inbox.py,<br/>github_pulls.py, github_checks.py,<br/>github_start.py, agent_profiles.py"]
    HB --> H2["cockpit-hub, cockpit-hub.cmd"]
    HB --> H3["worker-prompt.md"]
```

## 11. Platform notes and limits

Windows quirks, the hub's start-up contract and the list of things that must never ship are in `RECIPE.md` under "Watch out".
What is and is not connected is in `README.md`.
