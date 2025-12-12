# State Machine Test Bot - Quick Guide

## Overview

The State Machine Test Bot is a simple bot designed to validate the Phase 1 state machine framework. It demonstrates all core state machine features by clicking yellow NPCs.

## Features Demonstrated

✅ **State Transitions**: IDLE → CLICK_NPC → COMPLETE
✅ **Retry Logic**: CLICK_NPC state uses RETRY result to keep clicking
✅ **State History**: Tracks all state executions with timing
✅ **Timeout Protection**: 30 second timeout prevents infinite loops
✅ **Failover**: If CLICK_NPC fails, transitions to COMPLETE

## How to Run

### 1. Start the Bot

```bash
python -m osrsbot.app.menu
```

Select option **6. State Machine Test Bot (Click Yellow NPCs)**

### 2. Configure

- **Runs**: Default 1 run (recommended for testing)
- Press Enter to start when ready

### 3. What It Does

The bot will:
1. Start in IDLE state (safety checks)
2. Transition to CLICK_NPC state
3. Click yellow NPCs 5 times total
4. Use RETRY to keep clicking until target reached
5. Transition to COMPLETE state
6. Print state history with timing information

### 4. Expected Output

```
INFO - Initializing state machine for State Machine Test Bot
INFO - State machine initialized: 3 states, 2 transitions, starting at IDLE
INFO - Starting state machine cycle 1
INFO - Executing state: IDLE (attempt 1/2)
INFO - IDLE: Starting test bot
INFO - IDLE: Will click 5 yellow NPCs
INFO - State IDLE completed: success (duration: 0.01s, retries: 0)
INFO - Transitioning: IDLE → CLICK_NPC
INFO - Executing state: CLICK_NPC (attempt 1/11)
INFO - CLICK_NPC: Click 1/5
INFO - CLICK_NPC: Successfully clicked NPC (1/5)
INFO - Executing state: CLICK_NPC (attempt 2/11)
INFO - CLICK_NPC: Click 2/5
...
INFO - CLICK_NPC: Target clicks reached, completing
INFO - State CLICK_NPC completed: success (duration: 12.3s, retries: 4)
INFO - Transitioning: CLICK_NPC → COMPLETE
INFO - Executing state: COMPLETE (attempt 1/2)
INFO - COMPLETE: Test bot finished! Clicked 5 NPCs

State History (7 entries):
  IDLE: success (0.01s, retries: 0)
  CLICK_NPC: retry (2.1s, retries: 0)
  CLICK_NPC: retry (2.3s, retries: 1)
  CLICK_NPC: retry (2.0s, retries: 2)
  CLICK_NPC: retry (2.2s, retries: 3)
  CLICK_NPC: success (2.5s, retries: 4)
  COMPLETE: success (0.01s, retries: 0)
```

## Setup Requirements

### Yellow NPC Configuration

The bot uses `actions.click_color("yellow_npc")` to find NPCs. You need to configure this color in your calibration:

1. Run option **1. Calibrate Colors & Coordinates**
2. Add a color for "yellow_npc" (the yellow highlight when hovering NPCs)
3. Or update your `config.json` manually:

```json
{
  "colors": {
    "yellow_npc": [255, 255, 0]  // RGB for yellow NPC highlight
  }
}
```

**Note**: If yellow_npc color isn't calibrated, the bot will keep retrying until timeout (30s).

## State Machine Features Validated

### ✅ State Definition
- 3 states defined in `TestBotStates` enum
- Each state has metadata (name, description, max_retries, timeout)

### ✅ State Transitions
- Linear flow: IDLE → CLICK_NPC → COMPLETE
- No transitions from COMPLETE (cycle ends)

### ✅ Retry Logic
- CLICK_NPC uses `StateResult.RETRY` to continue clicking
- Max 10 retries configured (11 total attempts)
- Returns `StateResult.SUCCESS` when target reached

### ✅ State History
- Tracks all state executions
- Records: state name, result, duration, retry count
- Printed at end of cycle

### ✅ Timeout Protection
- CLICK_NPC has 30s timeout
- If timeout exceeded, returns `StateResult.TIMEOUT`
- Failover to COMPLETE state on timeout

### ✅ Failover States
- CLICK_NPC failover: COMPLETE (graceful degradation)
- If clicking fails repeatedly, cycle completes instead of crashing

## Troubleshooting

### Issue 1: "No yellow NPC found, retrying..."
**Cause**: Yellow NPC color not calibrated or no NPCs visible
**Solution**:
- Run calibration and add "yellow_npc" color
- Make sure NPCs are visible in-game
- Check your `config.json` has "yellow_npc" entry

### Issue 2: "State CLICK_NPC timed out after 30.0s"
**Cause**: Couldn't find yellow NPCs within timeout
**Solution**:
- Check NPCs are visible
- Verify color calibration is correct
- Bot will gracefully failover to COMPLETE

### Issue 3: Import errors
**Cause**: Python path not set correctly
**Solution**:
- Run from project root: `python -m osrsbot.app.menu`
- Or: Install package in dev mode: `pip install -e .`

## Comparison to Original Bots

| Feature | Original Bot | State Machine Test Bot |
|---------|-------------|------------------------|
| **State Management** | Implicit (loop-based) | Explicit (state machine) |
| **Retry Logic** | Manual | Automatic (per-state) |
| **Timeout Protection** | None | Per-state (30s) |
| **Failover** | Crash on error | Graceful (COMPLETE) |
| **History Tracking** | None | Full history |
| **Debugging** | Minimal logs | Detailed state logs |

## Next Steps

Once this test bot works successfully:

1. ✅ **Phase 1 Validated**: State machine framework is working
2. **Test Green Dragons State Bot**: Try the full implementation
3. **Compare Behavior**: Run original vs state machine bots side-by-side
4. **Move to Phase 2**: Add injectable RNG + metrics

## Code Structure

```python
# States
class TestBotStates(Enum):
    IDLE = "idle"
    CLICK_NPC = "click_npc"
    COMPLETE = "complete"

# State Metadata
{
    IDLE: max_retries=1, timeout=None,
    CLICK_NPC: max_retries=10, timeout=30.0, failover=COMPLETE,
    COMPLETE: max_retries=1, timeout=None
}

# Transitions
IDLE → CLICK_NPC
CLICK_NPC → COMPLETE

# Handlers
_handle_idle() → StateResult.SUCCESS
_handle_click_npc() → StateResult.RETRY or StateResult.SUCCESS
_handle_complete() → StateResult.SUCCESS
```

## Success Criteria

✅ Bot initializes state machine (3 states, 2 transitions)
✅ IDLE state executes and transitions to CLICK_NPC
✅ CLICK_NPC retries until target clicks reached
✅ State history shows all executions
✅ Cycle completes gracefully
✅ No crashes or infinite loops

---

**Ready to test?** Run the menu and select option 6!
