# Phase 1 Testing Guide

## Quick Reference

**State Machine Bot:** `GreenDragonsStateMachineBot` (new)
**Original Bot:** `GreenDragonsBot` (unchanged)

Both bots work - you can test side-by-side!

---

## Option 1: Dry Run Test (No Game Required)

Test state machine structure without running the actual bot.

### What to Check:

1. **Import Test** - Verify all files exist:
```python
# Run Python interactive shell in project root
python
>>> from osrsbot.core.state_types import StateResult, StateMetadata
>>> from osrsbot.core.state_machine_bot import StateMachineBot
>>> from osrsbot.scripts.green_dragons_state import GreenDragonsStateMachineBot, GreenDragonsStates
>>> print("✓ All imports successful!")
```

2. **States Check** - Verify 7 states defined:
```python
>>> for state in GreenDragonsStates:
...     print(f"  - {state.name}")
# Should print: IDLE, TELEPORT_TO_DRAGONS, NAVIGATE_TO_SPOT, COMBAT, TELEPORT_TO_BANK, BANKING, RECOVERY
```

3. **State Results Check**:
```python
>>> from osrsbot.core.state_types import StateResult
>>> for result in StateResult:
...     print(f"  - {result.name}: {result.value}")
# Should print: SUCCESS, FAILURE, RETRY, SKIP, TIMEOUT
```

---

## Option 2: Runtime Test (With Game)

### Modify Your Bot Runner

Update your main script (or `app/menu.py`) to use the state machine bot:

```python
# BEFORE (original bot):
from osrsbot.scripts.green_dragons import GreenDragonsBot
bot = GreenDragonsBot(interface, state, actions, config)

# AFTER (state machine bot):
from osrsbot.scripts.green_dragons_state import GreenDragonsStateMachineBot
bot = GreenDragonsStateMachineBot(interface, state, actions, config)

# Run as normal
bot.run(bank_location="varrock", runs=1)  # Start with just 1 run
```

### What to Monitor in Logs

#### 1. **State Machine Initialization**
Look for this in logs:
```
INFO - Initializing state machine for Green Dragons (State Machine)
INFO - State machine initialized: 7 states, 6 transitions, starting at IDLE
```

#### 2. **State Transitions**
Each state execution shows:
```
INFO - Executing state: IDLE (attempt 1/2)
INFO - State IDLE completed: success (duration: 0.01s, retries: 0)
INFO - Transitioning: IDLE → TELEPORT_TO_DRAGONS
```

#### 3. **Retry Logic (on failures)**
If a state fails:
```
INFO - Executing state: BANKING (attempt 1/4)
ERROR - BANKING: Failed - <error message>
INFO - State BANKING completed: failure (duration: 2.3s, retries: 0)
INFO - Retrying state BANKING (attempt 2/4)
```

#### 4. **Failover to Recovery**
If max retries exceeded:
```
WARNING - State BANKING failed after 4 attempts, failing over to RECOVERY
INFO - Transitioning: BANKING → RECOVERY
INFO - RECOVERY: Attempting recovery
```

#### 5. **Timeout Detection**
If state runs too long:
```
WARNING - State COMBAT timed out after 600.0s
INFO - State COMBAT completed: timeout (duration: 600.1s, retries: 0)
```

---

## Option 3: Compare with Original Bot

Run both bots side-by-side to verify same behavior:

### Test 1: One Full Cycle

**Original Bot:**
```python
from osrsbot.scripts.green_dragons import GreenDragonsBot
original_bot = GreenDragonsBot(interface, state, actions, config)
original_bot.run(bank_location="varrock", runs=1)
# Note duration and any issues
```

**State Machine Bot:**
```python
from osrsbot.scripts.green_dragons_state import GreenDragonsStateMachineBot
sm_bot = GreenDragonsStateMachineBot(interface, state, actions, config)
sm_bot.run(bank_location="varrock", runs=1)
# Compare duration and behavior
```

### Expected Results:
- Both should complete successfully
- State machine version has more detailed logs
- Timing should be similar (state machine adds <1s overhead)
- State machine recovers from failures better

---

## Testing Checklist

### ✅ Static Tests (No Game Required)

- [ ] All imports work
- [ ] 7 states defined correctly
- [ ] StateResult enum has 5 values
- [ ] No syntax errors in new files

### ✅ Runtime Tests (With Game)

- [ ] Bot initializes state machine on first cycle
- [ ] IDLE state executes successfully
- [ ] TELEPORT_TO_DRAGONS transitions correctly
- [ ] NAVIGATE_TO_SPOT walks and drinks potions
- [ ] COMBAT kills dragons and monitors HP
- [ ] TELEPORT_TO_BANK teleports successfully
- [ ] BANKING deposits and withdraws food
- [ ] Full cycle completes (IDLE → BANKING)

