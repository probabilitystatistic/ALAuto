import math
import string
from datetime import datetime, timedelta
from util.logger import Logger
from util.utils import Region, Utils
from threading import Thread

class CombatModule(object):

    def __init__(self, config, stats, retirement_module, enhancement_module):
        """Initializes the Combat module.

        Args:
            config (Config): ALAuto Config instance.
            stats (Stats): ALAuto Stats instance.
            retirement_module (RetirementModule): ALAuto RetirementModule instance.
            enhancement_module (EnhancementModule): ALAuto EnhancementModule instance.
        """
        self.enabled = True
        self.config = config
        self.stats = stats
        self.retirement_module = retirement_module
        self.enhancement_module = enhancement_module
        self.use_intersection = True if self.config.combat['search_mode'] == 1 else False
        self.chapter_map = self.config.combat['map']
        Utils.small_boss_icon = config.combat['small_boss_icon']
        self.exit = 0
        self.combats_done = 0
        self.enemies_list = []
        self.mystery_nodes_list = []
        self.blacklist = []
        self.movement_event = {}
        self.sleep_short = 0.5
        self.sleep_long = 1
        self.map_similarity = 0.95

        self.kills_count = 0
        self.kills_before_boss = {
            '1-1': 1, '1-2': 2, '1-3': 2, '1-4': 3,
            '2-1': 2, '2-2': 3, '2-3': 3, '2-4': 3,
            '3-1': 3, '3-2': 3, '3-3': 3, '3-4': 3,
            '4-1': 3, '4-2': 3, '4-3': 3, '4-4': 4,
            '5-1': 4, '5-2': 4, '5-3': 4, '5-4': 4,
            '6-1': 4, '6-2': 4, '6-3': 4, '6-4': 5,
            '7-1': 5, '7-2': 5, '7-3': 5, '7-4': 5,
            '8-1': 4, '8-2': 4, '8-3': 4, '8-4': 4,
            '9-1': 5, '9-2': 5, '9-3': 5, '9-4': 5,
            '10-1': 6, '10-2': 6, '10-3': 6, '10-4': 6,
            '11-1': 6, '11-2': 6, '11-3': 6, '11-4': 6,
            '12-1': 6, '12-2': 6, '12-3': 6, '12-4': 6,
            '13-1': 6, '13-2': 6, '13-3': 6, '13-4': 7
        }
        if self.chapter_map not in self.kills_before_boss:
            # check if current map is present in the dictionary and if it isn't,
            # a new entry is added with kills_before_boss value
            self.kills_before_boss[self.chapter_map] = self.config.combat['kills_before_boss']
        elif self.config.combat['kills_before_boss'] != 0:
            # updates default value with the one provided by the user
            self.kills_before_boss[self.chapter_map] = self.config.combat['kills_before_boss']

        self.region = {
            'fleet_lock': Region(1790, 750, 130, 30),
            'open_strategy_menu': Region(1797, 617, 105, 90),
            'disable_subs_hunting_radius': Region(1655, 615, 108, 108),
            'close_strategy_menu': Region(1590, 615, 40, 105),
            'menu_button_battle': Region(1517, 442, 209, 206),
            'map_summary_go': Region(1289, 743, 280, 79),
            'fleet_menu_go': Region(1485, 872, 270, 74),
            'combat_ambush_evade': Region(1493, 682, 208, 56),
            'combat_com_confirm': Region(848, 740, 224, 56),
            'combat_end_confirm': Region(1520, 963, 216, 58),
            'combat_dismiss_surface_fleet_summary': Region(790, 950, 250, 65),
            'menu_combat_start': Region(1578, 921, 270, 70),
            'tap_to_continue': Region(661, 840, 598, 203),
            'close_info_dialog': Region(1326, 274, 35, 35),
            'dismiss_ship_drop': Region(1228, 103, 692, 500),
            'retreat_button': Region(1130, 985, 243, 60),
            'dismiss_commission_dialog': Region(1065, 732, 235, 68),
            'normal_mode_button': Region(88, 990, 80, 40),
            'map_nav_right': Region(1831, 547, 26, 26),
            'map_nav_left': Region(65, 547, 26, 26),
            'event_button': Region(1770, 250, 75, 75),
            'lock_ship_button': Region(1086, 739, 200, 55),
            'clear_second_fleet': Region(1690, 473, 40, 40),
            'button_switch_fleet': Region(1430, 985, 240, 60),
            'menu_nav_back': Region(54, 57, 67, 67),
            'first_slot_choose': Region(1550, 270, 70, 60),
            'second_slot_choose': Region(1550, 460, 70, 60)
        }

        self.prohibited_region = {
            'left_side_bar': Region(0, 162, 190, 926),
            'top_bar': Region(0, 0, 1920, 114),
            'fleet_info': Region(0, 114, 1728, 56),
            'fleet_bonuses': Region(190, 170, 575, 75),
            'mission_conditions': Region(1837, 130, 83, 220),
            'strategy_tab': Region(1770, 590, 150, 136),
            'fleet_lock_button': Region(1755, 726, 165, 90),
            'command_buttons': Region(965, 940, 955, 140)
        }

        self.swipe_counter = 0
        self.fleet_switch_due_to_morale= False
        self.fleet_switch_index = -1


    def combat_logic_wrapper(self):
        """Method that fires off the necessary child methods that encapsulates
        the entire action of sortieing combat fleets and resolving combat.

        Returns:
            int: 1 if boss was defeated, 2 if successfully retreated after the specified
                number of fights, 3 if morale is too low, 4 if dock is full and unable to
                free it and 5 if fleet was defeated.
        """
        self.exit = 0
        self.start_time = datetime.now()
        # enhancecement and retirement flags
        enhancement_failed = False
        retirement_failed = False
        fleet_switch_candidate_for_morale= self.config.combat['low_mood_rotation_fleet']
        first_fleet_slot_position = [1650, 393]
        fleet_slot_separation = 64


        # get to map
        map_region = self.reach_map()
        Utils.touch_randomly_ensured(map_region, "menu/attack", ["combat/button_go"] , need_initial_screen=True, response_time=0.5)

        while True:
            Utils.wait_update_screen()

            if self.exit == 1 or self.exit == 2 or self.exit == 6:
                self.stats.increment_combat_done()
                time_passed = datetime.now() - self.start_time
                if self.stats.combat_done % self.config.combat['retire_cycle'] == 0 or ((self.config.commissions['enabled'] or \
                    self.config.dorm['enabled'] or self.config.academy['enabled']) and time_passed.total_seconds() > 3600) or \
                        not Utils.check_oil(self.config.combat['oil_limit']):
                        break
                else:
                    self.exit = 0
                    Logger.log_msg("Repeating map {}.".format(self.chapter_map))
                    while True:
                        Utils.touch_randomly(map_region)
                        Utils.wait_update_screen()
                        if Utils.find("combat/button_go"):
                            break
                    continue
            if self.exit > 2:
                self.stats.increment_combat_attempted()
                break
            if Utils.find("combat/button_go"):
                Logger.log_debug("Found map summary go button.")
                Utils.touch_randomly(self.region["map_summary_go"])
                Utils.wait_update_screen()
            if Utils.find("combat/menu_fleet") and (lambda x:x > 414 and x < 584)(Utils.find("combat/menu_fleet").y) and not self.config.combat['boss_fleet']:
                if not self.chapter_map[0].isdigit() and string.ascii_uppercase.index(self.chapter_map[2:3]) < 1 or self.chapter_map[0].isdigit():
                    Logger.log_msg("Removing second fleet from fleet selection.")
                    Utils.touch_randomly(self.region["clear_second_fleet"])
            if Utils.find("combat/menu_select_fleet"):
                Logger.log_debug("Found fleet select go button.")
                # Rotating fleet due to low morale
                if(self.fleet_switch_due_to_morale):
                    Logger.log_warning("Switching fleet due to low morale.")
                    self.fleet_switch_index = self.fleet_switch_index + 1
                    self.fleet_switch_due_to_morale= False
                    #if not self.config.combat['boss_fleet']:
                    #    self.select_fleet(first_slot_fleet = fleet_switch_candidate_for_morale[self.fleet_switch_index % len(fleet_switch_candidate_for_morale)])
                    #else:
                    #    if not self.select_fleet(first_slot_fleet = fleet_switch_candidate_for_morale[self.fleet_switch_index % len(fleet_switch_candidate_for_morale)], second_slot_fleet=??):
                    #       Logger.log_warning("Abnormal fleet order.")
                    Utils.touch_randomly(self.region["first_slot_choose"])
                    Utils.script_sleep(1)
                    target_fleet_vertical_position = first_fleet_slot_position[1] + fleet_slot_separation*(fleet_switch_candidate_for_morale[self.fleet_switch_index % len(fleet_switch_candidate_for_morale)] - 1)
                    Utils.touch([first_fleet_slot_position[0], target_fleet_vertical_position])
                    Utils.script_sleep(1)
                Utils.touch_randomly_ensured(self.region["fleet_menu_go"], "combat/menu_select_fleet", ["combat/button_retreat", "combat/alert_morale_low"], response_time=2)
            if Utils.find("combat/button_retreat"):
                Logger.log_debug("Found retreat button, starting clear function.")
                if (self.chapter_map[0] == '7' and self.chapter_map[2] == '2' and self.config.combat['clearing_mode'] and self.config.combat['focus_on_mystery_nodes']):
                    Logger.log_debug("Started special 7-2 farming.")
                    if not self.clear_map_special_7_2():
                   	    self.stats.increment_combat_attempted()
                   	    break
                    Utils.wait_update_screen()
                else:
                    if not self.clear_map():
                        self.stats.increment_combat_attempted()
                        break
                    Utils.wait_update_screen()
            if Utils.find("menu/button_sort"):
                if self.config.enhancement['enabled'] and not enhancement_failed:
                    if not self.enhancement_module.enhancement_logic_wrapper(forced=True):
                        enhancement_failed = True
                    Utils.script_sleep(1)
                    Utils.touch_randomly(map_region)
                    continue
                elif self.config.retirement['enabled'] and not retirement_failed:
                    if not self.retirement_module.retirement_logic_wrapper(forced=True):
                        retirement_failed = True
                    else:
                        # reset enhancement flag
                        enhancement_failed = False
                    Utils.script_sleep(1)
                    Utils.touch_randomly(map_region)
                    continue
                else:
                    Utils.touch_randomly(self.region['close_info_dialog'])
                    self.exit = 4
                    break
            if Utils.find("combat/alert_morale_low"):
                if self.config.combat['ignore_morale']:
                    Utils.find_and_touch("menu/button_confirm")
                #else:
                #    Utils.touch_randomly(self.region['close_info_dialog'])
                #    self.exit = 3
                #    break
                else:
                    Utils.touch_randomly(self.region['close_info_dialog'])
                    # Issue fleet rotation(currently not supporting for two fleets so bot rest when two fleets are used)
                    if self.config.combat['low_mood_rotation']:
                        self.exit = 6
                        self.fleet_switch_due_to_morale= True
                        Logger.log_warning("Low morale detected. Will switch to a different fleet.")
                        break
                    # bot rest by default
                    else:
                        self.exit = 3
                        break

            if Utils.find("menu/button_confirm"):
                Logger.log_msg("Found commission info message.")
                self.stats.increment_commissions_occurance()
                Utils.touch_randomly(self.region["combat_com_confirm"])

        Utils.script_sleep(1)
        Utils.menu_navigate("menu/button_battle")

        return self.exit

    def select_fleet(self, first_slot_fleet=1, second_slot_fleet=None):
        """ Select the fleets
            Return True if first_slot_fleet < second_slot_fleet (fleets in each slots will not be automatically changed )
        """
        first_slot_fleet1_position = [1650, 393]
        second_slot_fleet1_position = [1650, 593]
        fleet_slot_separation = 64
        Utils.touch_randomly(self.region["clear_second_fleet"])
        if second_slot_fleet ==None:
            Utils.touch_randomly(self.region["first_slot_choose"])
            Utils.touch(first_slot_fleet1_position[0], first_slot_fleet1_position[1]+fleet_slot_separation*(first_slot_fleet - 1))
        else:
            Utils.touch_randomly(self.region["first_slot_choose"])
            Utils.touch(first_slot_fleet1_position[0], first_slot_fleet1_position[1]+fleet_slot_separation*(first_slot_fleet - 1))
            Utils.touch_randomly(self.region["second_slot_choose"])
            Utils.touch(second_slot_fleet1_position[0], second_slot_fleet1_position[1]+fleet_slot_separation*(second_slot_fleet - 1))

    def reach_map(self):
        """
        Method which returns the map region for the stage set in the configuration file.
        If the map isn't found, it navigates the map selection menu to get to the world where the specified map is located.
        Only works with standard maps up to worlds 13 and some event maps.
        Also checks if hard mode is enabled, and if it's legit to keep it so (event maps C and D).
        If nothing is found even after menu navigation, it stops the bot workflow until the user moves to the right
        screen or the map asset is substituted with the right one.

        Returns:
            (Region): the map region of the selected stage.
        """
        Utils.wait_update_screen()
        # get to map selection menu
        if Utils.find("menu/button_battle"):
            Logger.log_debug("Found menu battle button.")
            Utils.touch_randomly(self.region["menu_button_battle"])
            Utils.wait_update_screen(2)

        # correct map mode
        if not self.chapter_map[0].isdigit():
            letter = self.chapter_map[2]
            event_maps = ['A', 'B', 'S', 'C', 'D']

            Utils.touch_randomly(self.region['event_button'])
            Utils.wait_update_screen(1)

