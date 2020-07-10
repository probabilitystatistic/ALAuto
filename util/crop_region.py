#from util.utils import Region


#class CropRegionModule(object):
""" All regions for cropped search(find_with_cropped) are store here.

"""
#	def __init__(self):
# form: x1, y1, x2, y2
data = {
    "menu/alert_info": [0, 0, 960, 540], # Just a rough estimation!
	"menu/build": [100, 0, 350, 100],
    "menu/button_battle": [1500, 420, 1700, 600],
    "menu/button_sort": [500, 700, 800, 850], # This is perhaps the sort button when port is full before starting a combat.
    "menu/item_found": [700, 100, 1200, 550],
    "commission/alert_completed": [1660, 400, 1760, 500],
    "retirement/alert_bonus": [200, 900, 450, 1050],
    "retirement/bonus": [460, 960, 620, 1060],
    "retirement/button_disassemble": [1050, 800, 1380, 940], # The "confirm" when showing money earned from disassembling equipment.
    "retirement/empty": [50, 450, 650, 650],
    "retirement/no_batch": [300, 400, 1700, 550],
    "retirement/selected_none": [650, 950, 800, 1080]
}
