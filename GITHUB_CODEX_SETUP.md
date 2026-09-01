# Codex + GitHub setup

This repository already contains `AGENTS.md`, so Codex can understand the project constraints.

## Recommended flow
1. Create a new GitHub repository, e.g. `capstone-gait`.
2. Upload/push this project as the initial commit.
3. Open Codex (web, desktop, IDE, or CLI) and sign in with your ChatGPT account.
4. In Codex web/cloud, connect GitHub and authorize only this repository if you want the narrowest permission scope.
5. Select the repository as the Codex working environment.
6. Ask Codex to read `AGENTS.md` first.
7. Give small tasks and review the diff/tests.
8. For cloud tasks, use the available Create PR / pull-request workflow rather than merging unreviewed changes.

## First Codex prompt
Read AGENTS.md and README.md. Run the unit tests first.
Then inspect the current calibration pipeline without changing its architecture.
Report any compatibility issues with my Windows + Python 3.11 environment.
After that, fix only confirmed issues, rerun tests, and summarize the diff.

## Useful follow-up prompt
Implement ESP32 serial ingestion using the JSON protocol documented in README.md.
Do not change the timestamp strategy: assign the common PC monotonic timestamp when each packet is received.
Add a parser test with valid and malformed packets.

## Local git bootstrap
```bash
git init
git add .
git commit -m "Initial gait calibration MVP"
git branch -M main
git remote add origin https://github.com/YOUR_ID/capstone-gait.git
git push -u origin main
```

Do not place GitHub personal access tokens inside this repository.
