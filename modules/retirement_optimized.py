from util.logger import Logger
from util.utils import Utils, Region
from datetime import datetime, timedelta
import util.crop_region as cr


class RetirementModule(object):

    def __init__(self, config, stats):
        """Initializes the Retirement module.

        Args:
            config (Config): ALAuto Config instance
            stats (Stats): ALAuto stats instance
        """
        self.config = config
        self.stats = stats
        self.sorted = False
        self.build_menu_sorted = False
        self.combat_sorted = False
        self.called_from_menu = False
        self.retirement_done = False
        self.previous_call_place = "combat"
        self.last_retire = 0
        self.forced_quit = False
        self.sleep_time_long = 0.0 # default = 1
        self.sleep_time_short = 0.0 # default =0.5
        self.region = {
            'combat_sort_button': Region(550, 750, 215, 64),
            'build_menu': Region(1452, 1030, 198, 29), # y should be over 1030 to avoid mistakingly touching "start building" button
            'retire_tab_1': Region(20, 661, 115, 60), # y should be below 730 to avoid mistakingly touching batch setting button
            # retire_tab_2 is used when there is wishing well
            'retire_tab_2': Region(30, 816, 94, 94), # should be modified to avoid touching batch setting button
            'menu_nav_back': Region(54, 57, 67, 67),
            'sort_filters_button': Region(1655, 14, 130, 51),
            'rarity_all_ship_filter': Region(435, 668, 190, 45),
            'common_ship_filter': Region(671, 668, 190, 45),
            'rare_ship_filter': Region(907, 668, 190, 45),
            'extra_all_ship_filter': Region(435, 779, 190, 45),
            'confirm_filter_button': Region(1090, 933, 220, 60),
            'confirm_selected_ships_button': Region(1551, 951, 43, 55), # x should be in 951~1006 to avoid mistakingly touching the "cancel" and "confirm" buttons in dock menu
            'confirm_selected_equipment_button': Region(1380, 785, 172, 62), # x >= 1380 to avoid mistakingly touching the "confirm" button after disassemble the equipments
            'disassemble_button': Region(1099, 827, 225, 58),
            'button_batch_retire': Region(960, 965, 100, 80) # x should be below 1060 to avoid mistakingly touch the cancel button after touching this button
        }

    def retirement_logic_wrapper(self, forced=False):
        """Method that fires off the necessary child methods that encapsulates
        the entire action of filtering and retiring ships

        Args:
            forced (bool): Forces retirement to start even if need_to_retire returns False.

        Returns:
            retirement_done (bool): whether at least one retirement was completed.
        """

        if self.need_to_retire or forced:
            self.last_retire = self.stats.combat_done
            self.called_from_menu = False
            self.retirement_done = False
            
            Utils.update_screen()

            in_dock =False

            # entering dock menu
            Logger.log_msg("Navigate to dock menu to retire ships.")
            loop = 0
            while True:
                # called from battle(the "combat/menu_formation" screen)           
                if Utils.find_with_cropped("menu/button_sort"):
                    Logger.log_debug("Retirement called from combat.")
                    response = Utils.touch_randomly_ensured(self.region['combat_sort_button'], "menu/button_sort", ["menu/dock"] ,
                                                            check_level_for_ref_before=4, response_time=0.5, 
                                                            stable_check_frame=1, stable_check_region=cr.data["menu/dock"])
                    if response != 0:
                        in_dock = True
                        break
                # called from main menu
                if Utils.find_with_cropped("menu/button_battle"):
                    Logger.log_debug("Retirement called from main menu.")
                    self.called_from_menu = True
                    oil, gold = Utils.get_oil_and_gold()
                    Utils.touch_randomly_ensured(self.region['build_menu'], "menu/button_battle", ["menu/build"], response_time=0.5, stable_check_frame=1)
                    # to build menu
                    response = Utils.touch_randomly_ensured(self.region['build_menu'], "", ["menu/build"])
                    # to dock menu
                    if response != 0:
                        if Utils.find_with_cropped("event/build_limited"):
                            response = Utils.touch_randomly_ensured(self.region['retire_tab_2'], "menu/build", ["menu/dock"], 
                                                                    check_level_for_ref_before=4, response_time=0.5, 
                                                                    stable_check_frame=1, stable_check_region=cr.data["menu/dock"])
                        else:
                            response = Utils.touch_randomly_ensured(self.region['retire_tab_1'], "", ["menu/dock"])
                        if response != 0:
                            in_dock = True
                            break
                loop += 1
                if loop > 10:
                    Logger.log_error("Fail to enter dock menu. Pretend the retirement is completed to continue automation.") 
                    self.retirement_done = True
                    if not self.called_from_menu:
                        Logger.log_exit("This failed retirement is called from combat. Terminating bot...")
                    break

            # setting the ship filter
            if in_dock:
                self.set_sort()

            # starting the retirement
            Utils.update_screen()
            loop = 0
            while in_dock:
                # select ships by batch retirement
                Logger.log_debug("Select ships by batch.")
                response = Utils.touch_randomly_ensured(self.region['button_batch_retire'], "menu/dock", ["retirement/no_batch", "retirement/alert_bonus"], 
                                                        similarity_after=0.9, check_level_for_ref_before=1)
                # no ships left for retirement
                if response == 1:
                    Logger.log_msg("No ship left to retire.")
                    self.retirement_done = True
                    break
                # ship found for retirement
                if response == 2:
                    # retire the ships already selected by batch
                    Logger.log_msg("Retire selected ships.")
                    self.handle_retirement()
                loop += 1
                if loop > 10:
                    Logger.log_error("Too many loops in starting retirement. Pretend it is completed to continue automation.") 
                    self.retirement_done = True
                    break

            # going back to the place calling retirement
            if self.called_from_menu:
                self.previous_call_place = "menu"
                Logger.log_msg("Go back to main menu.")
                Utils.menu_navigate("menu/button_battle")
                oil_delta, gold_delta = Utils.get_oil_and_gold()
                self.stats.read_oil_and_gold_change_from_retirement(oil_delta - oil, gold_delta - gold)
            else:
                self.previous_call_place = "combat"
                Logger.log_msg("Go back to combat.")
                Utils.touch_randomly(self.region['menu_nav_back'], sleep=2)
            return self.retirement_done
            Utils.update_screen()

    def set_sort(self):
        """Method which sets the correct filters for retirement.
        """
        if self.config.enhancement['enabled'] and (self.previous_call_place == "combat" or not self.called_from_menu):
            # Reset self.sorted if the request to retire came from combat
            # this time or the previous time. The check is necessary because
            # the filters for enhancement and retirement in combat are shared.
            # If the alert "dock is full" is encountered, the retirement 
            # module is called only if the enhancement module fails
            # (e.g. no common ships unlocked in dock).
            self.sorted = False
        if not self.build_menu_sorted and self.called_from_menu:
            # addressing case of only retirement module enabled and first place
            # it's called from is combat: self.sorted is set to true, but the filters
            # enabled when accessing from menu are separated from the ones in combat,
            # so they are not set. self.build_menu_sorted flag ensures that
            # the sorting procedure is done at least once when accessing to
            # retirement from main menu.
            self.build_menu_sorted = True
            self.sorted = False
        if not self.combat_sorted and not self.called_from_menu:
            # addressing case of only retirement module enabled and first place
            # it's called from is main menu: self.sorted is set to true, but the filters
            # enabled when accessing from combat are separated from the ones in menu,
            # so they are not set. self.combat_sorted flag ensures that
            # the sorting procedure is done at least once when accessing to
            # retirement from combat.
            self.combat_sorted = True
            self.sorted = False
        Logger.log_debug("Retirement: " + repr(self.config.retirement))
        while not self.sorted:
            Logger.log_msg("Set ship filter.")
            Utils.touch_randomly(self.region['sort_filters_button'], sleep=0.5)
            Utils.touch_randomly(self.region['rarity_all_ship_filter'], sleep=0.1)
            Utils.touch_randomly(self.region['extra_all_ship_filter'], sleep=0.1)
            if self.config.retirement['commons']:
                Utils.touch_randomly(self.region['common_ship_filter'], sleep=0.1)
            if self.config.retirement['rares']:
                Utils.touch_randomly(self.region['rare_ship_filter'], sleep=0.1)    
            self.sorted = True
            Utils.touch_randomly(self.region['confirm_filter_button'], sleep=0.5)
            
    def handle_retirement(self):
        # now in the selected ship screen after clicking the batch button

        # at least two click here to go from retirement/alert_bonus screen to equipment-selection screen so no check before click is set
        Utils.touch_randomly_ensured(self.region['confirm_selected_ships_button'], "", ["menu/alert_info"], 
                                     response_time=0.1)
        # at euqipment selection screen
        Utils.touch_randomly_ensured(self.region['confirm_selected_equipment_button'], "", ["retirement/button_disassemble"], 
                                             response_time=0.1)
        # at least two click here to go from money-earned screen to dock menu so no check before click is set
        Utils.touch_randomly_ensured(self.region['disassemble_button'], "", ["menu/dock"], 
                                             response_time=0.1)

    @property
    def need_to_retire(self):
        """Checks whether the script needs to retire ships

        Returns:
            bool: True if the script needs to retire ships
        """
        # check if it has already retired with current combat count so it doesn't enter a loop
        if self.config.combat['enabled'] and self.stats.combat_done > self.last_retire:
            return self.stats.combat_done % self.config.combat['retire_cycle'] == 0
        else:
            return False
