# {change-name}

## Scope

<!-- Scope -->
<!-- What a person must observe in this change, and why no automated test can observe it. A check the agent can run and judge itself belongs to the Functional Tests of tasks.md, not here. -->
<!-- If nothing in this change needs a person, say so here with the reason, and leave the Scenarios section with no scenario. -->

## Scenarios

<!-- Scenarios -->

### 1. {scenario name}

<!-- Scenario -->
<!-- Keep the fields in this order, and write "none" for a precondition or cleanup there is none of. Take the commands, flags, paths and messages from the code as built. -->
<!-- The result is written only as the user reports it: "- [passed]", "- [failed] <what the user observed>" or "- [skipped] <the user's reason>", in English in every language. A diagnosis of a failure goes under it as indented sub-items. -->

**Covers:**

- [`{domain}`](/dev/specs/{domain}/spec.md): {specification scenario name}

**Preconditions:** {what must hold before the first step}

**Steps:**

1. `{command}`

**Expected:**

- {what the user should observe}

**Cleanup:** {how to undo the steps}

**Result:**

- [ ] {left empty until the user reports}
