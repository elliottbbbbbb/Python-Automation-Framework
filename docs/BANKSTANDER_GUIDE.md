# Bankstander Script Guide

Quick reference for creating new bankstander scripts using all reusable components.

## Base Bot Features

Enable these features in your bot's `__init__`:

```python
super().__init__(
    *args,
    **kwargs,
    script_name="My Bot Name",
    enable_exit_key=True,      # Enables 'q' key to exit
    enable_status_ui=True,     # Enables status line updates
)
```

### Available Base Methods:

1. **`self._check_exit_requested()`** - Check if user pressed 'q', raises KeyboardInterrupt if true
2. **`self._update_ui(state, action)`** - Update status line (e.g., "[BANKING] Withdrawing items...")

---

## GameActions Banking Methods

All these methods are available in `self.actions`:

### 1. Bank Search and Withdraw (NEW!)

```python
success = self.actions.bank_search_and_withdraw(
    search_button_template=path_to_search_button,
    item_template=path_to_item,
    item_name="item name",
    search_text="search text",
    item_threshold=0.75
)
```

**What it does:**
- Clicks bank search button
- Types search text
- Waits for results
- Clicks item
- Clears search
- All in one convenient method!

**Example:**
```python
success = self.actions.bank_search_and_withdraw(
    search_button_template=self._bank_search_template,
    item_template=self._item_template,
    item_name="grimy toadflax",
    search_text="toadflax",
    item_threshold=0.75
)
```

---

### 2. Check if Bank is Open

```python
is_open = self.actions.is_bank_open(search_button_template_path)
```

**Parameters:**
- `search_button_template_path`: Path to bank search button template image

**Returns:** `True` if bank is open, `False` otherwise

**Example:**
```python
if not self.actions.is_bank_open(self._bank_search_template):
    # Bank is closed, need to open it
    self.actions.find_and_click_multi_template(banker_templates, "banker")
```

---

### 3. Find and Click Using Single Template

```python
success = self.actions.find_and_click_template(template_path, item_name, threshold=0.7)
```

**Parameters:**
- `template_path`: Path to template image file
- `item_name`: Name for logging (e.g., "grimy toadflax")
- `threshold`: Confidence threshold 0.0-1.0 (default: 0.7)

**Returns:** `True` if found and clicked, `False` otherwise

**Example:**
```python
# Click bank search button
if self.actions.click_template(
    self._bank_search_template,
    "bank search button",
    threshold=0.7
):
    print("Search button clicked!")
```

---

### 4. Find and Click Using Multiple Templates (Best Match)

```python
success = self.actions.find_and_click_multi_template(template_paths, item_name, threshold=0.7)
```

**Parameters:**
- `template_paths`: List of template image paths
- `item_name`: Name for logging
- `threshold`: Confidence threshold 0.0-1.0 (default: 0.7)

**Returns:** `True` if found and clicked, `False` otherwise

**Use this when:**
- Item appears differently at different zoom levels
- Multiple camera angles possible
- Want best accuracy across conditions

**Example:**
```python
# Multiple banker templates for different zoom levels
banker_templates = [
    "images/bot/bank/banker_1.PNG",
    "images/bot/bank/banker_2.PNG",
    "images/bot/bank/banker_zoomed_out.PNG",
]

if self.actions.find_and_click_multi_template(
    banker_templates,
    "banker",
    threshold=0.7
):
    print("Banker clicked!")
```

---

## Complete Bankstander Example

```python
from pathlib import Path
from osrsbot.core.state_machine_bot import StateMachineBot

class MyBankstanderBot(StateMachineBot):
    def __init__(self, *args, **kwargs):
        # Enable exit key ('q') and status UI
        super().__init__(
            *args,
            **kwargs,
            script_name="My Bankstander",
            enable_exit_key=True,
            enable_status_ui=True,
        )

        # Setup template paths
        images_dir = Path(__file__).parent.parent / "images" / "bot"
        bank_dir = images_dir / "bank"
        items_dir = images_dir / "items"

        self._bank_search_template = str(bank_dir / "bank_search_button.PNG")
        self._banker_templates = [
            str(bank_dir / "banker_1.PNG"),
            str(bank_dir / "banker_2.PNG"),
        ]
        self._my_item_template = str(items_dir / "my_item.PNG")

        self._bank_open = False

    def _handle_banking(self, context):
        # Check for exit request
        self._check_exit_requested()

        # Update status UI
        self._update_ui("BANKING", "Opening bank...")

        actions = self.actions

        # Check if bank is open
        if not actions.is_bank_open(self._bank_search_template):
            # Click banker to open bank
            if not actions.find_and_click_multi_template(
                self._banker_templates, "banker", threshold=0.7
            ):
                return StateResult.FAILURE

            actions.wait("long")
            self._bank_open = True

        # Use the new all-in-one bank search and withdraw method!
        self._update_ui("BANKING", "Withdrawing items...")
        if not actions.bank_search_and_withdraw(
            search_button_template=self._bank_search_template,
            item_template=self._my_item_template,
            item_name="my item",
            search_text="my item name",
            item_threshold=0.75,
        ):
            return StateResult.FAILURE

        return StateResult.SUCCESS
```

---

## Template Image Tips

1. **Capture templates at normal zoom/angle** you'll be using
2. **Multiple templates recommended for:**
   - Bankers (different zoom levels)
   - Items that change appearance
   - Anything affected by camera angle

3. **Single template is fine for:**
   - UI elements (search button, deposit buttons)
   - Items that look consistent
   - Small, distinct items

4. **Threshold Guidelines:**
   - UI elements: 0.7 - 0.8
   - Items in bank: 0.65 - 0.75
   - NPCs/Bankers: 0.6 - 0.7
   - Lower = more lenient, Higher = more strict

---

## Common Patterns

### Opening Bank
```python
if not self.actions.is_bank_open(self._bank_search_template):
    self.actions.find_and_click_multi_template(
        self._banker_templates, "banker"
    )
    self.actions.wait("long")
```

### Withdrawing Item with Search
```python
# Click search
self.actions.find_and_click_template(
    self._bank_search_template, "search button"
)
self.actions.wait("short")

# Type item name
import pyautogui
pyautogui.write("item name", interval=0.05)
self.actions.wait("long")

# Click item
self.actions.find_and_click_template(
    self._item_template, "item name", threshold=0.75
)

# Clear search
pyautogui.press("escape")
```

### Depositing
```python
if not self.actions.is_bank_open(self._bank_search_template):
    # Reopen bank
    self.actions.find_and_click_multi_template(
        self._banker_templates, "banker"
    )
    self.actions.wait("long")

# Deposit all
self.actions.bank_deposit_all()
```

---

## See Full Example

Check `src/osrsbot/scripts/bankstander_flax.py` for a complete working example.