#           By me: comment out the switching to normal mode for event map so I can farm D2 in Iris of light and dark.
#                Utils.touch_randomly(self.region['normal_mode_button'])
#                Utils.wait_update_screen(1)
        else:
            if Utils.find("menu/button_normal_mode"):
                Logger.log_debug("Disabling hard mode.")
                # disable the check for normal mode so as to do daily hard runs
                #Utils.touch_randomly(self.region['normal_mode_button'])
                Utils.wait_update_screen(1)

        map_region = Utils.find('maps/map_{}'.format(self.chapter_map), self.map_similarity)
        if map_region != None:
            Logger.log_msg("Found specified map.")
            return map_region
        else:
            # navigate map selection menu
            if not self.chapter_map[0].isdigit():
                if (self.chapter_map[2] == 'A' or self.chapter_map[2] == 'C') and \
                    (Utils.find('maps/map_E-B1', 0.99) or Utils.find('maps/map_E-D1', 0.99)):
                    Utils.touch_randomly(self.region['map_nav_left'])
                    Logger.log_debug("Swiping to the left")
                elif (self.chapter_map[2] == 'B' or self.chapter_map[2] == 'D') and \
                    (Utils.find('maps/map_E-A1', 0.99) or Utils.find('maps/map_E-C1', 0.99)):
                    Utils.touch_randomly(self.region['map_nav_right'])
                    Logger.log_debug("Swiping to the right")
            else:
                _map = 0
                for x in range(1, 14):
                    if Utils.find("maps/map_{}-1".format(x), 0.99):
                        _map = x
                        break
                if _map != 0:
                    taps = int(self.chapter_map.split("-")[0]) - _map
                    for x in range(0, abs(taps)):
                        if taps >= 1:
                            Utils.touch_randomly(self.region['map_nav_right'])
                            Logger.log_debug("Swiping to the right")
                            Utils.script_sleep()
                        else:
                            Utils.touch_randomly(self.region['map_nav_left'])
                            Logger.log_debug("Swiping to the left")
                            Utils.script_sleep()

        Utils.wait_update_screen()
