# GitHub setup commands

## Option A: Web UI + command line

1. On GitHub, create a new **private** repository named `pilot-pipeline`.
2. Do not add raw data or keys.
3. In terminal:

```bash
cd path/to/pilot-pipeline

git init
git branch -M main
git add README.md .gitignore requirements.txt configs docs scripts pipeline tests
git commit -m "Initialize multi-device pipeline scaffold"

git remote add origin https://github.com/YOUR_USERNAME/pilot-pipeline.git
git push -u origin main
```

## Option B: GitHub CLI

```bash
cd path/to/pilot-pipeline

git init
git branch -M main
git add README.md .gitignore requirements.txt configs docs scripts pipeline tests
git commit -m "Initialize multi-device pipeline scaffold"

gh repo create pilot-pipeline --private --source=. --remote=origin --push
```

## Safety check before every push

```bash
git status
git diff --cached --name-only
```

Make sure no files under `raw_data/`, `processed_data/`, `aligned_data/`, `quality_reports/`, credentials, keys, PDFs, PPTX files, or project-idea documents are staged.
