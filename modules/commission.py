import copy
from util.utils import Region, Utils
from util.logger import Logger
from util.stats import Stats
from util.config import Config


class CommissionModule(object):

    def __init__(self, config, stats):
        """Initializes the Expedition module.

        Args:
            config (Config): ALAuto Config instance
            stats (Stats): ALAuto stats instance
        """
        self.enabled = True
        self.config = config
        self.stats = stats
        self.attempts_count = 0
        self.commission_start_attempts = 0
        self.commission_is_full = False
        self.region = {
            'left_menu': Region(0, 203, 57, 86),
            'collect_oil': Region(206, 105, 98, 58),
            'collect_gold': Region(579, 102, 98, 58),
            'complete_commission': Region(574, 393, 181, 61),
            'button_go': Region(574, 393, 181, 61),
            'urgent_tab': Region(24, 327, 108, 103),
            'daily_tab': Region(22, 185, 108, 103),
            'last_commission': Region(298, 846, 1478, 146),
            'commission_recommend': Region(1306, 483, 192, 92),
            'commission_start': Region(1543, 483, 191, 92),
            'oil_warning': Region(1073, 738, 221, 59),
            'button_back': Region(48, 43, 76, 76),
            'tap_to_continue': Region(661, 840, 598, 203),
            'dismiss_side_tab': Region(1020, 148, 370, 784),
            'dismiss_message': Region(688, 11, 538, 55)
        }

    def commission_logic_wrapper(self):
        """Method that fires off the necessary child methods that encapsulates
        the entire action of starting and completing commissions.
        """
        Logger.log_msg("Found commission completed alert.")
        Utils.touch_randomly(self.region["left_menu"])

        Utils.script_sleep(1)
        Utils.touch_randomly(self.region["collect_oil"])
        Utils.script_sleep(0.5)
        Utils.touch_randomly(self.region["collect_gold"])
        Utils.script_sleep(0.5)

        self.attempts_count = 0

        while True:
            Utils.update_screen()

            if Utils.find("commission/button_completed") and (lambda x:x > 332 and x < 511)(Utils.find("commission/button_completed").y):
                Logger.log_debug("Found commission complete button.")
                self.completed_handler()
            if Utils.find("commission/alert_available", 0.9) and (lambda x:x > 332 and x < 511)(Utils.find("commission/alert_available", 0.9).y):
                Logger.log_debug("Found commission available indicator.")
                self.commission_is_full = False
                if self.attempts_count > 2:
                    Logger.log_msg("Exceeded number of tries allowed. Resuming with other tasks.")
                    Utils.touch_randomly(self.region["dismiss_side_tab"])
                    break
                Utils.touch_randomly(self.region["button_go"])
                self.attempts_count += 1
                self.commission_start_attempts = 0
                Utils.wait_update_screen(1)

                while not Utils.find("menu/commission"):
                    Utils.touch_randomly(self.region["button_go"])
                    Utils.wait_update_screen(1)
                    if Utils.find_and_touch("menu/alert_close"):
                        Utils.script_sleep(1)
                if self.urgent_handler_selective():
                    self.daily_handler()
                Utils.touch_randomly(self.region["button_back"])
                continue
            if Utils.find("commission/button_go") and (lambda x:x > 332 and x < 511)(Utils.find("commission/button_go").y):
                Logger.log_msg("All commissions are running.")
                Utils.touch_randomly(self.region["dismiss_side_tab"])
                break

        Utils.wait_update_screen()
        return True

    def completed_handler(self):
        Utils.touch_randomly(self.region["complete_commission"])
        Utils.script_sleep(1)

        while True:
            Utils.update_screen()

            if Utils.find("commission/alert_perfect"):
                Utils.touch_randomly(self.region["tap_to_continue"])
                self.stats.increment_commissions_received()
                continue
            if Utils.find("menu/item_found"):
                Utils.touch_randomly(self.region["tap_to_continue"])
                Utils.script_sleep(1)
                continue
            if Utils.find("commission/alert_available", 0.9):
                Logger.log_debug("Finished completing commissions.")
                Utils.script_sleep(0.5)
                return

    def daily_handler(self):
        while True:
            Utils.update_screen()

            Utils.swipe(960, 680, 960, 400, 300)
            Utils.touch_randomly(self.region["last_commission"])
            if not self.start_commission():
                if self.commission_start_attempts > 10:
                    Logger.log_warning("Going back to main menu and retrying.")
                else:
                    Logger.log_msg("No more commissions to start.")
                return

    def urgent_handler(self):
        """ Return true if there are remaining fleets for more commissions.
        """
        Utils.touch_randomly(self.region["urgent_tab"])

        while True:
            Utils.update_screen()

            if Utils.find_and_touch("commission/commission_status"):
                Logger.log_msg("Found status indicator on urgent commission.")
                if not self.start_commission():
                    if self.commission_start_attempts > 10:
                        Logger.log_warning("Going back to main menu and retrying.")
                    else:
                        Logger.log_msg("No more commissions to start.")
                    return False
            else:
                Utils.touch_randomly(self.region["daily_tab"])
                Logger.log_msg("No urgent commissions left.")
                break

        Utils.script_sleep(1)
        return True

    def urgent_handler_selective(self):
        """ Return true and move to daily commission menu if commission is not yet full.
        """   
        Utils.touch_randomly(self.region["urgent_tab"])
        scroll_bottom_reached = True

        Utils.update_screen()
        if Utils.find("commission/scroll_bar_exist"):
            scroll_bottom_reached = False
            Logger.log_debug("Scroll bar detected.")
        else:
            Logger.log_debug("No scroll bar detected.")

        while True:   
            Utils.script_sleep(1)

            if not self.commission_is_full:
                Utils.update_screen() 
                commission_list = self.find_filtered_commission()
                if not commission_list:
                    Logger.log_msg("Found no non-driller commissions on current screen.")
                if commission_list:
                    Logger.log_msg("Found {} non-driller commission(s).".format(len(commission_list)))
                    # Only touch the first commission in the list because the game resets the screen after clicking on one, rendering the position in the list wrong.
                    i = 0
                    Utils.touch(commission_list[i])
                    if not self.start_commission():
                        if self.commission_start_attempts > 10:
                            Logger.log_warning("Going back to main menu and retrying.")
                        else:
                            Logger.log_msg("No more commissions to start.")
                        return False
                    continue
                elif scroll_bottom_reached:
                    Utils.touch_randomly(self.region["daily_tab"])
                    Logger.log_msg("No urgent commissions left.")
                    Utils.script_sleep(1)
                    return True
                else:
                    Utils.swipe_commission_slot(4)
                    Utils.update_screen()
                    if Utils.find("commission/scroll_bar_reaching_end"):
                        scroll_bottom_reached = True
                        Logger.log_debug("Scroll bottom reached.")
            else:
                return False

    @classmethod
    def find_filtered_commission(self):
        same_slot_determination_separtion = 90 # separation for status_indicator and driller is around 80
        driller_list = []
        commission_list = []
        list_tmp = []
        Utils.update_screen()
        list_tmp = Utils.find_all("commission/commission_status")
        driller_list = Utils.find_all("commission/driller")
        commission_list = copy.deepcopy(list_tmp)

        if list_tmp:        
            if driller_list:
                for i in range(0, len(list_tmp)):
                    for j in range(0, len(driller_list)):
                        if same_slot_determination_separtion >= (list_tmp[i][1] - driller_list[j][1]) > 0:
                            commission_list.remove(list_tmp[i])
                            break
        return commission_list


    def start_commission(self):
        Logger.log_debug("Starting commission.")
        tapped_recommend = False

        while True:
            Utils.update_screen()

            if self.commission_start_attempts > 10:
                Logger.log_warning("Failed to start commission.")
                Utils.touch_randomly(self.region["dismiss_message"])
                break
            if Utils.find("commission/alert_begun"):
                Logger.log_msg("Successfully started commission.")
                Utils.touch_randomly(self.region["dismiss_message"])
                self.stats.increment_commissions_started()
                break
            if Utils.find("menu/button_confirm"):
                Logger.log_debug("Found commission oil warning message.")
                Utils.touch_randomly(self.region["oil_warning"])
                continue
            if tapped_recommend and Utils.find("commission/button_ready"):
                Logger.log_debug("Found commission start button.")
                Utils.touch_randomly(self.region["commission_start"])
                tapped_recommend = False
                continue
            if Utils.find("commission/button_recommend"):
                Logger.log_debug("Found commission recommend button.")
                Utils.touch_randomly(self.region["commission_recommend"])
                tapped_recommend = True
                self.commission_start_attempts += 1
                continue

        Utils.wait_update_screen(1)
        self.commission_is_full = Utils.find("commission/commissions_full")
        return not (self.commission_is_full or self.commission_start_attempts > 10)