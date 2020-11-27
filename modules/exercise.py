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
            'choose_current_daily_raid': Region(900, 500, 100, 100),
            'combat_end_confirm': Region(1504, 952, 38, 70), # safe
            'combat_automation': Region(20, 50, 200, 35),
            'close_info_dialog': Region(1326, 274, 35, 35),
            'daily_raid_left_arrow': Region(40, 510, 40, 60), 
            'daily_raid_right_arrow': Region(1840, 510, 30, 60), 
            'daily_raid_top_mission': Region(750, 250, 100, 100),
            'daily_raid_middle_mission': Region(750, 500, 100, 100),
            'daily_raid_bottom_mission': Region(750, 750, 100, 100),
            'fleet_menu_go': Region(1485, 872, 270, 74),
            'formation_menu_left_arrow': Region(50, 490, 20, 30),
            'formation_menu_right_arrow': Region(1356, 490, 24, 30),
            'raid_essex': Region(910, 390, 70, 70),
            'raid_essex_EX': Region(1650, 250, 50, 50),
            'raid_essex_hard': Region(1650, 410, 50, 50),
            'raid_essex_normal': Region(1650, 580, 50, 50),
            'raid_essex_easy': Region(1650, 750, 50, 50),
            'raid_repeat': Region(1300, 960, 100, 60),
            'raid_with_ticket': Region(1150, 750, 100, 50),
            'raid_without_ticket': Region(700, 750, 100, 50),
            'go_to_exercise': Region(1830, 980, 40, 70),
            'go_to_daily_raid': Region(1140, 980, 160, 60),
            'menu_button_battle': Region(1517, 442, 209, 206),
            'menu_combat_start': Region(1578, 921, 270, 70),
            'menu_nav_back': Region(54, 57, 67, 67),
            'start_exercise': Region(860, 820, 200, 60)
        }
        
        self.fleet_power_region = [
            [Region(334, 382, 138, 56), Region(334, 428, 138, 54)],
            [Region(700, 382, 138, 56), Region(700, 428, 138, 54)],
            [Region(1066, 382, 138, 56), Region(1066, 428, 138, 54)],
            [Region(1432, 382, 138, 56), Region(1432, 428, 138, 54)]
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
        if 0:
            oil, gold = Utils.get_oil_and_gold()
            do_easy = False
            do_normal = False
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

        
        #
        # beginning of temporary code for running daily raid
        #
        # move to daily raid menu
        Logger.log_msg("Starting daily raid run.")
        Utils.wait_update_screen()
        Utils.touch_randomly_ensured(self.region["menu_button_battle"], "", ["menu/attack"], response_time=1, stable_check_frame=1)
        Utils.touch_randomly_ensured(self.region["go_to_daily_raid"], "", ["menu/daily_raid"], response_time=1, stable_check_frame=1)

        selected_daily_raid = None
        fleet_chosen = 6
        mind_core_done = False
        techbox_done = False
        skillbook_done = False
        material_done = False
        count = 0
        while not (mind_core_done and techbox_done and skillbook_done and material_done):
            Utils.update_screen()
            count += 1
            if count >= 100:
                Logger.log_error("Too many loops in daily raid. Quitting...")
                break
            # find a daily raid
            if Utils.find_with_cropped("daily_raid/closed", similarity=0.9) or Utils.find_with_cropped("daily_raid/zero_ticket", similarity=0.9) or Utils.find_with_cropped("daily_raid/torpedo", similarity=0.9):
                if Utils.find_with_cropped("daily_raid/mind_core", similarity=0.9):
                    Logger.log_msg("Daily raid: cognitive chips closed or done")
                    mind_core_done = True
                if Utils.find_with_cropped("daily_raid/techbox", similarity=0.9):
                    Logger.log_msg("Daily raid: techbox closed or done")
                    techbox_done = True
                if Utils.find_with_cropped("daily_raid/skillbook", similarity=0.9):
                    Logger.log_msg("Daily raid: skillbook closed or done")
                    skillbook_done = True
                if Utils.find_with_cropped("daily_raid/material", similarity=0.9):
                    Logger.log_msg("Daily raid: material closed or done")
                    material_done = True
                Utils.touch_randomly(self.region["daily_raid_right_arrow"])
                Utils.script_sleep(0.5)
                continue
            if Utils.find_with_cropped("daily_raid/mind_core", similarity=0.9):
                selected_daily_raid = "mind_core"
                fleet_chosen = 5
                Logger.log_msg("Run for cognitive chips using fleet {}.".format(fleet_chosen))
            if Utils.find_with_cropped("daily_raid/techbox", similarity=0.9):
                selected_daily_raid = "techbox"
                fleet_chosen = 6
                Logger.log_msg("Run for techboxes using fleet {}.".format(fleet_chosen))
            if Utils.find_with_cropped("daily_raid/skillbook", similarity=0.9):
                selected_daily_raid = "skillbook"
                fleet_chosen = 6
                Logger.log_msg("Run for skillbooks using fleet {}.".format(fleet_chosen))
            if Utils.find_with_cropped("daily_raid/material", similarity=0.9):
                selected_daily_raid = "material"
                fleet_chosen = 5
                Logger.log_msg("Run for materials using fleet {}.".format(fleet_chosen))
            # enter the chosen daily raid
            if selected_daily_raid:
                Utils.touch_randomly_ensured(self.region["choose_current_daily_raid"], "", ["daily_raid/gold"], response_time=1, stable_check_frame=1)
                # run the daily raid at most 3 times(even if defeated and tickets available)
                for j in range(3):
                    if Utils.find_with_cropped("daily_raid/zero_ticket_green", similarity=0.95, print_info=True):
                        Utils.touch_randomly(self.region['menu_nav_back'])
                        Utils.script_sleep(1)
                        break
                    # choose the mission of the daily raid
                    Utils.touch_randomly_ensured(self.region["daily_raid_top_mission"], "daily_raid/gold", ["combat/menu_formation"], response_time=1, stable_check_frame=1)
                    self.daily_battle_handler(mode='daily_raid', use_this_fleet=fleet_chosen)
                
        Logger.log_success("All daily raids are completed.")
        Utils.menu_navigate("menu/button_battle")
        #
        # end of temporary code for running daily raid
        #
        



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
            # screen_to_string has poor OCR accuracy
            try:
                #main = int(OCR.screen_to_string(self.fleet_power_region[i][0], language="number", mode="exercise"))
                main = int(OCR.screen_to_string_by_OCRspace(self.fleet_power_region[i][0], mode="number"))
            except:
                Logger.log_warning("OCR for {}th opponent's main failed.".format(i+1))
                main = 99999
            try:
                #vanguard = int(OCR.screen_to_string(self.fleet_power_region[i][1], language="number", mode="exercise"))
                vanguard = int(OCR.screen_to_string_by_OCRspace(self.fleet_power_region[i][1], mode="number"))
            except:
                Logger.log_warning("OCR for {}th opponent's vanguard failed.".format(i+1))
                vanguard = 99999

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

    def daily_battle_handler(self, mode = 'exercise', use_this_fleet = None):
        """
        return True if fight is carried out, False otherwise.
        """
        Utils.update_screen()
        Utils.find_and_touch("combat/auto_combat_off")
        # set fleet if necessary
        if use_this_fleet:
            count = 0
            while not Utils.find_with_cropped("combat/fleet{}".format(use_this_fleet)):
                for i in range(6):
                    if Utils.find_with_cropped("combat/fleet{}".format(i+1)):
                        current_fleet = i + 1
                        Logger.log_msg('Current fleet: {}'.format(current_fleet))
                        break
                step = use_this_fleet - current_fleet
                for j in range(abs(step)):
                    if step > 0:
                        Utils.touch_randomly(self.region["formation_menu_right_arrow"])
                    else:
                        Utils.touch_randomly(self.region["formation_menu_left_arrow"])
                Utils.wait_update_screen()
                count += 1
                if count >= 10:
                    Logger.log_error("Too many loops in setting fleet in combat formulation menu. Terminating...")
                    exit()
            Logger.log_msg('Fleet {} set.'.format(use_this_fleet))

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
                #elif Utils.find_with_cropped("menu/alert_close"):
                else:
                    Utils.touch_randomly(self.region["menu_combat_start"])
                    Utils.script_sleep(1)

        Utils.script_sleep(4)

        defeat = False
        automation_corrected = False
        # in battle or not
        while True:
            Utils.update_screen()
            if Utils.find_with_cropped("combat/combat_pause", 0.7):
                Logger.log_debug("In battle.")
            else:
                if Utils.find_with_cropped("combat/menu_touch2continue"):
                    Logger.log_debug("Battle finished.")
                    break
            if not automation_corrected and Utils.find_with_cropped("combat/automation_disengage", similarity=0.9):
                Utils.touch_randomly(self.region['combat_automation'])
                automation_corrected = True
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

        elif mode == 'daily_raid':
            response = Utils.touch_randomly_ensured(self.region["combat_end_confirm"], "", 
                                                    ["menu/daily_raid", "combat/defeat_close_button"], 
                                                    response_time=2, similarity_after=0.9,
                                                    stable_check_frame=1)
            if response == 2:
                defeat = True
                Logger.log_warning("Fleet was defeated.")
                response = Utils.touch_randomly_ensured(self.region["battle_handler_defeat_close_touch"], "", 
                                                        ["menu/daily_raid"], 
                                                        response_time=2, stable_check_frame=1)
        
        
        # post-summary
        Logger.log_msg("Combat ended.")
        return True
