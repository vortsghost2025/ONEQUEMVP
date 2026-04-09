# START COMMAND - MANDATORY FOR ALL AGENTS

## BEFORE STARTING ANY WORK:

1. **READ** `.kilo/AGENT_ACTIVITY_LOG.md` - Review all previous actions
2. **CHECK** latest entries - Understand current state
3. **LOG** your presence - Add entry with your Agent ID if first time
4. **VERIFY** no conflicts - Check if another agent is working on same files

## MANDATORY LOGGING RULES:

### Every action MUST be logged with:
- **Timestamp**: ISO 8601 format (e.g., `2026-04-09T09:22:40-04:00`)
- **Agent ID**: Your model identifier (e.g., `kilo (z-ai/glm5)`)
- **Action Type**: One of:
  - `CREATE` - New file created
  - `MODIFY` - File modified
  - `DELETE` - File deleted
  - `TEST` - Test executed
  - `DEPLOY` - Deployment action
  - `DEBUG` - Debugging activity
  - `REVIEW` - Code review
  - `BLOCKED` - Blocked on something
  - `NOTE` - Important observation
- **Description**: What you did (concise)
- **Files**: List all affected files
- **Result**: Outcome (success/failure/pending)

### Log entry format:
```markdown
### 2026-04-09T09:22:40-04:00 | Agent: kilo (z-ai/glm5)
**Action**: [ACTION_TYPE]
**Description**: [What you did]
**Files**: 
- [file1]
- [file2]
**Result**: [outcome]
```

## ENFORCEMENT:

- **NO ACTION WITHOUT LOGGING** - If it's not logged, it didn't happen
- **LOG BEFORE ACTION** - Add entry before making changes
- **UPDATE AFTER COMPLETION** - Add result after action completes
- **OTHER AGENTS WILL CHECK** - All agents are required to verify logs

## AGENT IDENTIFICATION:

When you first start working on this project:
1. Add your Agent ID to the "AGENT IDs" section in `.kilo/AGENT_ACTIVITY_LOG.md`
2. Log your first action immediately
3. Include your Agent ID in every subsequent log entry

## FAILURE TO COMPLY:

Agents that do not log their actions:
1. Will be flagged in the activity log
2. May have their changes rejected
3. Will be reported to the user

---

**CURRENT TIME**: Use the timestamp from your environment or system clock
**LOG FILE**: `.kilo/AGENT_ACTIVITY_LOG.md`
**THIS FILE**: `.kilo/command/start.md` - READ EVERY TIME
