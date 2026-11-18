# Security policy

KJ Des runs with administrator rights and changes DNS and the Windows hosts
file, so security reports are taken seriously.

## Reporting a vulnerability

Please **do not open a public issue** for security problems.

Use GitHub's private vulnerability reporting for this repository
(**Security → Report a vulnerability**). If that option is not available,
contact the maintainer on GitHub ([@LUCASS7001](https://github.com/LUCASS7001))
and ask for a private channel.

Please include the KJ Des version, Windows version, steps to reproduce and,
if relevant, the lines from the Activity log (`%APPDATA%\KJ Des\kjdes.log`).
Remove any personal data from logs before sharing them.

## Scope

In scope, for example:

- privilege escalation through KJ Des, its installer or its recovery task;
- changes to DNS, hosts entries, tasks, files or registry entries that do not
  belong to KJ Des;
- the local relay forwarding traffic for hosts outside its allow-list;
- failures to restore the original network configuration.

Out of scope: whether a particular network or ISP can be unblocked.

## Supported versions

Only the latest released version receives fixes.
