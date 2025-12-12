# Legacy Scripts

This directory contains deprecated bot implementations kept for reference purposes.

## Deprecated Files

### `green_dragons.py` - Green Dragons Bot (Legacy)
- **Deprecated**: December 11, 2025
- **Reason**: Replaced by state machine version ([green_dragons_state.py](../green_dragons_state.py))
- **Migration**: Use `GreenDragonsStateMachineBot` instead of `GreenDragonsBot`

### `guns.py` - Guns/Pickpocketing Script (Legacy)
- **Deprecated**: December 11, 2025
- **Reason**: Function-based approach is harder to maintain and test
- **Migration**: Use StateMachineBot framework for new scripts

### `test.py` - Test Bot (Legacy)
- **Deprecated**: December 11, 2025
- **Reason**: Replaced by state machine version ([test_state_machine_bot.py](../test_state_machine_bot.py))
- **Migration**: Use `StateMachineTestBot` for testing

## Why Keep Legacy Code?

These files are preserved for:
1. **Reference**: Understanding the evolution from Bot class to StateMachineBot
2. **Migration**: Helping port remaining function-based scripts
3. **Documentation**: Showing the original implementation approach

## Should You Use These Files?

**No.** These files are deprecated and should not be used in new development.

- ❌ No longer maintained
- ❌ Missing modern features (state machine, retry logic, transition rules)
- ❌ Harder to test and debug

## For New Development

Use the StateMachineBot framework:
- See [state_machine_bot.py](../../core/state_machine_bot.py) for framework
- See [green_dragons_state.py](../green_dragons_state.py) for example
- See [TESTING_STATE_MACHINE_BOT.md](../../../../TESTING_STATE_MACHINE_BOT.md) for testing guide

---

**Removal Timeline**: These files may be permanently deleted after Q1 2026 if no issues arise.
