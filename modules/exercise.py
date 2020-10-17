import math
import string
from util.ocr import OCR
from util.logger import Logger
from util.utils import Region, Utils
from operator import itemgetter


class ExerciseModule(object):

    def __init__(self, config, stats):

        self.enabled = True
        self.config = config
        self.stats = stats
        self.combats_done = 0
        self.opponent_threshold = self.config.exercise["acceptable_fleet_power"]
        self.raid_without_ticket = False
        self.use_raid_ticket = False
 
        self.region = {
            'battle_handler_safe_touch': Region(40, 180, 110, 110),
            'battle_handler_defeat_close_touch': Region(880, 900, 100, 40),
            'combat_end_confirm': Region(1504, 952, 38, 70), # safe
            'close_info_dialog': Region(1326, 274, 35, 35),
            'fleet_menu_go': Region(1485, 872, 270, 74),
            'raid_essex': Region(910, 390, 70, 70),
            'raid_essex_EX': Region(1650, 250, 50, 50),
            'raid_essex_hard': Region(1650, 410, 50, 50),
            'raid_essex_normal': Region(1650, 580, 50, 50),
            'raid_essex_easy': Region(1650, 750, 50, 50),
            'raid_repeat': Region(1300, 960, 100, 60),
            'raid_with_ticket': Region(1150, 750, 100, 50),
            'raid_without_ticket': Region(700, 750, 100, 50),
            'go_to_exercise': Region(1830, 980, 40, 70),
            'menu_button_battle': Region(1517, 442, 209, 206),
            'menu_combat_start': Region(1578, 921, 270, 70),
            'menu_nav_back': Region(54, 57, 67, 67),
            'start_exercise': Region(860, 820, 200, 60)
        }
        
        self.fleet_power_region = [
            [Region(334, 392, 108, 36), Region(334, 438, 108, 34)],
            [Region(700, 392, 108, 36), Region(700, 438, 108, 34)],
            [Region(1066, 392, 108, 36), Region(1066, 438, 108, 34)],
            [Region(1432, 392, 108, 36), Region(1432, 438, 108, 34)]
        ]
        
        self.opponent = [
            [362, 181],
            [728, 181],
            [1094, 181],
            [1460, 181]
        ]


    def exercise_logic_wrapper(self):
        """Method that fires off the necessary child methods that encapsulates
        the entire action of exercise.

        Returns:
        """


        # beginning of temporary code for essex raid
        # switch on/off essex raid
        if 1:
            oil, gold = Utils.get_oil_and_gold()
            do_easy = False
            do_normal = True
            do_hard = True
            do_EX = False
            do_essex_exercise = [do_easy, do_normal, do_hard, do_EX]
            level_button = [self.region["raid_essex_easy"], self.region["raid_essex_normal"], self.region["raid_essex_hard"], self.region["raid_essex_EX"]]
            # move to the raid menu
            Utils.update_screen()
            Utils.touch_randomly_ensured(self.region["raid_essex"], "", ["menu/special_event"], response_time=1)
            for i in range(4):
                if not do_essex_exercise[i]:
                    continue
                Utils.touch_randomly_ensured(level_button[i], "menu/special_event", ["combat/menu_select_fleet"], response_time=1, check_level_for_ref_before=3)
                Utils.touch_randomly_ensured(self.region["fleet_menu_go"], "", ["combat/menu_formation"], response_time=1)
                while True:
                    if self.stats.combat_done != 0 and self.stats.combat_done % 5 == 0:
                        Logger.log_msg("Combats done in raid: {}".format(self.stats.combat_done))
                    if not self.daily_battle_handler(mode = 'raid'):
                        break
                    self.stats.increment_combat_done()
            Utils.menu_navigate()
            oil_delta, gold_delta = Utils.get_oil_and_gold()
            self.stats.read_oil_and_gold_change_from_battle(oil_delta - oil, gold_delta - gold)
            Logger.log_warning('End of Essex raid.')
        # end of temporary code for essex raid


        # move to exercise menu
        Utils.wait_update_screen()
        Utils.touch_randomly_ensured(self.region["menu_button_battle"], "", ["menu/attack"], response_time=1, stable_check_frame=1)
        Utils.touch_randomly_ensured(self.region["go_to_exercise"], "", ["menu/exercise"], response_time=1, stable_check_frame=1)

        Logger.log_msg("Threshold for fleet power: {}".format(self.opponent_threshold))

        # exercise combat loop
        while True:
            if Utils.find_with_cropped("exercise/zero_turn_left", similarity=0.99):
                Logger.log_msg("No more exercise turn left")
                break
            else:
                opponent = self.choose_opponent()
                Utils.touch_ensured(self.opponent[opponent], "", ["exercise/start_exercise"], response_time=1, stable_check_frame=1)
                Utils.touch_randomly_ensured(self.region["start_exercise"], "", ["combat/menu_formation"], response_time=1, stable_check_frame=1)
                self.daily_battle_handler(mode = 'exercise')

        Utils.menu_navigate("menu/button_battle")
        return

    def choose_opponent(self):
        # for now just choose the first opponent
        average_power_previous_opponent = 0
        power = []
        chosen = -1
        for i in range(4):
            # poor OCR accuracy
            """
            try:
                main = int(OCR.screen_to_string(self.fleet_power_region[i][0], language="number"))
            except:
                Logger.log_warning("OCR for {}th opponent's main failed.".format(i+1))
                main = 99999
            try:
                vanguard = int(OCR.screen_to_string(self.fleet_power_region[i][1], language="number"))
            except:
                Logger.log_warning("OCR for {}th opponent's vanguard failed.".format(i+1))
                vanguard = 99999
            """
            main = int(OCR.screen_to_string_by_OCRspace(self.fleet_power_region[i][0], mode="number"))
            vanguard = int(OCR.screen_to_string_by_OCRspace(self.fleet_power_region[i][1], mode="number"))

            # not working, but can still roughly give number of digits
            #main = Utils.read_numbers(self.fleet_power_region[i][0].x, self.fleet_power_region[i][0].y, self.fleet_power_region[i][0].w, self.fleet_power_region[i][0].h)
            #vanguard = Utils.read_numbers(self.fleet_power_region[i][1].x, self.fleet_power_region[i][1].y, self.fleet_power_region[i][1].w, self.fleet_power_region[i][1].h)
            power.append([main, vanguard])
            if main <= self.opponent_threshold and vanguard <= self.opponent_threshold:
                if (main + vanguard)/2 >= average_power_previous_opponent:
                    chosen = i
                average_power_previous_opponent = (main + vanguard)/2
            #Logger.log_msg("Opponent {}: {}, {}".format(i + 1, power[i][0], power[i][1]))

        candidate = [power[0][0], power[1][0], power[2][0], power[3][0]]
        Logger.log_msg("Opponents' power")
        Logger.log_msg("[{}, {}]; [{}, {}]; [{}, {}]; [{}, {}]".format(power[0][0], power[0][1], 
                                                                       power[1][0], power[1][1],
                                                                       power[2][0], power[2][1],
                                                                       power[3][0], power[3][1]))
        if chosen == -1:
            chosen = min(enumerate(candidate), key=itemgetter(1))[0] 
        Logger.log_msg("Opponent chosen: {}".format(chosen+1))
        return chosen

    def daily_battle_handler(self, mode = 'exercise'):
        """
        return True if fight is carried out, False otherwise.
        """
        Logger.log_msg("Starting combat.")

        while not (Utils.find_with_cropped("combat/menu_loading", 0.8)):
            Utils.update_screen()
            if Utils.find_with_cropped("combat/combat_pause", 0.7):
                Logger.log_warning("Loading screen was not found but combat pause is present, assuming combat is initiated normally.")
                break
            else:
                if mode == 'raid' and Utils.find_with_cropped("event/raid_ticket"):
                    # note that at least one ticket is needed for triggering the stopping condition for a difficulty raid
                    if self.use_raid_ticket:
                        Utils.touch_randomly(self.region['raid_with_ticket'])
                        Utils.script_sleep(1)
                    elif self.raid_without_ticket:
                        Utils.touch_randomly(self.region['raid_without_ticket'])
                        Utils.script_sleep(1)
                    else:
                        Utils.touch_randomly(self.region['close_info_dialog'])
                        # note that if quit from repeating only one touch is needed for going back to raid menu, but two touches if not quit from repeating.
                        Utils.touch_randomly_ensured(self.region['menu_nav_back'], "", ["menu/special_event"], response_time=1, stable_check_frame=1)
                        Logger.log_warning('No more free rounds.')
                        Utils.update_screen()
                        return False
                else:
                    Utils.touch_randomly(self.region["menu_combat_start"])
                    Utils.script_sleep(1)

        Utils.script_sleep(4)

        defeat = False
        # in battle or not
        while True:
            Utils.update_screen()
            if Utils.find_with_cropped("combat/combat_pause", 0.7):
                Logger.log_debug("In battle.")
            else:
                if Utils.find_with_cropped("combat/menu_touch2continue"):
                    Logger.log_debug("Battle finished.")
                    break
            Utils.script_sleep(1)

        # battle summary
        # this will keep clicking the screen until the end of battle summary(where the orange "confirm" button resides) or lock screen for new ships.
        # 1 empty touch for going from "touch2continue" to item obtained screen
        # no detection for items or ship drop
        Logger.log_msg("Battle summary")
        response = Utils.touch_randomly_ensured(self.region['battle_handler_safe_touch'], "", 
                                                ["combat/button_confirm"], response_time=0.1)

    
        # press the orange "confirm" button at the end of battle summary
        if mode == 'exercise':
            response = Utils.touch_randomly_ensured(self.region["combat_end_confirm"], "", 
                                                    ["menu/exercise", "combat/defeat_close_button"], 
                                                    response_time=2, similarity_after=0.9,
                                                    stable_check_frame=1)
            if response == 2:
                defeat = True
                Logger.log_warning("Fleet was defeated.")
                response = Utils.touch_randomly_ensured(self.region["battle_handler_defeat_close_touch"], "", 
                                                        ["menu/exercise"], 
                                                        response_time=2, stable_check_frame=1)
        
        elif mode == 'raid':
            # no detection of defeat
            response = Utils.touch_randomly_ensured(self.region["raid_repeat"], "", 
                                                    ["combat/menu_formation"], 
                                                    response_time=2, similarity_after=0.9,
                                                    stable_check_frame=1) 
        
        # post-summary
        Logger.log_msg("Combat ended.")
        return True
