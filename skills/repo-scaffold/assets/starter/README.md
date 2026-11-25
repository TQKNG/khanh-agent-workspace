<h1 align="center">{{PROJECT_NAME}}</h1>

<p align="center">
  <a href="https://github.com/{{OWNER}}/{{REPOSITORY}}/actions/workflows/{{CI_WORKFLOW}}.yml">
    <img alt="CI" src="https://img.shields.io/github/actions/workflow/status/{{OWNER}}/{{REPOSITORY}}/{{CI_WORKFLOW}}.yml?style=flat-square&label=ci" />
  </a>
  <!-- Include the release badge only when the repository has a release workflow. -->
  <a href="https://github.com/{{OWNER}}/{{REPOSITORY}}/actions/workflows/{{RELEASE_WORKFLOW}}.yml">
    <img alt="Release" src="https://img.shields.io/github/actions/workflow/status/{{OWNER}}/{{REPOSITORY}}/{{RELEASE_WORKFLOW}}.yml?style=flat-square&label=release" />
  </a>
  <a href="https://github.com/{{OWNER}}/{{REPOSITORY}}/releases">
    <img alt="Version" src="https://img.shields.io/github/v/release/{{OWNER}}/{{REPOSITORY}}?style=flat-square" />
  </a>
  <a href="LICENSE">
    <img alt="License" src="https://img.shields.io/github/license/{{OWNER}}/{{REPOSITORY}}?style=flat-square" />
  </a>
</p>

<h3 align="center">{{TEN_WORD_PRODUCT_SUMMARY}}</h3>

<p align="center">
  <img alt="{{PROJECT_NAME}} demo" src="{{DEMO_IMAGE_PATH_OR_URL}}" width="960" />
</p>

## Overview

{{PROJECT_NAME}} {{OVERVIEW_SENTENCE_ONE}}
{{OVERVIEW_SENTENCE_TWO}}
Current status: {{CURRENT_STATUS}}.

## Core Features

<!-- Keep each feature name to two to four words and describe its user benefit. -->
- **{{FEATURE_ONE_NAME}}** - {{FEATURE_ONE_BENEFIT}}.
- **{{FEATURE_TWO_NAME}}** - {{FEATURE_TWO_BENEFIT}}.
- **{{FEATURE_THREE_NAME}}** - {{FEATURE_THREE_BENEFIT}}.

<!-- Replace these three image placeholders with useful screenshots, or remove this block when images are unavailable. -->

<p align="center">
  <img alt="{{PROJECT_NAME}} screenshot one" src="{{SCREENSHOT_ONE_PATH_OR_URL}}" width="32%" />
  <img alt="{{PROJECT_NAME}} screenshot two" src="{{SCREENSHOT_TWO_PATH_OR_URL}}" width="32%" />
  <img alt="{{PROJECT_NAME}} screenshot three" src="{{SCREENSHOT_THREE_PATH_OR_URL}}" width="32%" />
</p>

## Quick Start

{{ONE_SENTENCE_LOCAL_SETUP_INTRODUCTION}}

```sh
{{CLONE_OR_LOCAL_SETUP_COMMAND}}
{{CHANGE_TO_PROJECT_DIRECTORY_COMMAND}}
{{INSTALL_COMMAND}}
{{CHECK_COMMAND}}
{{RUN_COMMAND}}
```

## Project Structure

```text
.
├── README.md
├── LICENSE
├── CONTRIBUTING.md
├── AGENTS.md
├── CLAUDE.md
├── {{PROJECT_SOURCE_OR_INFRASTRUCTURE_DIRECTORY}}/
│   └── {{PROJECT_SPECIFIC_FILES}}
└── .github/
    ├── copilot-instructions.md
    ├── pull_request_template.md
    ├── ISSUE_TEMPLATE/
    │   ├── bug_report.md
    │   └── feature_request.md
    └── workflows/
        └── {{CI_WORKFLOW}}.yml
```

<!-- Update this tree to match the files actually present in the repository. -->
<!-- If release setup is accepted, include its real files, such as RELEASING.md, release-please-config.json, .release-please-manifest.json, and the release workflow. -->

## How It Works

```mermaid
flowchart LR
    Input[{{INPUT_OR_TRIGGER}}] --> Interface[{{USER_OR_CALLER_INTERFACE}}]
    Interface --> Core[{{CORE_PROCESSING_STEP}}]
    Core --> Service[{{DATA_STORE_OR_EXTERNAL_SERVICE}}]
    Service --> Result[{{USER_VISIBLE_RESULT}}]
```

{{ONE_SENTENCE_FLOW_EXPLANATION}}.

- **{{FLOW_NODE_ONE_NAME}}** - {{FLOW_NODE_ONE_DESCRIPTION}}.
- **{{FLOW_NODE_TWO_NAME}}** - {{FLOW_NODE_TWO_DESCRIPTION}}.
- **{{FLOW_NODE_THREE_NAME}}** - {{FLOW_NODE_THREE_DESCRIPTION}}.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for local setup, checks, and pull request guidance.

## License

See [LICENSE](LICENSE) for the project's license.
