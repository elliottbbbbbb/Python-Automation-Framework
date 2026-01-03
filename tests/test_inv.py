import sys
import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

sys.path.insert(0, 'src')

from osrsbot.queries.inventory_queries import InventoryState
from osrsbot.services.screen_service import ScreenService
from osrsbot.services.template_match_service import TemplateMatchService
from osrsbot.models.config import Config

config = Config()
screen = ScreenService()
template = TemplateMatchService()

# Register inventory grid
template.register_grid(
    name="inventory",
    template_path="templates/inventory_grid.png",
    num_rows=7,
    num_cols=4,
    threshold=0.8
)

inv = InventoryState(template, screen, config)

print('\nTesting inventory detection with 5 items in slots 0, 1, 2, 3, 4...\n')
snapshot = inv.get_snapshot(force=True)
print(f'\nRESULTS:')
print(f'Total items detected: {snapshot.total_items}')
print(f'Filled slots: {snapshot.filled_slots}')
print(f'Empty slots (first 10): {snapshot.empty_slots[:10]}')