# By me: lowering the similarity for map detection
#        map_region = Utils.find('maps/map_{}'.format(self.chapter_map), 0.99)
        map_region = Utils.find('maps/map_{}'.format(self.chapter_map), self.map_similarity)
        if map_region == None:
            Logger.log_error("Cannot find the specified map, please move to the world where it's located.")
        while map_region == None:
            map_region = Utils.find('maps/map_{}'.format(self.chapter_map), self.map_similarity)
            Utils.wait_update_screen(1)

        Logger.log_msg("Found specified map.")
        return map_region

    def battle_handler(self, boss=False):
        Logger.log_msg("Starting combat.")

        # enhancecement and retirement flags
        enhancement_failed = False
        retirement_failed = False
        while not (Utils.find_with_cropped("combat/menu_loading", 0.8)):
            Utils.update_screen()
            if Utils.find_with_cropped("menu/button_sort"):
                if self.config.enhancement['enabled'] and not enhancement_failed:
                    if not self.enhancement_module.enhancement_logic_wrapper(forced=True):
                        enhancement_failed = True
                elif self.config.retirement['enabled'] and not retirement_failed:
                    if not self.retirement_module.retirement_logic_wrapper(forced=True):
                        retirement_failed = True
                else:
                    self.exit = 4
                    Utils.touch_randomly(self.region['close_info_dialog'])
                    return False
            elif Utils.find_with_cropped("combat/alert_morale_low"):
                if self.config.combat['ignore_morale']:
                    Utils.find_and_touch("menu/button_confirm")
                else:
                    Utils.touch_randomly(self.region['close_info_dialog'])
                    # Issue fleet rotation(currently not supporting for two fleets so bot rest when two fleets are used)
                    if self.config.combat['low_mood_rotation']:
                        self.exit = 6
                        self.fleet_switch_due_to_morale= True
                        Logger.log_warning("Low morale detected. Will switch to a different fleet.")
                        return False
                    # bot rest by default
                    else:
                        self.exit = 3
                        return False
            elif Utils.find_with_cropped("combat/combat_pause", 0.7):
                Logger.log_warning("Loading screen was not found but combat pause is present, assuming combat is initiated normally.")
                break
            else:
                Utils.touch_randomly(self.region["menu_combat_start"])
                Utils.script_sleep(1)

        Utils.script_sleep(4)

        # flags
        in_battle = True
        items_received = False
        locked_ship = False
        confirmed_fight = False
        defeat = False
        confirmed_fleet_switch = False
        while True:
            Utils.update_screen()

            if in_battle and Utils.find_with_cropped("combat/combat_pause", 0.7):
                Logger.log_debug("In battle.")
                Utils.script_sleep(1.5)
                continue
            if not items_received:
                if Utils.find_with_cropped("combat/menu_touch2continue"):
                    Logger.log_debug("Combat ended: tap to continue")
                    Utils.touch_randomly_ensured(self.region['tap_to_continue'], "combat/menu_touch2continue", ["menu/item_found", "combat/button_confirm"])
                    in_battle = False
                    continue
                if Utils.find_with_cropped("menu/item_found"):
                    Logger.log_debug("Combat ended: items received screen")
                    # the reference for combat/alert_lock is for possible mis-clicking here in the ship drop screen(screen change to
                    # ship drop screen but the previous screen is captured).
                    Utils.touch_randomly_ensured(self.region['tap_to_continue'], "menu/item_found", 
                                                ["combat/button_confirm", "menu/drop_elite", "menu/drop_rare", 
                                                 "menu/drop_ssr", "menu/drop_common", "combat/alert_lock"],
                                                 response_time=0.5,
                                                similarity_after=0.9)
                    Utils.script_sleep(0)
                    continue
                if (not locked_ship) and Utils.find_with_cropped("combat/alert_lock", 0.9): 
                    Logger.log_msg("Locking received ship.")
                    Utils.touch_randomly_ensured(self.region['lock_ship_button'], "combat/alert_lock", ["combat/button_confirm"], similarity_before=0.9)
                    locked_ship = True
                    continue
                if Utils.find_with_cropped("menu/drop_elite"):
                    Logger.log_msg("Received ELITE ship as drop.")
                    # sometimes this ensured touch fails after 10 clicks(but still keep going to continue). It successes the next time after the continue.
                    Utils.touch_randomly_ensured(self.region['dismiss_ship_drop'], "menu/drop_elite", ["combat/button_confirm", "combat/alert_lock"])
                    Utils.script_sleep(self.sleep_short)
                    continue
                elif Utils.find_with_cropped("menu/drop_rare"):
                    Logger.log_msg("Received new RARE ship as drop.")
                    Utils.touch_randomly_ensured(self.region['dismiss_ship_drop'], "menu/drop_rare", ["combat/button_confirm", "combat/alert_lock"])
                    Utils.script_sleep(self.sleep_short)
                    continue
                elif Utils.find_with_cropped("menu/drop_ssr"):
                    Logger.log_msg("Received SSR ship as drop.")
                    Utils.touch_randomly_ensured(self.region['dismiss_ship_drop'], "menu/drop_ssr", ["combat/button_confirm", "combat/alert_lock"])
                    Utils.script_sleep(self.sleep_short)
                    continue
                elif Utils.find_with_cropped("menu/drop_common"):
                    Logger.log_msg("Received new COMMON ship as drop.")
                    Utils.touch_randomly_ensured(self.region['dismiss_ship_drop'], "menu/drop_common", ["combat/button_confirm", "combat/alert_lock"])
                    Utils.script_sleep(self.sleep_short)
                    continue
            if not in_battle:
                if (not confirmed_fight) and Utils.find_with_cropped("combat/button_confirm"):
                    Logger.log_msg("Combat ended.")
                    items_received = True
                    confirmed_fight = True
                    Utils.touch_randomly_ensured(self.region["combat_end_confirm"], "combat/button_confirm", 
                                                ["combat/button_retreat", "menu/button_confirm", 
                                                 "combat/defeat_close_button", "menu/attack"], 
                                                response_time=3, similarity_after=0.9,
                                                stable_check_frame=3)
                if (not confirmed_fight) and Utils.find_with_cropped("combat/commander"):
                    items_received = True
                    # prevents fleet with submarines from getting stuck at combat end screen
                    Logger.log_warning("Dismissing the submarine screen.")
                    Utils.touch_randomly(self.region["combat_dismiss_surface_fleet_summary"])
                    continue
                if defeat and not confirmed_fleet_switch:
                    if Utils.find_with_cropped("combat/alert_unable_battle"):
                        Utils.touch_randomly(self.region['close_info_dialog'])
                        Utils.script_sleep(1)
                        self.exit = 5
                        return False
                    if Utils.find_with_cropped("combat/alert_fleet_cannot_be_formed"):
                        # fleet will be automatically switched
                        Utils.touch_randomly(self.region['close_info_dialog'])
                        confirmed_fleet_switch = True
                        self.enemies_list.clear()
                        self.mystery_nodes_list.clear()
                        self.blacklist.clear()
                        Utils.script_sleep(self.sleep_long)
                        if boss:
                            self.exit = 5
                            return False
                        continue
                    else:
                        # flagship sunk, but part of backline still remains
                        # proceed to retreat
                        Utils.script_sleep(self.sleep_long)
                        self.exit = 5
                        return False
                if confirmed_fight and Utils.find_with_cropped("menu/button_confirm"):
                    Logger.log_msg("Found commission info message.")
                    self.stats.increment_commissions_occurance()
                    Utils.touch_randomly(self.region["combat_com_confirm"])
                    continue
                if confirmed_fight and (not boss) and Utils.find_with_cropped("combat/button_retreat"):
                    #Utils.touch_randomly(self.region["hide_strat_menu"])
                    if confirmed_fleet_switch:
                        # if fleet was defeated and it has now been switched
                        return False
                    else:
                        # fleet won the fight
                        self.combats_done += 1
                        self.kills_count += 1
                        if self.kills_count >= self.kills_before_boss[self.chapter_map]:
                            # waiting the appearance of boss
                            Utils.script_sleep(2)
                        return True
                if confirmed_fight and Utils.find_and_touch_with_cropped("combat/defeat_close_button",0.9):
                    Logger.log_debug("Fleet was defeated.")
                    defeat = True
                    Utils.script_sleep(3)
                if boss and confirmed_fight:
                    if not defeat:
                        return True

    def movement_handler(self, target_info):
        """
        Method that handles the fleet movement until it reach its target (mystery node or enemy node).
        If the coordinates are wrong, they will be blacklisted and another set of coordinates to work on is obtained.
        If the target is a mystery node and what is found is ammo, then the method will fall in the blacklist case
        and search for another enemy: this is inefficient and should be improved, but it works.

        Args:
            target_info (list): coordinate_x, coordinate_y, type. Describes the selected target.
        Returns:
            (int): 1 if a fight is needed, otherwise 0.
        """
        Logger.log_msg("Moving towards objective.")
        count = 0
        location = [target_info[0], target_info[1]]
        Utils.script_sleep(1)

        while True:
            Utils.update_screen()
            event = self.check_movement_threads()

            if (self.chapter_map[0].isdigit() and not self.config.combat['clearing_mode']) and event["combat/button_evade"]:
                Logger.log_msg("Ambush was found, trying to evade.")
                Utils.touch_randomly(self.region["combat_ambush_evade"])
                Utils.script_sleep(0.5)
                continue
            if (self.chapter_map[0].isdigit() and not self.config.combat['clearing_mode']) and event["combat/alert_failed_evade"]:
                Logger.log_warning("Failed to evade ambush.")
                self.kills_count -= 1
                Utils.touch_randomly(self.region["menu_combat_start"])
                self.battle_handler()
                continue
            if self.chapter_map[0].isdigit() and event["combat/alert_ammo_supplies"]:
                Logger.log_msg("Received ammo supplies")
                if target_info[2] == "mystery_node":
                    Logger.log_msg("Target reached.")
                    self.fleet_location = target_info[0:2]
                    return 0
                continue
            if self.chapter_map[0].isdigit() and event["menu/item_found"]:
                Logger.log_msg("Item found on node.")
                Utils.touch_randomly(self.region['tap_to_continue'])
                if Utils.find("combat/menu_emergency"):
                    Utils.script_sleep(1)
                    Utils.touch_randomly(self.region["close_strategy_menu"])
                if target_info[2] == "mystery_node":
                    Logger.log_msg("Target reached.")
                    self.fleet_location = target_info[0:2]
                    return 0
                continue
            if event["menu/alert_info"]:
                Logger.log_debug("Found alert.")
                Utils.find_and_touch("menu/alert_close")
                continue
            if event["combat/menu_loading"]:
                self.fleet_location = target_info[0:2]
                return 1
            elif event["combat/menu_formation"]:
                Utils.find_and_touch("combat/auto_combat_off")
                self.fleet_location = target_info[0:2]
                return 1
            else:
                if count != 0 and count % 3 == 0:
                    Utils.touch(location)
                if (count > 11 and (self.chapter_map == '7-2' or self.chapter_map == '5-1') and self.config.combat['clearing_mode']):
                    Logger.log_warning("Clicking on the destination for too many times. Assuming target reached.")
                    return 0
                if count > 21:
                    Logger.log_msg("Blacklisting location and searching for another enemy.")
                    self.blacklist.append(location[0:2])
                    self.fleet_location = None
                    location = self.get_closest_target(self.blacklist, mystery_node=(not self.config.combat["ignore_mystery_nodes"]))
                    count = 0
                count += 1

    def unable_handler(self, coords, boss=False):
        """
        Method called when the path to the target (boss fleet or mystery node) is obstructed by mobs:
        it procedes to switch targets to the mobs which are blocking the path.

        Args:
            coords (list): coordinate_x, coordinate_y. These coordinates describe the target's location.
        """
        if boss:
            Logger.log_debug("Unable to reach boss function started.")
        else:
            Logger.log_debug("Unable to reach selected target function started.")
        self.blacklist.clear()

        closest_to_unreachable_target = self.get_closest_target(self.blacklist, coords, boss=boss)