### ✅ Error Handling Tests

- [ ] **Simulate failure**: Manually cause a failure (e.g., close bank interface)
- [ ] **Verify retry**: Bot should retry up to max_retries
- [ ] **Verify failover**: After max retries, should failover to RECOVERY
- [ ] **Verify recovery**: RECOVERY state should attempt to fix issue

### ✅ State History Tests

After running 1 cycle, check history:

```python
# Add this to your bot script after bot.run():
history = bot.get_state_history()
print(f"\nState History ({len(history)} entries):")
for entry in history:
    print(f"  {entry.state.name}: {entry.result.value} ({entry.duration:.2f}s, retries: {entry.retry_count})")
```

Expected output:
```
State History (7 entries):
  IDLE: success (0.01s, retries: 0)
  TELEPORT_TO_DRAGONS: success (3.2s, retries: 0)
  NAVIGATE_TO_SPOT: success (15.4s, retries: 0)
  COMBAT: success (180.5s, retries: 0)
  TELEPORT_TO_BANK: success (2.1s, retries: 0)
  BANKING: success (12.3s, retries: 0)
```

---

## Common Issues & Solutions

### Issue 1: "State handler '_handle_X' not found"
**Cause:** Handler method missing for state
**Solution:** Check `green_dragons_state.py` has all 7 handlers:
- `_handle_idle`
- `_handle_teleport_to_dragons`
- `_handle_navigate_to_spot`
- `_handle_combat`
- `_handle_teleport_to_bank`
- `_handle_banking`
- `_handle_recovery`

### Issue 2: "State machine exceeded max states (50)"
**Cause:** Infinite loop in state transitions
**Solution:** Check for RETRY without SUCCESS condition

### Issue 3: Import errors
**Cause:** Python path not set correctly
**Solution:**
- Ensure you're running from project root
- Or: `set PYTHONPATH=src` (Windows) / `export PYTHONPATH=src` (Linux)
- Or: Install package in development mode: `pip install -e .`

### Issue 4: "inventory_full() not found"
**Cause:** Using old state.py without Phase 0 changes
**Solution:** Ensure Phase 0 was implemented (inventory_full method added)

---

## Success Criteria (Phase 1)

✅ **State machine completes full cycle**
- All 7 states execute in order
- Returns to idle (or completes banking)

✅ **Retry logic recovers from failures**
- Simulated failure retries up to max_retries
- Different states have different retry limits

✅ **RECOVERY state handles edge cases**
- Max retries triggers failover to RECOVERY
- RECOVERY attempts to escape/reset
- RECOVERY resets to IDLE

✅ **State history tracked correctly**
- Can retrieve last N state executions
- Each entry has: state, result, duration, retry_count
- Timestamps accurate

✅ **Transitions never deadlock**
- No infinite loops
- Max 50 states per cycle enforced
- Clear error messages on issues

---

## Performance Comparison

Expected metrics (one cycle):

| Metric | Original Bot | State Machine Bot |
|--------|-------------|-------------------|
| **Total Duration** | ~200-250s | ~202-253s |
| **Overhead** | 0s | <3s (initialization + tracking) |
| **Failure Recovery** | None | Automatic retries |
| **Debugging Info** | Minimal | Detailed state history |
| **Code Clarity** | Mixed | Explicit states |

---

## Next Steps After Testing

Once Phase 1 tests pass:

1. **Use State Machine Bot** as primary
2. **Monitor for issues** over several runs
3. **Decide on Phase 2**: Injectable RNG + Metrics
   - Adds deterministic testing
   - Session tracking
   - Pattern analysis

4. **Or skip to Phase 3**: Advanced anti-detection
   - Async delays
   - Multi-dimensional pattern detection
   - Statistical realism

---

## Quick Test Command

If package is installed:
```bash
# Run from project root
python -c "from osrsbot.scripts.green_dragons_state import GreenDragonsStates; print('✓ States:', [s.name for s in GreenDragonsStates])"
```

Expected output:
```
✓ States: ['IDLE', 'TELEPORT_TO_DRAGONS', 'NAVIGATE_TO_SPOT', 'COMBAT', 'TELEPORT_TO_BANK', 'BANKING', 'RECOVERY']
```

---

## Support

If you encounter issues:
1. Check logs for detailed error messages
2. Verify Phase 0 is implemented (inventory_full exists)
3. Compare with original bot behavior
4. Check state handler methods are all implemented
5. Review state transitions match expected flow

Good luck testing! 🚀
