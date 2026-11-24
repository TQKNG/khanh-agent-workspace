# Docs repository layout

```
docs.json
images/diagrams/<doc-number>.png     # exported PNGs, referenced from pages as /images/diagrams/...
diagrams/src/<doc-number>.drawio     # editable sources, created from the templates
architecture/*.mdx                   # pages that embed the PNGs
```

- Mintlify cannot render `.drawio`; pages embed the PNG and link to the source.
- Commit source and PNG together.
  The `/new-diagram` command and the check hook assume this layout; when a repository uses other folders, pass `--out-dir` to the script and mention the change to the user.
- When working through the Mintlify admin connection rather than a local clone, upload the PNG with the upload tool and keep the `.drawio` source in the git repository.