# By me:
        Utils.script_sleep(1)
        Utils.touch(closest_to_unreachable_target)
# if the target in above line is reachable and if the dialog "unbale to reach target" from a previous 
# moving attemp has not yet disappeared, the update screen below will wrongly think the reachable target 
# is unreachable. The solution is to ask the program to wait before clicking the target.
        Utils.update_screen()

        if Utils.find("combat/alert_unable_reach"):
            Logger.log_warning("Unable to reach next to selected target.")
            self.blacklist.append(closest_to_unreachable_target[0:2])

            while True:
                closest_enemy = self.get_closest_target(self.blacklist)
# By me:
                Utils.script_sleep(1)
                Utils.touch(closest_enemy)
                Utils.update_screen()

                if Utils.find("combat/alert_unable_reach"):
                    self.blacklist.append(closest_enemy[0:2])
                else:
                    break

            self.movement_handler(closest_enemy)
            if not self.battle_handler():
                return False
            return True
        else:
            self.movement_handler(closest_to_unreachable_target)
            if not self.battle_handler():
                return False
            return True

    def retreat_handler(self):
        """ Retreats if necessary.
        """

        force_retreat = True if self.exit != 1 else False
        pressed_retreat_button = False

        while True:
            Utils.update_screen()

            if Utils.find("combat/menu_formation"):
                Utils.touch_randomly(self.region["menu_nav_back"])
                Utils.script_sleep(1)
                continue
            if force_retreat and (not pressed_retreat_button) and Utils.find("combat/button_retreat"):
                Logger.log_msg("Retreating...")
                if Utils.touch_randomly_ensured(self.region['retreat_button'], "combat/button_retreat", ["menu/button_confirm"]):
                    pressed_retreat_button = True
                Utils.script_sleep(1)
                continue
            if Utils.find_and_touch("menu/button_confirm"):
                # confirm either the retreat or an urgent commission alert
                Utils.script_sleep(1)
                continue
            if Utils.find("menu/attack"):
                return

    def clear_map(self):
        """ Clears map.
        """
        self.fleet_location = None
        self.combats_done = 0
        self.kills_count = 0
        self.enemies_list.clear()
        self.mystery_nodes_list.clear()
        self.blacklist.clear()
        self.swipe_counter = 0
        Logger.log_msg("Started map clear.")
        Utils.script_sleep(2.5)

        while Utils.find("combat/fleet_lock", 0.99):
            Utils.touch_randomly(self.region["fleet_lock"])
            Logger.log_warning("Fleet lock is not supported, disabling it.")
            Utils.wait_update_screen()

        if self.config.combat['fleet_switch_at_beinning']:
            Utils.touch_randomly(self.region['button_switch_fleet'])

        #swipe map to fit everything on screen
        swipes = {
            'E-B3': lambda: Utils.swipe(960, 540, 1060, 670, 300),
            'E-D3': lambda: Utils.swipe(960, 540, 1060, 670, 300),
            # needs to be updated
# By me:
# adding the swipe to fit the question mark of 5-1 on screen
            '5-1': lambda: Utils.swipe(1000, 500, 1000, 600, 300),
            '12-2': lambda: Utils.swipe(1000, 570, 1300, 540, 300),
            '12-3': lambda: Utils.swipe(1250, 530, 1300, 540, 300),
            '12-4': lambda: Utils.swipe(960, 300, 960, 540, 300),
            '13-1': lambda: Utils.swipe(1020, 500, 1300, 540, 300),
            '13-2': lambda: Utils.swipe(1125, 550, 1300, 540, 300),
            '13-3': lambda: Utils.swipe(1150, 510, 1300, 540, 300),
            '13-4': lambda: Utils.swipe(1200, 450, 1300, 540, 300)
        }
        swipes.get(self.chapter_map, lambda: None)()

        # disable subs' hunting range
        if self.config.combat["hide_subs_hunting_range"]:
            Utils.script_sleep(0.5)
            Utils.touch_randomly(self.region["open_strategy_menu"])
            Utils.script_sleep()
            Utils.touch_randomly(self.region["disable_subs_hunting_radius"])
            Utils.script_sleep()
            Utils.touch_randomly(self.region["close_strategy_menu"])

        # special switch for special farming
        if self.chapter_map=="5-1":
            # Special farming for 5-1:
            # Setup: fleet 1 = boss fleet; another fleet = mob fleet; enable boss fleet = True; prioritize mystery node = True
            # 1. boss fleet move to obtain the mystery node at the beginning(this also ensure no boss blocking by boss fleet)
            # 2. switch to mob fleet, and let it clear 4 enemies(boss block by mob fleet can be handled by the default left/right disclosing)
            # 3. switch back to boss fleet, and clear the boss
            target_info = self.get_closest_target(self.blacklist, mystery_node=True)
            Utils.touch(target_info[0:2])
            self.movement_handler(target_info)
            Utils.touch_randomly(self.region['button_switch_fleet'])
            Utils.update_screen()
#By me:
# allow the bot to collect question node at the first turn
        #target_info = self.get_closest_target(self.blacklist)
        target_info = self.get_closest_target(self.blacklist, mystery_node=(not self.config.combat["ignore_mystery_nodes"]))

        while True:
            Utils.update_screen()

            if Utils.find("combat/alert_unable_battle"):
                Utils.touch_randomly(self.region['close_info_dialog'])
                self.exit = 5
            #if self.config.combat['retreat_after'] != 0 and self.combats_done >= self.config.combat['retreat_after']:
            if self.config.combat['retreat_after'] != 0 and self.kills_count >= self.config.combat['retreat_after'] and (target_info != None and target_info[2] == 'enemy'):
                Logger.log_msg("Retreating after defeating {} enemies".format(self.config.combat['retreat_after']))
                self.exit = 2
            if self.exit != 0:
                self.retreat_handler()
                return True
