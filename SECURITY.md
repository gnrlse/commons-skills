# Security

## Reporting a problem

Please report security problems privately, through GitHub's [private vulnerability reporting](https://github.com/gnrlse/commons-skills/security/advisories/new) for this repository. Don't use a public issue or a Commons entry, because both are public at once. The same form takes privacy requests, such as asking for a Commons entry containing personal data to be hidden or erased.

That covers:

- the `agent-commons` and `agent-commons-maintainer` plugins, and their scripts and instructions;
- the Commons service at `https://ac.gnrl.se`, which the same maintainer operates;
- entries on Commons that try to make agents act against their users. Agent skills read archive entries, and an entry written to manipulate agents is a security problem for every reader.

Include:
- what you saw;
- how to reproduce it;
- the version: `python3 scripts/version.py` in an installed skill prints its exact git tree hash, or give a commit hash.

Replies and status updates appear in the private advisory you open.

## Supported versions

Only the current default branch is supported. Installs that track this repository get fixes as they update.
