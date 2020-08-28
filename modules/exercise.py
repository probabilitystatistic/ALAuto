import math
import string
from util.logger import Logger
from util.utils import Region, Utils


class ExerciseModule(object):

    def __init__(self, config, stats):

        self.enabled = True
        self.config = config
        self.stats = stats
        self.combats_done = 0
 
        self.region = {
            'battle_handler_safe_touch': Region(40, 180, 110, 110),
            'battle_handler_defeat_close_touch': Region(880, 900, 100, 40),
            'combat_end_confirm': Region(1504, 952, 38, 70), # safe
            'go_to_exercise': Region(1830, 980, 40, 70),
            'menu_button_battle': Region(1517, 442, 209, 206),
            'menu_combat_start': Region(1578, 921, 270, 70),
            'start_exercise': Region(860, 820, 200, 60)
        }

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

        # move to exercise menu
        Utils.wait_update_screen()
        Utils.touch_randomly_ensured(self.region["menu_button_battle"], "", ["menu/attack"], response_time=1, stable_check_frame=1)
        Utils.touch_randomly_ensured(self.region["go_to_exercise"], "", ["menu/exercise"], response_time=1, stable_check_frame=1)

        Logger.log_msg("Threshold for fleet power: {}".format(self.config.exercise["acceptable_fleet_power"]))

        # exercise combat loop
        while True:
            if False:
                print("Placeholder")
            if Utils.find_with_cropped("exercise/zero_turn_left"):
                Logger.log_msg("No more exercise turn left")
                break
            else:
                opponent = self.choose_opponent()
                Utils.touch_ensured(self.opponent[opponent], "", ["exercise/start_exercise"], response_time=1, stable_check_frame=1)
                Utils.touch_randomly_ensured(self.region["start_exercise"], "", ["combat/menu_formation"], response_time=1, stable_check_frame=1)
                self.exercise_battle_handler()

        Utils.menu_navigate("menu/button_battle")
        return

    def choose_opponent(self):
        # for now just choose the first opponent
        return 0

    def exercise_battle_handler(self):
        Logger.log_msg("Starting combat.")

        while not (Utils.find_with_cropped("combat/menu_loading", 0.8)):
            Utils.update_screen()
            if Utils.find_with_cropped("combat/combat_pause", 0.7):
                Logger.log_warning("Loading screen was not found but combat pause is present, assuming combat is initiated normally.")
                break
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
        # no detection for items or ship drop(except new ship inquiring if locking)
        Logger.log_msg("Battle summary")
        response = Utils.touch_randomly_ensured(self.region['battle_handler_safe_touch'], "", 
                                                ["combat/button_confirm"], response_time=0.1, empty_touch=2)

    
        # press the orange "confirm" button at the end of battle summary
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

        # post-summary
        Logger.log_msg("Combat ended.")
        return
