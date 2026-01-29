# Construction Training Bot - Template Image Requirements

## Overview
Before running the construction training bot, you must create template images for all required items, NPCs, and objects. The bot uses OpenCV template matching to locate these elements on screen.

## How to Create Template Images

1. **In-game setup:**
   - Set your game to Fixed Mode or Resizable with consistent zoom level
   - Ensure RuneLite plugins are configured (see below)
   - Have the required items/objects visible

2. **Screenshot capture:**
   - Use Windows Snipping Tool (Win + Shift + S) or similar
   - Capture ONLY the item/object itself (not surrounding UI)
   - Save as PNG format
   - Crop tightly around the item with minimal extra pixels

3. **File naming:**
   - Use exact names as specified below
   - Save to the correct directory
   - PNG format only

## Required RuneLite Configuration

### NPC Indicators Plugin
Enable and configure NPC highlighting for Phials:
- Plugin: **NPC Indicators**
- Highlight NPC: **Phials**
- Highlight color: **#FFD700** (gold/yellow)
- This color is already configured in `config.json` as `phials_npc_highlight`

---

## Required Templates

### 1. Items (Directory: `src/osrsbot/images/bot/items/`)

#### teleport_to_house.png
- **What to capture:** Teleport to house scroll in your inventory
- **Size:** ~32x32 pixels (inventory item size)
- **Notes:** Ensure full icon is visible, including scroll design

#### plank.png
- **What to capture:** Regular wooden plank (unnoted) in inventory
- **Size:** ~32x32 pixels
- **Notes:** This is the UNNOTED plank (after exchange with Phials)

#### plank_noted.png
- **What to capture:** Noted wooden plank in inventory (has paper icon overlay)
- **Size:** ~32x32 pixels
- **Notes:** This is the NOTED version with the paper stack icon
- **Important:** Must be distinguishable from unnoted plank

#### iron_nails.png
- **What to capture:** Iron nails stack in inventory
- **Size:** ~32x32 pixels
- **Notes:** The nail icon should be clearly visible

#### hammer.png
- **What to capture:** Hammer tool in inventory
- **Size:** ~32x32 pixels
- **Notes:** Standard construction hammer

#### saw.png
- **What to capture:** Saw tool in inventory
- **Size:** ~32x32 pixels
- **Notes:** Standard construction saw

#### coins.png (Optional)
- **What to capture:** Coins stack in inventory
- **Size:** ~32x32 pixels
- **Notes:** Bot can also use color detection for coins

---

### 2. Construction Objects (Directory: `src/osrsbot/images/bot/construction/`)

#### house_portal.png
- **What to capture:** House portal (both inside and outside house)
- **Size:** Variable, ~60x80 pixels typical
- **Notes:**
  - Capture the entire portal archway
  - Should work for both exterior (Rimmington) and interior (inside house)
  - May need to create two separate templates if portals look different

#### chair_hotspot.png
- **What to capture:** Empty chair build space (transparent/ghostly white outline)
- **Size:** Variable, ~40x60 pixels typical
- **Notes:**
  - Capture when hotspot is EMPTY (no chair built)
  - Should show the transparent/ghostly outline
  - This is the build space in parlour room

#### built_chair_crude.png
- **What to capture:** Crude wooden chair (level 1) after building
- **Size:** Variable, ~40x60 pixels typical
- **Notes:**
  - Capture AFTER building (solid brown chair, not transparent)
  - This is the basic wooden chair

#### built_chair_wooden.png
- **What to capture:** Wooden chair (level 8) after building
- **Size:** Variable, ~40x60 pixels typical
- **Notes:**
  - Capture AFTER building (solid chair)
  - Only needed if you have level 8+ Construction

#### built_chair_rocking.png
- **What to capture:** Rocking chair (level 14) after building
- **Size:** Variable, ~40x60 pixels typical
- **Notes:**
  - Capture AFTER building (solid chair)
  - Only needed if you have level 14+ Construction

#### red_cross.png
- **What to capture:** Red X icon on unavailable build options
- **Size:** ~16x16 pixels
- **Notes:**
  - Open construction interface
  - Capture the red X that appears on options you can't build
  - This appears when you don't have the level or materials

---

### 3. Chair Option Templates (Directory: `src/osrsbot/images/bot/construction/`)

These templates are used to click the correct chair type in the construction build interface.

#### chair_option_rocking.png
- **What to capture:** Rocking chair icon in construction interface
- **Size:** ~40x40 pixels
- **Notes:**
  - Right-click ghostly chair → click "Build Chair Space" → construction interface opens
  - Capture the rocking chair icon (rightmost option in chair build menu)
  - Crop tightly around just the chair icon, not the text or background
  - This is the chair icon showing what you will build, not the built chair