# By me:
# Solution when boss is hidden by player's fleet. This should work for map 5-1 and 6-1.
# It's just moving one grid left(it's two to avoid further possible block).
# The width of one grid is roughly 180 pixels.
# Note that this will fail if the boss is hidden by the other fleet.
            if self.kills_count >= self.kills_before_boss[self.chapter_map] and not Utils.find_in_scaling_range("enemy/fleet_boss", similarity=0.9):
                Logger.log_msg("Boss fleet is not found. Trying to uncover the boss.")
                self.fleet_location = None
                single_fleet_location = self.get_fleet_location()
                location_left_of_fleet = [0, 0]
                location_left_of_fleet[0] = single_fleet_location[0] - 180
                location_left_of_fleet[1] = single_fleet_location[1]
                Utils.touch(location_left_of_fleet)
                # We must give some time for the fleet to move, otherwise the screen update right after continue will still fail to see boss.
                Utils.script_sleep(1.5)
                continue
            if self.kills_count >= self.kills_before_boss[self.chapter_map] and Utils.find_in_scaling_range("enemy/fleet_boss", similarity=0.9):
                Logger.log_msg("Boss fleet was found.")

                if self.config.combat['boss_fleet']:
                    if self.chapter_map == 'E-B3' or self.chapter_map == 'E-D3':
                        s = 3
                    else:
                        s = 0
                    swipes = {
                        0: lambda: Utils.swipe(960, 240, 960, 940, 300),
                        1: lambda: Utils.swipe(1560, 540, 260, 540, 300),
                        2: lambda: Utils.swipe(960, 940, 960, 240, 300),
                        3: lambda: Utils.swipe(260, 540, 1560, 540, 300)
                    }

                    Utils.touch_randomly(self.region['button_switch_fleet'])
                    Utils.wait_update_screen(2)
                    boss_region = Utils.find_in_scaling_range("enemy/fleet_boss", similarity=0.9)

                    while not boss_region:
                        if s > 3: s = 0
                        swipes.get(s)()
                        Utils.wait_update_screen(0.5)
                        boss_region = Utils.find_in_scaling_range("enemy/fleet_boss", similarity=0.9)
                        s += 1

                    # swipe to center the boss fleet on the screen
                    # first calculate the translation vector coordinates
                    translation_sign = 1 if boss_region.x < 960 else -1
                    translation_module = 175 if boss_region.y > 300 else 75
                    horizontal_translation = translation_sign * translation_module
                    angular_coefficient = -1 * ((540 - boss_region.y)/(960 - boss_region.x))
                    Utils.swipe(boss_region.x + horizontal_translation, boss_region.y + int(horizontal_translation * angular_coefficient),
                        960 + horizontal_translation, 540 + int(horizontal_translation * angular_coefficient), 300)
                    Utils.wait_update_screen()

                boss_region = Utils.find_in_scaling_range("enemy/fleet_boss", similarity=0.9)
                while not boss_region:
                    # refreshing screen to deal with mist
                    Utils.wait_update_screen(1)
                    boss_region = Utils.find_in_scaling_range("enemy/fleet_boss", similarity=0.9)

                #extrapolates boss_info(x,y,enemy_type) from the boss_region found
                boss_info = [boss_region.x + 50, boss_region.y + 25, "boss"]
                self.clear_boss(boss_info)
                continue
            if target_info == None:
                target_info = self.get_closest_target(self.blacklist, mystery_node=(not self.config.combat["ignore_mystery_nodes"]))
                continue
            if target_info:
                #tap at target's coordinates
                Utils.touch(target_info[0:2])
                # This sleep must be long to avoid capturing the screen before game responds but also short enough to capture the "unable to reach..." dialog before it disappears.
                #Utils.script_sleep(1)
                Utils.update_screen()
            else:
                continue
