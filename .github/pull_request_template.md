## Summary

<!-- What does this change and why? -->

## Checklist

- [ ] `python -m pytest -q` passes (with `QT_QPA_PLATFORM=offscreen`)
- [ ] No change touches resources that do not belong to KJ Des
      (other hosts blocks, tasks, folders, registry entries)
- [ ] Hosts markers, task name, folder names and installer AppId are unchanged
- [ ] New user-visible text is added to `ar.json`, `tr.json` and `en.json`
- [ ] No logs, local paths, keys, certificates or other secrets are included
- [ ] Network-engine changes (if any) were tested on a real network — describe below

## Testing notes