#### chair_option_wooden.png
- **What to capture:** Wooden chair icon in construction interface
- **Size:** ~40x40 pixels
- **Notes:**
  - Same process as rocking chair
  - Capture the wooden chair icon (middle option in chair build menu)
  - Only needed if you're below level 14 Construction

#### chair_option_crude.png
- **What to capture:** Crude wooden chair icon in construction interface
- **Size:** ~40x40 pixels
- **Notes:**
  - Same process as rocking chair
  - Capture the crude wooden chair icon (leftmost option in chair build menu)
  - Only needed if you're below level 8 Construction

#### chair_option_rocking_unavailable.png
- **What to capture:** Rocking chair icon WITH red cross overlay (unavailable)
- **Size:** ~40x40 pixels
- **Notes:**
  - When you're out of planks/nails, the chair shows a red cross
  - Capture the entire icon including the red cross overlay
  - Used to detect when materials have run out

#### chair_option_wooden_unavailable.png (Optional)
- **What to capture:** Wooden chair icon WITH red cross overlay (unavailable)
- **Size:** ~40x40 pixels
- **Notes:**
  - Same as rocking unavailable
  - Only needed if you're below level 14 Construction

#### chair_option_crude_unavailable.png (Optional)
- **What to capture:** Crude chair icon WITH red cross overlay (unavailable)
- **Size:** ~40x40 pixels
- **Notes:**
  - Same as rocking unavailable
  - Only needed if you're below level 8 Construction

---

### 4. UI Elements (Directory: `src/osrsbot/images/bot/ui_templates/`)

#### construction_skill_icon.png (Optional)
- **What to capture:** Construction skill popup icon (hammer & saw)
- **Size:** ~24x24 pixels
- **Notes:**
  - This appears in top-right when you gain Construction XP
  - Shows hammer and saw crossed
  - Can also use color detection instead of template

---

## Verification Checklist

Before running the bot, verify you have created:

**Items (7 templates):**
- [ ] teleport_to_house.png
- [ ] plank.png
- [ ] plank_noted.png
- [ ] iron_nails.png
- [ ] hammer.png
- [ ] saw.png
- [ ] coins.png (optional)

**Construction Objects (6 templates):**
- [ ] house_portal.png
- [ ] chair_hotspot.png
- [ ] built_chair_crude.png
- [ ] built_chair_wooden.png (if level 8+)
- [ ] built_chair_rocking.png (if level 14+)
- [ ] red_cross.png

**Chair Option Templates (6 templates):**
- [ ] chair_option_rocking.png (if level 14+)
- [ ] chair_option_wooden.png (if level 8+)
- [ ] chair_option_crude.png
- [ ] chair_option_rocking_unavailable.png (with red cross - for material shortage detection)
- [ ] chair_option_wooden_unavailable.png (optional, with red cross)
- [ ] chair_option_crude_unavailable.png (optional, with red cross)

**UI Elements (1 template):**
- [ ] construction_skill_icon.png (optional)

---

## Troubleshooting

### Template Not Found Errors
- Ensure file names match EXACTLY (case-sensitive)
- Verify file is PNG format
- Check file is in correct directory
- Re-capture template with tighter crop

### Template Matching Fails
- Try different zoom levels in-game
- Ensure lighting/brightness consistent
- Capture template with same game settings as when running bot
- Increase template threshold in code (lower = more lenient)

### NPC Detection Issues (Phials)
- Verify NPC Indicators plugin is enabled in RuneLite
- Check Phials is highlighted with #FFD700 color
- Ensure NPC name is spelled correctly in plugin settings
- Bot will fall back to template matching if color detection fails

---

## Alternative: Color-Based Detection

Some elements can use color detection instead of templates:

1. **Phials NPC:** Configure NPC Indicators plugin (recommended)
2. **Built chair:** Use color change detection (transparent → solid brown)
3. **Dialogue boxes:** Use black background color detection
4. **Coins:** Use gold color detection

These are configured in `config.json` under the `colors` section.

---

## Tips for Best Results

1. **Consistent game settings:**
   - Always use same zoom level
   - Same screen resolution
   - Same RuneLite plugins enabled

2. **Clean captures:**
   - No overlapping UI elements
   - No mouse cursor in screenshot
   - Full item/object visible

3. **Test templates:**
   - Run bot in test mode first
   - Check logs for "template not found" errors
   - Adjust templates as needed

4. **Multiple templates:**
   - Can create multiple templates for same item (different angles/states)
   - Bot supports multi-template matching
   - Useful for objects that change appearance

---

## Need Help?

If you're having trouble creating templates:
1. Check the NMZ bot templates for reference examples
2. Review the template matching documentation
3. Enable DEBUG logging to see template matching confidence scores
4. Test individual templates using the template matching service directly

---

**Last Updated:** 2026-01-24
**Bot Version:** Construction Training v1.0