# By me: it seems that lower similarity(0.8) actually make the bot unable to detect "unable to reach".
#        but it should be easier when similarity is low. Not sure why                
#            if Utils.find("combat/alert_unable_reach", 0.8):
            if Utils.find("combat/alert_unable_reach"):
                Logger.log_warning("Unable to reach the target.")
                if self.config.combat['focus_on_mystery_nodes'] and target_info[2] == "mystery_node":
                    self.enemies_list.clear()
                    self.unable_handler(target_info[0:2])
                else:
                    self.blacklist.append(target_info[0:2])
                    target_info = None
                continue
            else:
                target_info_tmp = target_info
                movement_result = self.movement_handler(target_info)
                if movement_result == 1:
                    self.battle_handler()
                # This swipe for map 2-3 makes bot more likely to target key enemies blocking the boss
                if self.chapter_map == '2-3' and target_info_tmp[2] == 'mystery_node':
                    Logger.log_msg("Relocating screen of 2-3 after picking the mystery node.")
                    Utils.swipe(1000, 350, 1000, 700, 1500)

                target_info = None

                self.blacklist.clear()

                Utils.script_sleep(3)
                continue

    def clear_map_special_7_2(self):
        """ Framing 7-2 for 4 question marks with 3 or at most 4 battles. Only support one fleet!
        """ 
        question_mark_all_obtained = False
        position_boss = [956, 538]
        position_A3 = [378, 539]
        position_B3 = [569, 538]
        position_C4 = [752, 681]
        region_question_mark_A2 =[327, 348, 481, 468]
        region_question_mark_D4 =[861, 611, 1056, 754]

        block_right_clear = False
        block_left_clear = False
        block_A3_clear = False
        targeting_block_right = False
        targeting_block_left = False
        targeting_block_A3 = False
        three_fight_farming_fleet_switched = False

        region_block_right = [[1230, 232, 1388, 543], [1432, 347, 1588, 468], [1449, 473, 1616, 603]] # corresponding to F1, G2, and G3 in [x1,y1,x2,y2] format.
        region_block_left = [[467, 610, 642, 754], [677, 474, 853, 603], [649, 760, 843, 917]] # B4, C3, and C5
        region_block_A3 = [296, 472, 460, 605]


        #right_enemy_list = ['F1', 'G2', 'G3']
        #right_enemy_region = {
        #    'F1': Region(1230, 232, 1388, 543),
        #    'G2': Region(1432, 347, 1588, 468),
        #    'G3': Region(1449, 473, 1616, 603)
        #}
        #left_enemy_list = ['B4', 'C3', 'C5']
        #left_enemy_region = {
        #    'B4': Region(467, 610, 642, 754),
        #    'C3': Region(677, 474, 853, 603),
        #    'C5': Region(649, 760, 843, 917)
        #}
        #A3_region = {'A3': Region(296, 472, 460, 605)}


        self.fleet_location = None
        self.combats_done = 0
        self.kills_count = 0
        self.enemies_list.clear()
        self.mystery_nodes_list.clear()
        self.blacklist.clear()
        self.swipe_counter = 0
        Logger.log_msg("Started map clear.")
        Utils.script_sleep(2.5)

        while Utils.find("combat/fleet_lock", 0.99):
            Utils.touch_randomly(self.region["fleet_lock"])
            Logger.log_warning("Fleet lock is not supported, disabling it.")
            Utils.wait_update_screen()

        if self.config.combat['fleet_switch_at_beinning']:
            Utils.touch_randomly(self.region['button_switch_fleet'])
            if not self.reset_screen_by_anchor_point():
                Logger.log_warning("Fail to reset the screen by anchor. Force retreat and try again.")
                self.exit = 5
                self.retreat_handler()
                return True
            Utils.script_sleep(1)     

        # move to the boss position to avoid blocking A3 enemy
        # FIXME: This might fail if the initial spawns happen to block our fleet
        Utils.touch(position_boss)
        Utils.script_sleep(2.5)

        target_info = None

        while True:
            Utils.update_screen()

            if Utils.find("combat/alert_unable_battle"):
                Utils.touch_randomly(self.region['close_info_dialog'])
                self.exit = 5
            if question_mark_all_obtained and self.config.combat['retreat_after'] == 3:
                Logger.log_msg("Retreating after obtaining all question marks.")
                self.exit = 2
            if self.exit != 0:
                self.retreat_handler()
                return True
            if self.kills_count >= 3 and target_info == None and not question_mark_all_obtained:
                Logger.log_msg("Collecting question marks after 3 battles.")
                target_info = self.get_closest_target(self.blacklist, [], True, False)
                if target_info[2] == 'enemy': 
                    Logger.log_msg("No more question marks.")
                    question_mark_all_obtained = True
                    continue
                # When blocked by A3 enemy, sometime the unable_handler fail to attack A3. Therefore we explicitely do attacking A3 here.
                if target_info[2] == 'mystery_node' and not block_A3_clear and self.is_within_zone([target_info[0], target_info[1]], region_question_mark_A2):
                    self.enemies_list.clear()
                    enemies = self.get_enemies([], False)
                    for index in range(0, len(enemies)):
                        if self.is_within_zone([enemies[index][0], enemies[index][1]], region_block_A3):
                            Logger.log_warning("Targeting A2 but enemy appears at A3. Switching to targeting A3 for clearing the block.")
                            target_info[0] = enemies[index][0]
                            target_info[1] = enemies[index][1]
                            target_info[2] = 'enemy'
                            targeting_block_A3 = True
                            break
                    continue
            if self.kills_count == 3 and self.config.combat['retreat_after'] == 0 and not three_fight_farming_fleet_switched:
                # switch fleet after killing 2 enemies for 3-fight farming
                # this makes farming easier by switching to a healthy fleet
                Logger.log_msg("Fleet switching after 2 fights for easier 3-fight 7-2 farming.")
                Utils.touch_randomly(self.region['button_switch_fleet'])
                if not self.reset_screen_by_anchor_point():
                    Logger.log_warning("Fail to reset the screen by anchor. Force retreat and try again.")
                    self.exit = 5
                    self.retreat_handler()
                    return True
                three_fight_farming_fleet_switched = True
                Utils.script_sleep(1)
                continue  
            if self.kills_count >= self.kills_before_boss[self.chapter_map] and Utils.find_in_scaling_range("enemy/fleet_boss", similarity=0.9):
                Logger.log_msg("Boss fleet was found.")

                if self.config.combat['boss_fleet']:
                    if self.chapter_map == 'E-B3' or self.chapter_map == 'E-D3':
                        s = 3
                    else:
                        s = 0
                    swipes = {
                        0: lambda: Utils.swipe(960, 240, 960, 940, 300),
                        1: lambda: Utils.swipe(1560, 540, 260, 540, 300),
                        2: lambda: Utils.swipe(960, 940, 960, 240, 300),
                        3: lambda: Utils.swipe(260, 540, 1560, 540, 300)
                    }

                    Utils.touch_randomly(self.region['button_switch_fleet'])
                    Utils.wait_update_screen(2)
                    boss_region = Utils.find_in_scaling_range("enemy/fleet_boss", similarity=0.9)

                    while not boss_region:
                        if s > 3: s = 0
                        swipes.get(s)()
                        Utils.wait_update_screen(0.5)
                        boss_region = Utils.find_in_scaling_range("enemy/fleet_boss", similarity=0.9)
                        s += 1

                    # swipe to center the boss fleet on the screen
                    # first calculate the translation vector coordinates
                    translation_sign = 1 if boss_region.x < 960 else -1
                    translation_module = 175 if boss_region.y > 300 else 75
                    horizontal_translation = translation_sign * translation_module
                    angular_coefficient = -1 * ((540 - boss_region.y)/(960 - boss_region.x))
                    Utils.swipe(boss_region.x + horizontal_translation, boss_region.y + int(horizontal_translation * angular_coefficient),
                        960 + horizontal_translation, 540 + int(horizontal_translation * angular_coefficient), 300)
                    Utils.wait_update_screen()

                boss_region = Utils.find_in_scaling_range("enemy/fleet_boss", similarity=0.9)
                while not boss_region:
                    # refreshing screen to deal with mist
                    Utils.wait_update_screen(1)
                    boss_region = Utils.find_in_scaling_range("enemy/fleet_boss", similarity=0.9)

                #extrapolates boss_info(x,y,enemy_type) from the boss_region found
                boss_info = [boss_region.x + 50, boss_region.y + 25, "boss"]
                self.clear_boss(boss_info)
                continue
            if target_info == None:
                targeting_block_right, targeting_block_left, targeting_block_A3, target_info = \
                self.get_special_target_for_7_2(block_right_clear, block_left_clear, block_A3_clear, region_block_right, region_block_left, region_block_A3, targeting_block_right, targeting_block_left, targeting_block_A3)
                location_tmp = [target_info[0], target_info[1]]
                target_info = self.get_closest_target(self.blacklist, location_tmp, False, False)
                continue
            if target_info:
                #tap at target's coordinates
                Utils.touch(target_info[0:2])
                # This sleep must be long to avoid capturing the screen before game responds but also short enough to capture the "unable to reach..." dialog before it disappears.
                #Utils.script_sleep(0.5)
                Utils.update_screen()
            else:
                continue
            if Utils.find("combat/alert_unable_reach"):
                Logger.log_warning("Unable to reach the target.")
                if self.config.combat['focus_on_mystery_nodes'] and target_info[2] == "mystery_node":
                    self.enemies_list.clear()
                    self.unable_handler(target_info[0:2])
                else:
                    self.blacklist.append(target_info[0:2])
                    target_info = None
                continue
            else:
                movement_result = self.movement_handler(target_info)
                if movement_result == 1:
                    self.battle_handler()
                    Utils.script_sleep(3)
                    
                if targeting_block_right:
                    block_right_clear = True 
                if targeting_block_left:
                    block_left_clear = True 
                if targeting_block_A3:
                    block_A3_clear = True  

                self.blacklist.clear()                 

                # Move the fleet a bit to avoid possible blocking.
                fleet_location = self.get_fleet_location()
                # leaving A3 for possible blocking of question mark at A2. Detection of own fleet at A3 sometimes does not work, so this one also use target_info.
                if self.exit == 0 and self.is_within_zone(fleet_location, region_block_A3) or self.is_within_zone([target_info[0], target_info[1]], region_block_A3):
                    Utils.touch(position_B3)

                # leaving D4 for possible blocking of question mark at D2.
                if self.exit == 0 and self.is_within_zone(fleet_location, region_question_mark_D4):
                    Utils.touch(position_C4)

                target_info = None

                continue

    def reset_screen_by_anchor_point(self):
        screen_is_reset = False
        swipes = {
                    2: lambda: Utils.swipe(960, 240, 960, 940, 300),
                    0: lambda: Utils.swipe(1560, 540, 260, 540, 300),
                    1: lambda: Utils.swipe(960, 940, 960, 240, 300),
                    3: lambda: Utils.swipe(260, 540, 1560, 540, 300)
                }
        if self.chapter_map == "7-2":
            anchor_position = [1564, 677]
            anchor_tolerance = [10, 10]
        else:
            Logger.log_error('No anchor point is set for map {}.'.format(self.chapter_map))
            return False

        swipe_reset = 0
        Utils.update_screen()
        anchor = Utils.find_in_scaling_range("map_anchors/map_{}".format(self.chapter_map), similarity=0.95)
        while not screen_is_reset:
            s = 0
            while not anchor:
                swipes.get(s % 3)()
                Utils.wait_update_screen(0.5)
                anchor = Utils.find_in_scaling_range("map_anchors/map_{}".format(self.chapter_map), similarity=0.95)
                s += 1
                if s > 15:
                    Logger.log_error("Swipe too many times for searching anchor point.")
                    return False
            Utils.swipe(1920/2, 1080/2, 1920/2 + anchor_position[0] - anchor.x, 1080/2 + anchor_position[1] - anchor.y, 1500)
            swipe_reset += 1
            if swipe_reset > 15:
                Logger.log_error("Swipe too many times for resetting screen.")
                return False
            Utils.wait_update_screen(1)
            # check if resetiing screen is really successful
            anchor = Utils.find_in_scaling_range("map_anchors/map_{}".format(self.chapter_map), similarity=0.95)
            if not anchor:
                Logger.log_warning("Anchor found but cannot find anchor after swipe. Retrying...")
                continue
            if abs(anchor.x - anchor_position[0]) <= anchor_tolerance[0] and abs(anchor.y - anchor_position[1]) <= anchor_tolerance[1]:
                Logger.log_msg("Screen successfully reset.")
                screen_is_reset = True
        return True
        




    def is_within_zone(self, location, zone):
        # Determine if the location is within the zone
        # location: the array [x, y] for the position 
        # zone: the area in [x1, y1, x2, y2]
        if((location[0]-zone[0]) >= 0 and (location[0]-zone[2] <= 0) and (location[1]-zone[1]) >= 0 and (location[1]-zone[3] <= 0)):
            return True
        else:
            return False   

    def get_special_target_for_7_2(self, block_right_clear, block_left_clear, block_A3_clear, \
                                         region_block_right, region_block_left, region_block_A3,\
                                         targeting_block_right, targeting_block_left, targeting_block_A3): 

        block_target_obtained = False
        # Must clean enemies_list before using get_enemies, otherwise it will not scan for enemies.
        self.enemies_list = []
        enemies = self.get_enemies([], False)
        targets = enemies

        if not block_right_clear:
            for index_target in range(0, len(targets)):
                for index_block in range(0,3):
                    if self.is_within_zone(targets[index_target], region_block_right[index_block]):
                        index_target_chosen = index_target
                        Logger.log_info('Found right block enemy at: {}'.format(targets[index_target]))
                        targeting_block_right = True
                        block_target_obtained = True
                        break
                if block_target_obtained :
                    break
        if not block_left_clear and not block_target_obtained:
            for index_target in range(0, len(targets)):
                for index_block in range(0,3):
                    if self.is_within_zone(targets[index_target], region_block_left[index_block]):
                        index_target_chosen = index_target
                        Logger.log_info('Found left block enemy at: {}'.format(targets[index_target]))
                        targeting_block_left = True
                        block_target_obtained = True
                        break
                if block_target_obtained :
                    break
        if not block_A3_clear and not block_target_obtained:
            for index_target in range(0, len(targets)):
                if self.is_within_zone(targets[index_target], region_block_A3):
                    index_target_chosen = index_target
                    Logger.log_info('Found A3 enemy at: {}'.format(targets[index_target]))
                    targeting_block_A3 = True
                    block_target_obtained = True
                    break
        if not block_target_obtained:
            Logger.log_info('Found no block enemy, attacking the first one at: {}'.format(targets[0]))
            index_target_chosen = 0
        return targeting_block_right, targeting_block_left, targeting_block_A3, [targets[index_target_chosen][0], targets[index_target_chosen][1], 'enemy']

    def clear_boss(self, boss_info):
        Logger.log_debug("Started boss function.")

        self.enemies_list.clear()
        self.mystery_nodes_list.clear()
        self.blacklist.clear()
        self.fleet_location = None

        while True:
            #tap at boss' coordinates
            Utils.touch(boss_info[0:2])
            # This sleep cannot be short, otherwise the screen capture right below may capture a screen 
            # immediately after clicking while the game has not yet reponded. This could be the true reason 
            # why bot sometimes stuck when path to boss is blocked: if the game has not yet response to show 
            # "unable to reach..." and the screen is captured, bot would think there is no blocking! Bot then
            # blacklist boss by the movement_handler, attacking another fleet, and believe it defeat the boss.
            #
            # This issue is a reflection of the fact that the game cannot response infinitely fast. Therefore, 
            # the sleeping time here should be the time for the game to finish its response due to the touch. 
            Utils.script_sleep(0.5)
            Utils.update_screen()

