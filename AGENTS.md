# Project Guidelines for Wah Yan Star

## Deployment & Version Control Rules

1. **Local Testing First**:
   - All code updates, bug fixes, and feature additions must be tested and verified locally on `http://localhost:8085`.
   - Never push changes to GitHub (`git push origin main`) automatically.

2. **Explicit User Permission Required for GitHub & Render**:
   - Commits can be created locally on the `main` branch.
   - Pushing to GitHub (`origin main`) is **STRICTLY PROHIBITED** until the user has thoroughly tested the local webapp and has explicitly granted permission to push.
   - Render.com is linked to the GitHub repository. Because pushing to GitHub can trigger production deployment on Render, always wait for the user's explicit authorization before running any push commands.
