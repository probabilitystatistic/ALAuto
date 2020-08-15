#from util.utils import Region


#class CropRegionModule(object):
""" All regions for cropped search(find_with_cropped) are store here.

"""
#	def __init__(self):
# form: x1, y1, x2, y2
data = {
    "combat/alert_fleet_cannot_be_formed": [500, 400, 1400, 800],
    "combat/alert_lock": [500, 200, 1500, 900], # Just a rough estimation!
    "combat/alert_morale_low": [500, 200, 1500, 900], # Just a rough estimation!
    "combat/alert_unable_battle": [700, 450, 1250, 650], 
    "combat/button_confirm": [1480, 920, 1800, 1080],
    "combat/button_go": [1200, 700, 1800, 980],
    "combat/button_retreat": [1100, 950, 1400, 1080], 
    "combat/combat_pause": [1600, 0, 1920, 150],
    "combat/commander": [100, 250, 1000, 400],
    "combat/defeat_close_button": [750, 850, 1150, 1000],
    "combat/menu_loading": [1560, 960, 1920, 1080],
    "combat/menu_select_fleet": [160, 80, 600, 200],
    "combat/menu_touch2continue": [100, 900, 900, 1000],
    "commission/alert_completed": [1660, 400, 1760, 500],
    "commission/scroll_bar_exist": [1860, 80, 1920, 180],
    "commission/scroll_bar_reaching_end": [1860, 980, 1920, 1080],
    "menu/alert_info": [0, 0, 960, 540], # Just a rough estimation!
    "menu/alert_close": [960, 0, 1920, 540], # Just a rough estimation!
    "menu/attack": [140, 0, 420, 100],
    "menu/build": [100, 0, 350, 100],
    "menu/button_battle": [1500, 420, 1700, 600],
    "menu/button_confirm": [500, 540, 1920, 1080], # Just a rough estimation!
    "menu/button_sort": [500, 700, 800, 850], # This is perhaps the sort button when port is full before starting a combat.
    "menu/drop_common": [1000, 250, 1920, 880], # Just a rough estimation!
    "menu/drop_elite": [1000, 250, 1920, 880], # Just a rough estimation!
    "menu/drop_rare": [1000, 250, 1920, 880], # Just a rough estimation!
    "menu/drop_ssr": [1000, 250, 1920, 880], # Just a rough estimation!
    "menu/item_found": [700, 150, 1200, 400],
    "retirement/alert_bonus": [200, 900, 450, 1050],
    "retirement/bonus": [460, 960, 620, 1060],
    "retirement/button_disassemble": [1050, 800, 1380, 940], # The "confirm" when showing money earned from disassembling equipment.
    "retirement/empty": [50, 450, 650, 650],
    "retirement/no_batch": [300, 400, 1700, 550],
    "retirement/selected_none": [650, 950, 800, 1080],
    "retirement/setting_quick_retire": [350, 180, 700, 280]
}