# By me: it seems that lower similarity(0.8) actually make the bot unable to detect "unable to reach".
#        but it should be easier when similarity is low. Not sure why
#            if Utils.find("combat/alert_unable_reach", 0.8):
            if Utils.find("combat/alert_unable_reach"):
                Logger.log_msg("Unable to reach boss.")
                #handle boss' coordinates
                if not self.unable_handler(boss_info[0:2], boss=True):
                    return
                swipes = {
                    0: lambda: Utils.swipe(960, 240, 960, 940, 300),
                    1: lambda: Utils.swipe(1560, 540, 260, 540, 300),
                    2: lambda: Utils.swipe(960, 940, 960, 240, 300),
                    3: lambda: Utils.swipe(260, 540, 1560, 540, 300)
                }

# By me: This should be a bug. It switch fleet no matter what.
#                Utils.touch_randomly(self.region['button_switch_fleet'])
                Utils.wait_update_screen(2)
                boss_region = Utils.find_in_scaling_range("enemy/fleet_boss", similarity=0.9)
                s = 0
                while not boss_region:
                    if s > 15: 
                        Logger.log_error("Searching boss for too many times. Start retreating... ")
                        self.exit = 5
                        return
                    swipes.get(s)()
                    Utils.wait_update_screen(0.5)
                    boss_region = Utils.find_in_scaling_range("enemy/fleet_boss", similarity=0.9)
                    s += 1
                boss_info = [boss_region.x + 50, boss_region.y + 25, "boss"]
                continue
            else:
                self.movement_handler(boss_info)
                if self.battle_handler(boss=True):
                    self.exit = 1
                    Logger.log_msg("Boss successfully defeated.")
                else:
                    self.exit = 5
                    Logger.log_warning("Fleet defeated by boss.")
                #Utils.script_sleep(3)

                # A temporary solution if bot fails to capture "enable to reach..." dialog so the actual boss is not cleared.
                Utils.update_screen()
                if Utils.find_with_cropped("combat/button_retreat"):
                    Logger.log_warning("Still in battle map after attacking the boss. Re-targeting the boss.")
                    boss_region = Utils.find_in_scaling_range("enemy/fleet_boss", similarity=0.9)
                    s = 0
                    while not boss_region:
                        if s > 15: 
                            Logger.log_error("Searching boss for too many times. Start retreating... ")
                            self.exit = 5
                            return
                        swipes.get(s % 3)()
                        Utils.wait_update_screen(0.5)
                        boss_region = Utils.find_in_scaling_range("enemy/fleet_boss", similarity=0.9)
                        s += 1
                    boss_info = [boss_region.x + 50, boss_region.y + 25, "boss"]
                    continue
                else:
                    return

    def get_enemies(self, blacklist=[], boss=False):
        sim = 0.99
        filter_coordinates = True if len(self.enemies_list) == 0 else False
        if blacklist:
            Logger.log_info('Blacklist: ' + str(blacklist))
            if len(blacklist) > 2:
                self.enemies_list.clear()

        while not self.enemies_list:
            if (boss and len(blacklist) > 4) or (not boss and len(blacklist) > 3) or sim < 0.985:
                if self.swipe_counter > 3: self.swipe_counter = 0
                swipes = {
                    0: lambda: Utils.swipe(960, 240, 960, 940, 300),
                    1: lambda: Utils.swipe(1560, 540, 260, 540, 300),
                    2: lambda: Utils.swipe(960, 940, 960, 240, 300),
                    3: lambda: Utils.swipe(260, 540, 1560, 540, 300)
                }
                swipes.get(self.swipe_counter)()
                sim += 0.005
                self.swipe_counter += 1
            Utils.update_screen()

            if self.use_intersection:
                base_region_type = Region(60, 60, 100, 100)
                base_region_level = Region(-60, -80, 100, 100)
                single_triangle = map(lambda coords: Region(coords[0].item() + base_region_type.x, coords[1].item() + base_region_type.y,
                    base_region_type.w, base_region_type.h), Utils.find_all('enemy/enemyt1', sim - 0.04, useMask=True))
                double_triangle = map(lambda coords: Region(coords[0].item() + base_region_type.x, coords[1].item() + base_region_type.y,
                    base_region_type.w, base_region_type.h), Utils.find_all('enemy/enemyt2', sim - 0.075, useMask=True))
                triple_triangle = map(lambda coords: Region(coords[0].item() + base_region_type.x, coords[1].item() + base_region_type.y,
                    base_region_type.w, base_region_type.h), Utils.find_all('enemy/enemyt3', sim - 0.075, useMask=True))
                lv_enemies = list(map(lambda coords: Region(coords[0].item() + base_region_level.x, coords[1].item() + base_region_level.y,
                    base_region_level.w, base_region_level.h), Utils.find_all('enemy/enemylv', sim - 0.04, useMask=True)))
                t1_enemies = []
                for st in single_triangle:
                    t1_enemies.extend(map(st.intersection, lv_enemies))
                t1_enemies = filter(None, t1_enemies)
                t2_enemies = []
                for dt in double_triangle:
                    t2_enemies.extend(map(dt.intersection, lv_enemies))
                t2_enemies = filter(None, t2_enemies)
                t3_enemies = []
                for tt in triple_triangle:
                    t3_enemies.extend(map(tt.intersection, lv_enemies))
                t3_enemies = filter(None, t3_enemies)

                intersections = []
                intersections.extend(t1_enemies)
                intersections.extend(t2_enemies)
                intersections.extend(t3_enemies)
                # filter duplicate intersections by intersecting them
                filtered_intersections = []
                while intersections:
                    region = intersections.pop(0)
                    new_intersections = []
                    for item in intersections:
                        res = region.intersection(item)
                        if res:
                            region = res
                        else:
                            new_intersections.append(item)
                    intersections = new_intersections
                    filtered_intersections.append(region)
                enemies_coords = map(Region.get_center, filtered_intersections)
                # filter coordinates inside prohibited regions
                for p_region in self.prohibited_region.values():
                    enemies_coords = [x for x in enemies_coords if (not p_region.contains(x))]

                self.enemies_list = [x for x in enemies_coords if (not self.filter_blacklist(x, blacklist))]

            else:
                l1 = list(map(lambda x:[x[0] - 3, x[1] - 27], Utils.find_all_with_resize('enemy/fleet_level', sim - 0.025, useMask=True)))
                Logger.log_debug("L1: " +str(l1))
                l2 = list(map(lambda x:[x[0] + 75, x[1] + 110], Utils.find_all_with_resize('enemy/fleet_1_down', sim - 0.02)))
                Logger.log_debug("L2: " +str(l2))
                l3 = list(map(lambda x:[x[0] + 75, x[1] + 90], Utils.find_all_with_resize('enemy/fleet_2_down', sim - 0.02)))
                Logger.log_debug("L3: " +str(l3))
                l4 = list(map(lambda x:[x[0] + 75, x[1] + 125], Utils.find_all_with_resize('enemy/fleet_3_up', sim - 0.035)))
                Logger.log_debug("L4: " +str(l4))
                l5 = list(map(lambda x:[x[0] + 75, x[1] + 100], Utils.find_all_with_resize('enemy/fleet_3_down', sim - 0.035)))
                Logger.log_debug("L5: " +str(l5))
                l6 = list(map(lambda x:[x[0] + 75, x[1] + 110], Utils.find_all_with_resize('enemy/fleet_2_up', sim - 0.025)))
                Logger.log_debug("L6: " +str(l6))
                enemies_coords = l1 + l2 + l3 + l4 + l5 + l6
                # filter coordinates inside prohibited regions
                for p_region in self.prohibited_region.values():
                    enemies_coords = [x for x in enemies_coords if (not p_region.contains(x))]
                self.enemies_list = [x for x in enemies_coords if (not self.filter_blacklist(x, blacklist))]

            if self.config.combat['siren_elites']:
                l7 = Utils.find_siren_elites()
                # filter coordinates inside prohibited regions
                for p_region in self.prohibited_region.values():
                    l7 = [x for x in l7 if (not p_region.contains(x))]
                l7 = [x for x in l7 if (not self.filter_blacklist(x, blacklist))]
                Logger.log_debug("L7 " +str(l7))
                self.enemies_list.extend(l7)

            sim -= 0.005

        if filter_coordinates:
            self.enemies_list = Utils.filter_similar_coords(self.enemies_list, distance=67)
        return self.enemies_list

    def get_mystery_nodes(self, blacklist=[], boss=False):
        """Method which returns a list of mystery nodes' coordinates.
        """
        if len(blacklist) > 2:
            self.mystery_nodes_list.clear()


        if len(self.mystery_nodes_list) == 0 and not Utils.find('combat/question_mark', 0.9):
            # if list is empty and a question mark is NOT found
            return self.mystery_nodes_list
        else:
            # list has elements or list is empty but a question mark has been found
            filter_coordinates = True if len(self.mystery_nodes_list) == 0 else False
            sim = 0.95

            while not self.mystery_nodes_list and sim > 0.93:
                Utils.update_screen()

                l1 = list(map(lambda x:[x[0], x[1] + 140], Utils.find_all_with_resize('combat/question_mark', sim)))

                # filter coordinates inside prohibited regions
                for p_region in self.prohibited_region.values():
                    l1 = [x for x in l1 if (not p_region.contains(x))]
                l1 = [x for x in l1 if (not self.filter_blacklist(x, blacklist))]

                self.mystery_nodes_list = l1
                sim -= 0.005

            if filter_coordinates:
                self.mystery_nodes_list = Utils.filter_similar_coords(self.mystery_nodes_list)

            return self.mystery_nodes_list

    def filter_blacklist(self, coord, blacklist):
        for y in blacklist:
            if abs(coord[0] - y[0]) < 65 and abs(coord[1] - y[1]) < 65:
                return True
        return False

    def get_fleet_location(self):
        """Method to get the fleet's current location. Note it uses the green
        fleet marker to find the location but returns around the area of the
        feet of the flagship

        Returns:
            array: An array containing the x and y coordinates of the fleet's
            current location.
        """
        if not self.fleet_location:
            coords = [0, 0]
            count = 0

            while coords == [0, 0]:
                Utils.update_screen()
                count += 1

                if count > 4:
                    Utils.swipe(960, 540, 960, 540 + 150 + count * 20, 100)
                    Utils.update_screen()

                if Utils.find('combat/fleet_ammo', 0.8):
                    coords = Utils.find('combat/fleet_ammo', 0.8)
                    coords = [coords.x + 140, coords.y + 225 - count * 20]
                elif Utils.find('combat/fleet_arrow', 0.9):
                    coords = Utils.find('combat/fleet_arrow', 0.9)
                    coords = [coords.x + 25, coords.y + 320 - count * 20]

                if count > 4:
                    Utils.swipe(960, 540 + 150 + count * 20, 960, 540, 100)
                elif (math.isclose(coords[0], 160, abs_tol=30) & math.isclose(coords[1], 142, abs_tol=30)):
                    coords = [0, 0]

            self.fleet_location = coords

        return self.fleet_location

    def get_closest_target(self, blacklist=[], location=[], mystery_node=False, boss=False):
        """Method to get the enemy closest to the specified location. Note
        this will not always be the enemy that is actually closest due to the
        asset used to find enemies and when enemies are obstructed by terrain
        or the second fleet

        Args:
            blacklist(array, optional): Defaults to []. An array of
            coordinates to exclude when searching for the closest enemy

            location(array, optional): Defaults to []. An array of coordinates
            to replace the fleet location.

        Returns:
            array: An array containing the x and y coordinates of the closest
            enemy to the specified location
        """
        fleet_location = self.get_fleet_location()

        if location == []:
           location = fleet_location

        if mystery_node and self.chapter_map[0].isdigit():
            mystery_nodes = self.get_mystery_nodes(blacklist, boss)
            if self.config.combat['focus_on_mystery_nodes'] and len(mystery_nodes) > 0:
                # giving mystery nodes top priority and ignoring enemies
                targets = mystery_nodes
                Logger.log_info("Prioritizing mystery nodes.")
            else:
                # mystery nodes are valid targets, same as enemies
                enemies = self.get_enemies(blacklist, boss)
                targets = enemies + mystery_nodes
        else:
            # target only enemy mobs
            targets = self.get_enemies(blacklist, boss)

        closest = targets[Utils.find_closest(targets, location)[1]]

        Logger.log_info('Current location is: {}'.format(fleet_location))
        Logger.log_info('Targets found at: {}'.format(targets))
        Logger.log_info('Closest target is at {}'.format(closest))

        if closest in self.enemies_list:
            x = self.enemies_list.index(closest)
