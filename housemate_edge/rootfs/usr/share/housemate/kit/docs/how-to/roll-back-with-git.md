# Roll back with git

`/config` is a git repository (run `scripts/git-init.sh` if it is not).

- What changed: `git status`, `git diff`, `git log --oneline -- <path>`.
- Undo a committed change and keep the history: `git revert <commit>`.
- Put one file back as it was at a commit: `git checkout <commit> -- <path>`,
  then commit it with a why.
- Undo uncommitted edits to one file: `git checkout -- <path>`.

After any rollback: `scripts/check-config.sh`, reload the domain involved, and
tell the user what you rolled back and why. Git does not hold `secrets.yaml`,
databases or credentials; those cannot be rolled back this way.
