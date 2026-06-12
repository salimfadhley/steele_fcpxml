# CLI `--json` always emits an empty `info` object - does any caller rely on it?

**Status:** cleanup (not blocking; affects only the CLI's --json output)
**Created:** 2026-06-12
**Slug:** cli-json-info-empty

## Context

Porting the validator CLI from
`/Users/salimfadhley/workspace/mind_of_steele/src/mind_of_steele/fcpxml_validator/main.py`
to `src/steele_fcpxml/cli.py`.

The `--json` branch (lines 60-73) builds its `info` payload like this:

```python
"info": {
    k: v
    for k, v in result.info.items()
    if not isinstance(v, (list, object))
},
```

Every Python value is an instance of `object`, so `isinstance(v, (list, object))`
is always `True`, the `not` makes it always `False`, and the comprehension
therefore yields `{}` for **every** input. The `--json` output's `info` field
is always an empty object - none of the real validation metadata
(version, asset/clip counts, format details) ever reaches it. The presumed
intent was to drop only the non-JSON-serializable values (the `ClipInfo`
lists), i.e. something like `if not isinstance(v, (list, dict))` or a
positive allow-list of scalar keys.

## Specific question

Does any downstream consumer (a CI job, a script, anything that parses
`validate ... --json`) currently depend on the `info` field being present and
populated - or, conversely, depend on it being empty? Since the field has
always been empty, I expect nothing relies on its contents, but you can grep
`mind_of_steele` for callers of the JSON output to confirm.

## What I plan to do if I get no answer

Fix the filter so scalar info values (str / int / float / bool / None) are
included and the non-serializable lists (e.g. the `clips` list of `ClipInfo`)
are excluded, so `--json` emits the useful metadata it was always meant to.
I will add a test asserting `--json` output includes `fcpxml_version` and the
count fields. If you would rather I preserve the exact current behaviour
(empty `info`) for strict backward compatibility, say so and I will port it
verbatim instead.