# By me:
# clear the list such that the bot search enemy every turn
#            del self.enemies_list[x]
            self.enemies_list.clear()
            target_type = "enemy"
        else:
            x = self.mystery_nodes_list.index(closest)
# By me:
# clear the list such that the bot search mystery node every turn
#            del self.mystery_nodes_list[x]
            self.mystery_nodes_list.clear()
            target_type = "mystery_node"

        return [closest[0], closest[1], target_type]

    def check_movement_threads(self):
        thread_list = []
        # essential threads
        thread_check_alert_info = Thread(
            target=self.check_movement_threads_func, args=("menu/alert_info",))
        thread_check_menu_formation = Thread(
            target=self.check_movement_threads_func, args=("combat/menu_formation",))
        thread_check_menu_loading = Thread(
            target=self.check_movement_threads_func, args=("combat/menu_loading",))
        thread_list.extend([thread_check_alert_info, thread_check_menu_formation, thread_check_menu_loading])

        # threads needed for non-event maps (where mystery nodes appears)
        if self.chapter_map[0].isdigit():
            thread_check_alert_ammo = Thread(
                target=self.check_movement_threads_func, args=("combat/alert_ammo_supplies",))
            thread_check_item_found = Thread(
                target=self.check_movement_threads_func, args=("menu/item_found",))
            thread_list.extend([thread_check_alert_ammo, thread_check_item_found])

            # threads needed for story maps without clearing mode enabled
            if not self.config.combat['clearing_mode']:
                thread_check_button_evade = Thread(
                    target=self.check_movement_threads_func, args=("combat/button_evade",))
                thread_check_failed_evade = Thread(
                    target=self.check_movement_threads_func, args=("combat/alert_failed_evade",))
                thread_list.extend([thread_check_button_evade, thread_check_failed_evade])

        Utils.multithreader(thread_list)

        return self.movement_event

    def check_movement_threads_func(self, event):
        self.movement_event[event] = (
            True
            if (Utils.find(event))
            else False)
