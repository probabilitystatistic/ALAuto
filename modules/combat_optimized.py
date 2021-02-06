import math
import string
import cv2
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
        self.map_similarity = 0.85

        self.kills_count = 0
        self.dedicated_map_strategy = False
        self.automatic_sortie = True
        self.enter_automatic_battle = False
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
            'automation_repeat_button': Region(1300, 820, 100, 50),
            'automation_search_enemy_switch': Region(1800, 820, 100, 30),
            'fleet_lock': Region(1790, 750, 130, 30),
            'open_strategy_menu': Region(1797, 617, 105, 90),
            'disable_subs_hunting_radius': Region(1655, 615, 108, 108),
            'close_strategy_menu': Region(1590, 615, 40, 105),
            'menu_button_battle': Region(1517, 442, 209, 206),
            'map_summary_go': Region(1289, 743, 280, 79),
            'fleet_menu_go': Region(1485, 872, 200, 74),
            'combat_ambush_evade': Region(1493, 682, 208, 56),
            'combat_automation': Region(20, 50, 200, 35),
            'combat_com_confirm': Region(848, 740, 224, 56),
            'combat_end_confirm': Region(1613, 947, 30, 25), # x=1613~1643, y=947~972 for safe touch
            'combat_dismiss_surface_fleet_summary': Region(790, 950, 250, 65),
            'emergency_repair_in_map': Region(1800, 620, 80, 100),
            'menu_combat_start': Region(1578, 921, 270, 70),
            'tap_to_continue': Region(661, 840, 598, 203),
            'close_info_dialog': Region(1326, 274, 35, 35),
            'dismiss_ship_drop': Region(200, 200, 200, 200),
            #'dismiss_ship_drop': Region(1228, 103, 692, 500),
            'retreat_button': Region(1130, 985, 243, 60),
            'dismiss_commission_dialog': Region(1065, 732, 235, 68),
            'normal_mode_button': Region(88, 990, 80, 40),
            'main_battleline': Region(500, 500, 50, 50),
            'map_nav_right': Region(1831, 547, 26, 26),
            'map_nav_left': Region(65, 547, 26, 26),
            'event_button': Region(1770, 250, 75, 75),
            'lock_ship_button': Region(1086, 739, 200, 55),
            'clear_second_fleet': Region(1690, 473, 40, 40),
            'button_switch_fleet': Region(1430, 985, 240, 60),
            'menu_nav_back': Region(54, 57, 67, 67),
            'battle_handler_safe_touch': Region(40, 180, 110, 110),
            'battle_handler_defeat_close_touch': Region(880, 900, 100, 40),
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

        self.key_map_region = {
            '2-1':{'B3': Region(668, 540, 189, 140),
                   'C1': Region(863, 288, 183, 119),
                   'C3': Region(861, 540, 189, 140),
                   'D3': Region(1060, 540, 189, 140),
                   'E1': Region(1233, 288, 167, 119),
                   'E2': Region(1247, 408, 170, 132),
                   'E3': Region(1263, 540, 174, 140),
                   'F2': Region(1436, 409, 169, 131),
                   'F3': Region(1461, 540, 171, 140)
            },
            'E-C1':{'C6': Region(559, 762, 200, 156),
                    'D6': Region(764, 760, 210, 160),
                    'F5': Region(1187, 613, 185, 140)
            },
            'E-C3':{'C1': Region(960, 273, 170, 114),
                    'D1': Region(1142, 274, 170, 114),
                    'F2': Region(1532, 391, 135, 125)
            },
            'E-D3':{'C1': Region(930, 110, 100, 60),
                    'D2': Region(1100, 200, 110, 80),
                    'F7': Region(1560, 870, 140, 60)
            }
        }

        self.swipe_counter = 0
        self.fleet_switch_due_to_morale= False
        self.fleet_switch_index = -1
        self.targeting_2_1_D3 = False


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
        slot_to_switch_fleet = self.config.combat['slot_for_rotation']
        fleet_slot_position = [[1650, 393], [1650, 593]]
        first_fleet_slot_position = [1650, 393]
        second_fleet_slot_position = [1650, 593]
        fleet_slot_separation = 64
        oil_delta = 0
        gold_delta = 0


        # get to map
        map_region = self.reach_map()
        
        Utils.touch_randomly_ensured(map_region, "menu/attack", ["combat/button_go"] , need_initial_screen=True, response_time=0.5, stable_check_frame=2)

        while True:
            #Utils.wait_update_screen()
            Utils.update_screen()

            if self.exit == 1 or self.exit == 2 or self.exit == 6:
                if not self.exit == 6:
                    self.stats.increment_combat_done()
                time_passed = datetime.now() - self.start_time
                if self.stats.combat_done % self.config.combat['retire_cycle'] == 0 or ((self.config.commissions['enabled'] or \
                    self.config.dorm['enabled'] or self.config.academy['enabled']) and time_passed.total_seconds() > 3600) or \
                        not Utils.check_oil(self.config.combat['oil_limit']):
                        break
                else:
                    self.exit = 0
                    Logger.log_msg("Repeating map {}.".format(self.chapter_map))
                    Utils.touch_randomly_ensured(map_region, "menu/attack", ["combat/button_go"], response_time=0.5, stable_check_frame=2)
                    """
                    while True:
                        Utils.touch_randomly(map_region)
                        Utils.wait_update_screen()
                        if Utils.find("combat/button_go"):
                            break
                    """
                    continue
            if self.exit > 2:
                self.stats.increment_combat_attempted()
                break
            if Utils.find_with_cropped("combat/button_go"):
                Logger.log_debug("Found map summary go button.")
                Utils.touch_randomly_ensured(self.region["map_summary_go"], "combat/button_go", ["combat/menu_select_fleet"], stable_check_frame=1)
                #Utils.wait_update_screen()
            if Utils.find("combat/menu_fleet") and (lambda x:x > 414 and x < 584)(Utils.find("combat/menu_fleet").y) and not self.config.combat['boss_fleet']:
                if not self.chapter_map[0].isdigit() and string.ascii_uppercase.index(self.chapter_map[2:3]) < 1 or self.chapter_map[0].isdigit():
                    Logger.log_msg("Removing second fleet from fleet selection.")
                    Utils.touch_randomly(self.region["clear_second_fleet"])
            if Utils.find_with_cropped("combat/menu_select_fleet"):
                Logger.log_debug("Found fleet select go button.")
                # Rotating fleet due to low morale
                if(self.fleet_switch_due_to_morale):
                    Logger.log_warning("Switching fleet due to low morale.")
                    self.fleet_switch_index = self.fleet_switch_index + 1
                    self.fleet_switch_due_to_morale= False
                    fleet_to_switch_to = fleet_switch_candidate_for_morale[self.fleet_switch_index % len(fleet_switch_candidate_for_morale)]
                    Logger.log_msg("Switch to fleet {} for the {}th slot".format(fleet_to_switch_to, slot_to_switch_fleet))
                    #if not self.config.combat['boss_fleet']:
                    #    self.select_fleet(first_slot_fleet = fleet_switch_candidate_for_morale[self.fleet_switch_index % len(fleet_switch_candidate_for_morale)])
                    #else:
                    #    if not self.select_fleet(first_slot_fleet = fleet_switch_candidate_for_morale[self.fleet_switch_index % len(fleet_switch_candidate_for_morale)], second_slot_fleet=??):
                    #       Logger.log_warning("Abnormal fleet order.")
                    if slot_to_switch_fleet == 1:
                        Utils.touch_randomly(self.region["first_slot_choose"])
                    if slot_to_switch_fleet == 2:
                        Utils.touch_randomly(self.region["second_slot_choose"])
                    Utils.script_sleep(0.1)
                    target_fleet_vertical_position = fleet_slot_position[slot_to_switch_fleet - 1][1] + fleet_slot_separation*(fleet_to_switch_to - 1)
                    Utils.touch([fleet_slot_position[slot_to_switch_fleet - 1][0], target_fleet_vertical_position])
                    Utils.script_sleep(0.1)
                if self.automatic_sortie:
                    Utils.touch_randomly_ensured(self.region["fleet_menu_go"], "combat/menu_select_fleet", ["combat/automation_search_enemy", "combat/alert_morale_low", "menu/button_confirm"], response_time=1)
                else:
                    Utils.touch_randomly_ensured(self.region["fleet_menu_go"], "combat/menu_select_fleet", ["combat/button_retreat", "combat/alert_morale_low", "menu/button_confirm"], response_time=2)
            if Utils.find_with_cropped("combat/button_retreat") or (self.automatic_sortie and Utils.find_with_cropped("combat/automation_search_enemy")):
                Logger.log_debug("Found retreat button, starting clear function.")
                oil, gold = Utils.get_oil_and_gold()
                oil = oil + 10 # admission fee
                if (self.chapter_map[0] == '7' and self.chapter_map[2] == '2' and self.config.combat['clearing_mode'] and self.config.combat['focus_on_mystery_nodes']):
                    Logger.log_debug("Started special 7-2 farming.")
                    self.dedicated_map_strategy = True
                    if not self.clear_map_special_7_2():
                   	    self.stats.increment_combat_attempted()
                   	    break
                elif self.chapter_map == '2-1' and self.config.combat['clearing_mode'] and self.config.combat['focus_on_mystery_nodes']:
                    Logger.log_debug("Started special 2-1 farming.")
                    self.dedicated_map_strategy = True
                    if not self.clear_map_special_2_1():
                        self.stats.increment_combat_attempted()
                        break
                else:
                    if not self.clear_map():
                        self.stats.increment_combat_attempted()
                        break
                Utils.wait_update_screen()
                # excluding the data from terms for fleet rotation due to moral
                if not self.exit == 6: 
                    oil_delta, gold_delta = Utils.get_oil_and_gold()
                    self.stats.read_oil_and_gold_change_from_battle(oil_delta - oil, gold_delta - gold)
            if Utils.find_with_cropped("menu/button_sort"):
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
            if Utils.find_with_cropped("combat/alert_morale_low"):
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

            if Utils.find_with_cropped("menu/button_confirm"):
                Logger.log_msg("Found commission info message.")
                self.stats.increment_commissions_occurance()
                Utils.touch_randomly(self.region["combat_com_confirm"])
                Utils.wait_update_screen()

        #Utils.script_sleep(1)
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
        if Utils.find_with_cropped("menu/button_battle"):
            Logger.log_debug("Found menu battle button.")
            Utils.touch_randomly_ensured(self.region["menu_button_battle"], "", ["menu/attack"], response_time=1, stable_check_frame=1)
            Utils.touch_randomly_ensured(self.region["main_battleline"], "", ["combat/hardmode", "combat/normalmode"], response_time=1)
            Utils.wait_update_screen(1)

        # correct map mode
        if not self.chapter_map[0].isdigit():
            letter = self.chapter_map[2]
            event_maps = ['A', 'B', 'S', 'C', 'D']

            Utils.touch_randomly(self.region['event_button'])
            Utils.wait_update_screen(1)

#           By me: comment out the switching to normal mode for event map so I can farm D2 in Iris of light and dark.
#                Utils.touch_randomly(self.region['normal_mode_button'])
#                Utils.wait_update_screen(1)
        # disable the check for normal mode so as to do daily hard runs
        #else:
            #if Utils.find_with_cropped("menu/button_normal_mode"):
                #Logger.log_debug("Disabling hard mode.")
                #Utils.touch_randomly(self.region['normal_mode_button'])
                #Utils.wait_update_screen(1)

        map_region = Utils.find('maps/map_{}'.format(self.chapter_map), self.map_similarity)
        if map_region != None:
            Logger.log_msg("Found specified map.")
            return map_region
        else:
            # navigate map selection menu
            if not self.chapter_map[0].isdigit():
                if (self.chapter_map[2] == 'A' or self.chapter_map[2] == 'C') and \
                    (Utils.find('maps/map_E-B1', self.map_similarity) or Utils.find('maps/map_E-D1', self.map_similarity)):
                    Utils.touch_randomly(self.region['map_nav_left'])
                    Logger.log_debug("Swiping to the left")
                elif (self.chapter_map[2] == 'B' or self.chapter_map[2] == 'D') and \
                    (Utils.find('maps/map_E-A1', self.map_similarity) or Utils.find('maps/map_E-C1', self.map_similarity)):
                    Utils.touch_randomly(self.region['map_nav_right'])
                    Logger.log_debug("Swiping to the right")
            else:
                _map = 0
                for x in range(1, 14):
                    if Utils.find("maps/map_{}-1".format(x), self.map_similarity, print_info=True):
                        _map = x
                        break
                if _map != 0:
                    taps = int(self.chapter_map.split("-")[0]) - _map
                    for x in range(0, abs(taps)):
                        if taps >= 1:
                            Utils.touch_randomly_ensured(self.region['map_nav_right'], "", [], response_time=0.1)
                            Logger.log_debug("Swiping to the right")
                            #Utils.script_sleep()
                        else:
                            Utils.touch_randomly_ensured(self.region['map_nav_left'], "", [], response_time=0.1)
                            Logger.log_debug("Swiping to the left")
                            #Utils.script_sleep()

        Utils.wait_update_screen()
        map_region = Utils.find('maps/map_{}'.format(self.chapter_map), self.map_similarity, print_info=True)
        if map_region == None:
            Logger.log_error("Cannot find the specified map, please move to the world where it's located.")
        count = 0
        while map_region == None:
            map_region = Utils.find('maps/map_{}'.format(self.chapter_map), self.map_similarity, print_info=True)
            Utils.wait_update_screen(1)
            count += 1
            if count >= 600:
                Logger.log_error("Wait for correct map for too long. Terminating...")
                exit()

        Logger.log_msg("Found specified map.")
        return map_region


    def battle_handler(self, boss=False):
        Logger.log_msg("Starting combat.")

        # enhancecement and retirement flags
        enhancement_failed = False
        retirement_failed = False
        count = 0
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
            elif Utils.find_with_cropped("combat/button_retreat"):
                Logger.log_error('battle_handler called but somehow retreat button is detected.')
                Logger.log_error('Forcing retreat...')
                self.exit = 5
                return False
            else:
                Utils.touch_randomly(self.region["menu_combat_start"])
                Utils.script_sleep(1)
            count += 1
            if count >= 100:
                Logger.log_error('Too many loops in battle_handler for searching "combat/menu_loading".')
                Logger.log_error('Forcing retreat...')
                self.exit = 5
                return False

        Utils.script_sleep(4)

        defeat = False
        automation_corrected = False
        count = 0
        # in battle or not
        while True:
            Utils.update_screen()
            if Utils.find_with_cropped("combat/combat_pause", 0.7):
                Logger.log_debug("In battle.")
            else:
                if Utils.find_with_cropped("combat/menu_touch2continue", 0.9):
                    Logger.log_debug("Battle finished.")
                    break
            if not automation_corrected and Utils.find_with_cropped("combat/automation_disengage", similarity=0.9):
                Utils.touch_randomly(self.region['combat_automation'])
                automation_corrected = True
            count += 1
            if count >= 300:
                Logger.log_error("Battle time is too long. Assume battle finished")
                break
            Utils.script_sleep(1,0)

        # battle summary
        # this will keep clicking the screen until the end of battle summary(where the orange "confirm" button resides) or lock screen for new ships.
        # no detection for items or ship drop(except new ship inquiring if locking)
        Logger.log_msg("Battle summary")
        response = Utils.touch_randomly_ensured(self.region['battle_handler_safe_touch'], "", 
                                                ["combat/button_confirm", "combat/alert_lock"], 
                                                similarity_after=0.9, response_time=0.1)

        # lock a new received ship and cocntinue to the end of battle summary
        if response == 2:
            Logger.log_msg("Locking received new ship.")
            # this will keep clicking the screen until the end of battle summary
            Utils.touch_randomly_ensured(self.region['lock_ship_button'], "", ["combat/button_confirm"],
                                         response_time=0.1)

        # press the orange "confirm" button at the end of battle summary
        """
            Keep in mind bot may mis-judge a normal enemy as boss so "combatt/button_retreat" is still included 
                in the possible outcome of the click

            For the region of the orange "confirm" button in x=1613~1643, y=947~972, bot will not mis-click the 
                "switch over" button(for switching fleet) in the stage screen or the "commission" button(for entering 
                commission menu) in the "menu/attack" screen.

            However it could mis-dismiss the info screen noting a new ergent commission. Currently this is avoided by
                checking if the screen is stable.

            Currently info screens noting forced fleet switch or unable-to-battle due to defeat are assumed to be safe
                from the misclick.

            It is assumed no commission will appear if defeated.

            Note that when a commision popups after killing a mob fleet, "menu/button_confirm" and "menu/button_retreat" 
                both appears in the screen. As bot needs to click the confirm button of the commission, the detection of
                "menu/button_confirm" must be placed before "menu/button_retreat" in the ref_after_touch list. Otherwise
                bot will detect "menu/button_retreat" and thinks there is no commission(and stuck). Similarly in case of
                killing the boss, "menu/button_confirm" and "menu/attack" both appear.

        """
        #Logger.enable_debugging(Logger)
        if not self.chapter_map[0].isdigit() and boss:
            """
            Special treatment for event map giving items after clearing the map
                note that when item is given retreat button can generally be detected(similarity~0.94) so here we 
                ignore the retreat button. This is fine as it is a boss fight.
            Also note that the response is carefully alligned such that the they match up with conventional cases.
            """
            response = Utils.touch_randomly_ensured(self.region["combat_end_confirm"], "", 
                                                    ["menu/item_found","menu/button_confirm", 
                                                     "menu/attack", "combat/defeat_close_button"], 
                                                    response_time=3, similarity_after=0.9,
                                                    stable_check_frame=2)
            # extra click to handle the item found case
            if response == 1:
                response = Utils.touch_randomly_ensured(self.region['battle_handler_safe_touch'], "", 
                                                        ["menu/button_confirm", "menu/attack"], 
                                                        response_time=3, similarity_after=0.95,
                                                        stable_check_frame=2)
                # to match up the response with the conventional cases
                if response == 2:
                    response = 3
        else:
            # it seems that defeat is sometimes not detected in 7-2
            response = Utils.touch_randomly_ensured(self.region["combat_end_confirm"], "", 
                                                    ["menu/button_confirm", "combat/button_retreat", 
                                                     "menu/attack", "combat/defeat_close_button"], 
                                                    response_time=3, similarity_after=0.9,
                                                    stable_check_frame=2)
        #Logger.disable_debugging(Logger)

        if response == 4:
            defeat = True
            Logger.log_warning("Fleet was defeated.")
            # possible outcome: the fleet can still battle; the fleet cannot battle; no other fleet and lose
            response = Utils.touch_randomly_ensured(self.region["battle_handler_defeat_close_touch"], "", 
                                                    ["combat/button_retreat", "combat/alert_fleet_cannot_be_formed",
                                                     "combat/alert_unable_battle"
                                                    ], 
                                                    response_time=2,
                                                    stable_check_frame=1)

        # post-summary
        if defeat:
            """ retreat or not(controlled by self.exit) in various cases(according to original battle_handler):
            unable to battle(no remaining fleet) = y
            fleet cannot be formed, boss fight = y
            fleet cannot be formed, mob fight = n (this indicates 2 fleets are sent to the stage)
            combat/button_retreat(flag ship of current fleet sunk but backline is still alive) = y
            """
            if response == 1:
                Logger.log_debug("Flag ship is sunk but backline is still alive. Proceed to retreat.")
                self.exit = 5
            elif response == 2:
                Logger.log_debug("Current fleet is destroyed and automatically switched.")
                Utils.touch_randomly_ensured(self.region['close_info_dialog'], "", ["combat/button_retreat"],
                                             stable_check_frame=2)
                self.enemies_list.clear()
                self.mystery_nodes_list.clear()
                self.blacklist.clear()
                if boss:
                    Logger.log_debug("Proceed to retreat.")
                    self.exit = 5
            elif response == 3:
                Logger.log_debug("All fleets are destroyed. Back to chapter map.")
                Utils.touch_randomly_ensured(self.region['close_info_dialog'], "", ["menu/attack"],
                                             stable_check_frame=2)
                self.exit = 5
            return False
        else:
            if response == 1:
                Logger.log_msg("Found commission info message.")
                self.stats.increment_commissions_occurance()
                if boss:
                    Utils.touch_randomly_ensured(self.region["combat_com_confirm"], "", ["menu/attack"],
                                                 stable_check_frame=1)
                else:
                    Utils.touch_randomly_ensured(self.region["combat_com_confirm"], "", ["combat/button_retreat"],
                                                 stable_check_frame=1)
            elif  response == 3:
                Logger.log_debug("Stage was cleared.")
            self.combats_done += 1
            self.kills_count += 1
            Logger.log_msg("Combat ended.")
            return True

    def movement_handler(self, target_info, try_touch = True):
        """
        Method that handles the fleet movement until it reach its target (mystery node or enemy node).
        If the coordinates are wrong, they will be blacklisted and another set of coordinates to work on is obtained.
        If the target is a mystery node and what is found is ammo, then the method will fall in the blacklist case
        and search for another enemy: this is inefficient and should be improved, but it works.

        Args:
            target_info (list): coordinate_x, coordinate_y, type. Describes the selected target.
        Returns:
            (int): 1 if a fight is needed, 2 if retreat is needed, otherwise 0.
        """
        """
        Known bug: In the case when target arrow is found, if a fleet passes a mystery node yielding ammo 
        but not detected, the fleet will just stopped. This results in blacklisting the reachable target.
        """
        stationary_screen_check = True
        stationary_screen_check_frame = 20
        stationary_screen_check_similarity = 0.9
        Logger.log_msg("Moving towards objective.")
        count = 0
        location = [target_info[0], target_info[1]]
        # set up region to search the green arrow at destination
        # assume target_info gives the center of the target
        # this method would still mis-judge if the target is 2 tiles above the current fleet(the arrow of current fleet could be mis-judged as target arrow)
        if try_touch:
            arrow_found = False
        else:
            arrow_found = True
        target_arrow_search_region = Utils.get_region_for_target_arrow_search(location)
        fleet_arrival_detection_region = Utils.get_region_for_fleet_arrival_detection(location)
        #print("fleet_arrival_detection_region:", fleet_arrival_detection_region.x, fleet_arrival_detection_region.y, fleet_arrival_detection_region.w, fleet_arrival_detection_region.h)
        count_fleet_at_target_location = 0
        use_emergency_repair = False
        if self.chapter_map == '7-2' and self.config.combat['retreat_after'] != 3:
            use_emergency_repair = True
        #Utils.script_sleep(1)
        stationary_screen_counter = 0 
        stationary_screen_stable_frame_counter = 0

        while True:
            Utils.update_screen()
            if stationary_screen_check:
                if stationary_screen_counter == 0:
                    previous_screen = Utils.screen
                else:
                    match = cv2.matchTemplate(previous_screen, Utils.screen, cv2.TM_CCOEFF_NORMED)
                    value = cv2.minMaxLoc(match)[1]
                    if value >= stationary_screen_check_similarity:
                        stationary_screen_stable_frame_counter += 1
                    else:
                        stationary_screen_stable_frame_counter = 0
                    if stationary_screen_stable_frame_counter >= stationary_screen_check_frame:
                        Logger.log_msg('Stationary screen detected. Re-issuing the command...')
                        arrow_found = False
                        stationary_screen_stable_frame_counter = 0
                        #Utils.save_screen('stationary_screen')
                    previous_screen = Utils.screen
                stationary_screen_counter += 1
                if stationary_screen_counter >= 1000:
                    Logger.log_error('Too many loops in cheching stationary screen in movement_handler. Exiting...')

            event = self.check_movement_threads()

            if not arrow_found and Utils.find_with_cropped("combat/fleet_arrow", dynamical_region = target_arrow_search_region):
                Logger.log_msg('Target arrow found.')
                arrow_found = True
            #if self.chapter_map[0].isdigit() and event["combat/alert_ammo_supplies"]:
            if self.chapter_map == '6-1' and Utils.find_with_cropped('combat/alert_unable_reach', similarity=0.9):
                Logger.log_msg("Cannot reach the target")
                return -1
            if Utils.find_with_cropped("combat/alert_ammo_supplies", similarity=0.9):
                # from time to time ammo supply similarity could go below 0.95
                Logger.log_msg("Received ammo supplies")
                if target_info[2] == 'enemy' or target_info[2] == 'empty':
                    arrow_found = False
                # wait for the info box to disappear
                Utils.script_sleep(2)
                if target_info[2] == "mystery_node":
                    Logger.log_msg("Target reached.")
                    self.fleet_location = target_info[0:2]
                    return 0
                continue
            if self.targeting_2_1_D3 and self.key_map_region['2-1']['D3'].contains(self.get_fleet_location()):
                """
                FL = self.get_fleet_location()
                print('D3 region:', self.key_map_region['2-1']['D3'].x, self.key_map_region['2-1']['D3'].y, self.key_map_region['2-1']['D3'].w, self.key_map_region['2-1']['D3'].h)
                print('Fleet location:', FL)
                #if self.key_map_region['2-1']['D3'].contains(self.get_fleet_location()):
                if self.key_map_region['2-1']['D3'].contains(FL):
                    Logger.log_msg('Target empty tile arrived.')
                    self.targeting_2_1_D3 = False
                    return 0
                """
                Logger.log_msg('Target empty tile arrived.')
                self.targeting_2_1_D3 = False
                return 0
            if (self.chapter_map[0].isdigit() and not self.config.combat['clearing_mode']) and event["combat/button_evade"]:
                Logger.log_msg("Ambush was found, trying to evade.")
                Utils.touch_randomly(self.region["combat_ambush_evade"])
                arrow_found = False
                Utils.script_sleep(0.5)
                continue
            if (self.chapter_map[0].isdigit() and not self.config.combat['clearing_mode']) and event["combat/alert_failed_evade"]:
                Logger.log_warning("Failed to evade ambush.")
                self.kills_count -= 1
                arrow_found = False
                Utils.touch_randomly(self.region["menu_combat_start"])
                self.battle_handler()
                continue
            if self.chapter_map[0].isdigit() and event["menu/item_found"]:
                Logger.log_msg("Item found on node.")
                Utils.touch_randomly(self.region['tap_to_continue'])
                if target_info[2] == 'enemy' or target_info[2] == 'boss' or target_info[2] == 'empty':
                    arrow_found = False
                if Utils.find_with_cropped("combat/menu_emergency"): # note that current screen saved is still the old screen receiving an item
                    Utils.script_sleep(1)
                    if use_emergency_repair:
                        Utils.touch_randomly_ensured(self.region['emergency_repair_in_map'], "", ["combat/button_use_repair"], response_time=1)
                        Utils.find_and_touch_with_cropped("combat/button_use_repair")
                        Logger.log_msg("Use emergency repair")
                        Utils.script_sleep(2)
                    Utils.touch_randomly(self.region["close_strategy_menu"])
                if target_info[2] == "mystery_node":
                    Logger.log_msg("Target reached.")
                    self.fleet_location = target_info[0:2]
                    return 0
                continue
            if Utils.find_with_cropped("combat/alert_morale_low"):
                if self.config.combat['ignore_morale']:
                    Utils.find_and_touch("menu/button_confirm")
                else:
                    Utils.touch_randomly(self.region['close_info_dialog'])
                    if self.config.combat['low_mood_rotation']:
                        self.exit = 6
                        self.fleet_switch_due_to_morale= True
                        Logger.log_warning("Low morale detected. Will switch to a different fleet.")
                        return 2
                    # bot rests by default
                    else:
                        self.exit = 3
                        return 2
            if (target_info[2] == 'mystery_node' or target_info[2] == 'empty') and fleet_arrival_detection_region.contains(self.get_fleet_location()):
                count_fleet_at_target_location += 1
                if count_fleet_at_target_location >= 3:
                    if target_info[2] == 'mystery_node':
                        Logger.log_warning('Fleet locates at the target mystery node but nothing is detected.')
                    else:
                        Logger.log_msg("Target empty tile reached")
                    return 0
                continue
            if Utils.find_with_cropped("combat/menu_loading", 0.8) or Utils.find_with_cropped("combat/combat_pause", 0.7):
                self.fleet_location = target_info[0:2]
                return 1
            elif event["combat/menu_formation"]:
                Utils.find_and_touch("combat/auto_combat_off")
                self.fleet_location = target_info[0:2]
                return 1
            else:
                if count != 0 and count % 3 == 0 and not arrow_found:
                    Utils.touch(location)
                if count > 41 and self.chapter_map == '2-1' and self.dedicated_map_strategy:
                    Logger.log_error("Too many loops in movement_handler in 2-1. Forcing retreating...")
                    self.targeting_2_1_D3 = False
                    self.exit = 5
                    return 2
                if (count > 41 and (self.chapter_map == '7-2' or self.chapter_map == '6-1' or self.chapter_map == '5-1') and self.config.combat['clearing_mode']):
                    # if the count is too small, bot would return 0(no fight needed) if the target is afar.
                    # if the count is too large, bot perform many meaningless touch and waste time if the 
                    #   target arrow is not found and the info for reaching the target is not captured.
                    #   This occurs mostly when the target is a mystery node containing ammo(may miss the ammo info) and 
                    #   when the this mystery node is very close to current fleet(unable to capture target arrow).
                    Logger.log_warning("Clicking on the destination for too many times. Assuming target reached.")
                    return 0
                if count > 41 and not (self.chapter_map == '7-2' or self.chapter_map == '6-1' or self.chapter_map == '5-1' or self.chapter_map == '2-1'):
                    Logger.log_msg("Blacklisting location and searching for another enemy.")
                    self.blacklist.append(location[0:2])
                    self.fleet_location = None
                    arrow_found = False
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
        count = 0

        while True:
            Utils.update_screen()
            if count > 100:
                # ensurance policy to avoid infinite loops
                Logger.log_error("Stuck in retreat_handler! Quitting the program...")
                exit()
            if Utils.find("combat/menu_formation"):
                Utils.touch_randomly(self.region["menu_nav_back"])
                Utils.script_sleep(1)
                continue
            if force_retreat and (not pressed_retreat_button) and Utils.find("combat/button_retreat"):
                Logger.log_msg("Retreating...")
                if Utils.touch_randomly_ensured(self.region['retreat_button'], "combat/button_retreat", ["menu/button_confirm"], response_time=0.5, stable_check_frame=2):
                    pressed_retreat_button = True
                Utils.script_sleep(1)
                continue
            if Utils.find_and_touch("menu/button_confirm"):
                # confirm either the retreat or an urgent commission alert
                Utils.script_sleep(1)
                continue
            if Utils.find_and_touch("combat/button_confirm"):
                # ensurance policy if the touch in the end of boss combat fails
                Logger.log_error("The touch in the end of a boss battle fails!")
                Utils.script_sleep(10)
                continue
            if Utils.find("menu/attack"):
                return
            count += 1

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
        self.enter_automatic_battle = False
        boss_swipe = 0
        Logger.log_msg("Started map clear.")
        Utils.script_sleep(2.5)

        screen_update_period = 3
        while self.automatic_sortie:
            Utils.script_sleep(screen_update_period, 0)
            Utils.update_screen()
            if Utils.find_with_cropped("combat/repeat"):
                #if self.enter_automatic_battle:
                #   self.combats_done += 1
                #    Logger.log_msg("One battle finished")
                #    self.enter_automatic_battle = False
                Logger.log_msg("One automatic sortie completed")
                if (self.stats.combat_done + 1) % self.config.combat['retire_cycle'] == 0:
                    Logger.log_msg("Return to main")
                    Utils.touch_randomly_ensured(self.region['battle_handler_safe_touch'], "combat/repeat", ["menu/attack"], response_time=0.5)
                    self.exit = 1
                    return True
                else:
                    self.stats.increment_combat_done()
                    Utils.touch_randomly_ensured(self.region['automation_repeat_button'], "", ["combat/automation_search_enemy", "combat/combat_pause"], response_time=1)
                    Logger.log_msg("Repeating automatic sortie")
            if Utils.find_with_cropped("menu/attack"):
                # wait to ensure stable screen
                Utils.wait_update_screen(3)
                if Utils.find_with_cropped("menu/attack"):
                    Logger.log_warning("Somehow still in attack menu. Assume defeated and retrying...")
                    self.exit = 5
                    return False
            if (not self.enter_automatic_battle) and Utils.find_with_cropped("combat/combat_pause"):
                self.enter_automatic_battle = True
                battle_screen_update_period = screen_update_period
                enter_battle_summary = False
                count = 0
                while True:
                    Utils.script_sleep(battle_screen_update_period, 0)
                    Utils.update_screen()
                    count += 1
                    if not enter_battle_summary and not Utils.find_with_cropped("combat/combat_pause"):
                        battle_screen_update_period = 0.1
                        enter_battle_summary = True
                    if enter_battle_summary and (Utils.find_with_cropped("combat/automation_search_enemy") or Utils.find_with_cropped("combat/repeat")):
                        self.combats_done += 1
                        Logger.log_msg("One battle finished")
                        self.enter_automatic_battle = False
                        if False and self.chapter_map == "6-1" and (self.combats_done == 2 or self.combats_done == 4):
                            if Utils.touch_randomly_ensured(self.region['automation_search_enemy_switch'], "combat/automation_search_enemy", ["combat/button_retreat"], response_time=0.5):
                                Logger.log_msg("Automation sortie halted")
                                self.reset_screen_by_anchor_point()
                                Logger.log_msg("Collect mystery nodes")
                                mystery_nodes_list = self.get_mystery_nodes()
                                if mystery_nodes_list:
                                    target_info = [mystery_nodes_list[0][0], mystery_nodes_list[0][1], 'mystery_node']
                                    Utils.touch(target_info[0:2])
                                    movement_result = self.movement_handler(target_info)
                                    if movement_result == -1:
                                        Logger.log_msg('Mystery node is blocked. Skip this mystery_node.')
                                else:
                                    Logger.log_msg('No mystery node is found')
                                Logger.log_msg('Resume automation sortie')
                                Utils.update_screen()
                                Utils.touch_randomly_ensured(self.region['automation_search_enemy_switch'], "combat/button_retreat", ["combat/automation_search_enemy"], response_time=0.05)
                            else:
                                Logger.log_warning("Fail to halt automation sortie")
                        break
                    if count >= 300:
                        Logger.log_warning("Too many loops in detecting a fight in automation sortie")
                        break

        while Utils.find_with_cropped("menu/button_confirm"):
            Logger.log_msg("Found commission info message.")
            self.stats.increment_commissions_occurance()
            Utils.touch_randomly(self.region["combat_com_confirm"])
            Utils.wait_update_screen()

        
        while self.config.combat['clearing_mode'] and not Utils.find("combat/fleet_lock", 0.99):
            Utils.touch_randomly(self.region["fleet_lock"])
            Logger.log_warning("Using fleet lock.")
            Utils.wait_update_screen()
        

        if self.config.combat['fleet_switch_at_beinning']:
            Utils.touch_randomly(self.region['button_switch_fleet'])
            Utils.script_sleep(2)
            # for ashen simulation
            if self.chapter_map == 'E-C1' and False:
                self.reset_screen_by_anchor_point()
            # for scherzo of iron and blood
            if self.chapter_map == 'E-C3' and False:
                self.reset_screen_by_anchor_point()
            # for cherry blossom
            if self.chapter_map == 'E-D3' and True:
                self.reset_screen_by_anchor_point()
            

        #swipe map to fit everything on screen
        swipes = {
            'E-B3': lambda: Utils.swipe(960, 540, 1060, 670, 300),
            'E-C3': lambda: Utils.swipe(1200, 540, 800, 540, 300),
            #'E-D3': lambda: Utils.swipe(960, 540, 1060, 670, 300),
            # needs to be updated
            '4-2': lambda: Utils.swipe(1000, 700, 1000, 400, 300), #to focus on enemies in the lower part of the map
            '5-1': lambda: Utils.swipe(1000, 400, 1000, 700, 300), #to fit the question mark of 5-1 on the screen
            #'6-1': lambda: Utils.swipe(1200, 550, 800, 450, 300), #to focus on enemies in the left part of the map(C5 mystery mark seems to be undetectable by bot)
            #'6-1': lambda: Utils.swipe(700, 500, 1300, 500, 300), #temporary solution to avoid bug related to blocking boss 
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

        # special initial move/switch for easier farming in some specific maps
        if self.chapter_map == "5-1":
            # Special farming for 5-1:
            # Setup: fleet 1 = boss fleet; another fleet = mob fleet; enable boss fleet = True; prioritize mystery node = True
            # 1. boss fleet move to obtain the mystery node at the beginning(this also ensures no boss blocking by boss fleet)
            # 2. switch to mob fleet, and let it clear 4 enemies(boss block by mob fleet can be handled by the default left disclosing)
            # 3. switch back to boss fleet, and clear the boss
            target_info = self.get_closest_target(self.blacklist, mystery_node=True)
            Utils.touch(target_info[0:2])
            self.movement_handler(target_info)
            Utils.touch_randomly(self.region['button_switch_fleet'])
            Utils.script_sleep(2)
            Utils.update_screen()
        
        # dedicated for scherzo of iron and blood event(farming points and torpedo fighter)
        if self.chapter_map == "E-C3" and False:
            Utils.touch(self.key_map_region['E-C3']['C1'].get_center())
            Utils.script_sleep(2)
            Utils.touch(self.key_map_region['E-C3']['D1'].get_center())
            Utils.script_sleep(1)
            Utils.update_screen()
            self.battle_handler()
            Utils.touch(self.key_map_region['E-C3']['F2'].get_center())
            Utils.script_sleep(2)
            Utils.update_screen()
            self.battle_handler()
            #Utils.touch_randomly(self.region['button_switch_fleet'])
            Utils.update_screen()
            #fleet_switched_for_E_C3 = False

        # dedicated for cherry blossom event(farming points)
        if self.chapter_map == "E-D3" and True:
            Utils.touch(self.key_map_region['E-D3']['C1'].get_center())
            Utils.script_sleep(6)
            Utils.update_screen()
            self.battle_handler()
            Utils.touch(self.key_map_region['E-D3']['D2'].get_center())
            Utils.script_sleep(3)
            Utils.update_screen()
            self.battle_handler()
            Utils.touch(self.key_map_region['E-D3']['F7'].get_center())
            Utils.script_sleep(8)
            Utils.update_screen()
            self.battle_handler()
            Utils.update_screen()
            self.exit = 0
            #fleet_switched_for_E_C3 = False

        # dedicated for ashen simulation(farming points and gun)
        if self.chapter_map == "E-C1" and False:
            for i in range(3):
                Utils.update_screen()
                # kill possible D6 enemy to clear path to C6
                if i == 0:
                    if self.enemy_exist_here(self.key_map_region['E-C1']['D6']):
                        coord = self.key_map_region['E-C1']['D6'].get_center()
                        Logger.log_msg("D6 enemy exists")
                    else:
                        Logger.log_msg("No D6 enemy")
                        continue
                if i == 1:
                    coord = self.key_map_region['E-C1']['C6'].get_center()
                    Logger.log_msg("Targetting C6 elite")
                if i == 2:
                    coord = self.key_map_region['E-C1']['F5'].get_center()
                    Logger.log_msg("Targetting F5 elite")
                target_info = [coord[0], coord[1], 'enemy']
                Utils.touch(coord)
                movement_result = self.movement_handler(target_info)
                if movement_result == 1:
                    self.battle_handler()


        fleet_switched = False
        # setting specific to 6-1
        if self.chapter_map == '6-1':
            self.reset_screen_by_anchor_point()
#By me:
# allow the bot to collect question node at the first turn
        #target_info = self.get_closest_target(self.blacklist)
        if not (self.config.exercise['enabled'] and self.config.combat['clearing_mode']):
            if self.chapter_map == '6-1':
                target_info = self.get_closest_target(self.blacklist, mystery_node=(not self.config.combat["ignore_mystery_nodes"]), focus_main_fleet=True)
            elif self.chapter_map == '1-3':
                target_info = self.get_closest_target(self.blacklist, mystery_node=False)
            else:
                target_info = self.get_closest_target(self.blacklist, mystery_node=(not self.config.combat["ignore_mystery_nodes"]))

        while True:
            Utils.update_screen()

            if Utils.find_with_cropped("combat/alert_unable_battle"):
                Utils.touch_randomly(self.region['close_info_dialog'])
                self.exit = 5
            #if self.config.combat['retreat_after'] != 0 and self.combats_done >= self.config.combat['retreat_after']:
            if self.config.combat['retreat_after'] != 0 and self.kills_count >= self.config.combat['retreat_after'] and (target_info != None and target_info[2] == 'enemy'):
                Logger.log_msg("Retreating after defeating {} enemies".format(self.config.combat['retreat_after']))
                self.exit = 2
            if self.exit != 0:
                self.retreat_handler()
                return True
            if (self.kills_count == 2 and self.chapter_map == "6-1" and not fleet_switched):
                # this makes farming easier by switching to a healthy fleet
                Logger.log_msg("Go to B3")
                coord = [475, 575] #B3 in 6-1
                Utils.touch(coord)
                movement_result = self.movement_handler([coord[0], coord[1], 'empty']) 
                if movement_result == -1:
                    Logger.log_msg('Current fleet is not blocking the boss spawn point')
                elif movement_result == 1:
                    Logger.log_warning('Somehow there is an enemy at B3')
                    if not self.battle_handler() and self.chapter_map == '6-1':
                        # reset screen if defeated
                        self.reset_screen_by_anchor_point()
                    Utils.save_screen('somehow-B3-enemy')
                Utils.script_sleep(1)
                Logger.log_msg("Fleet switching after 2 fights for easier 6-1 farming.")
                Utils.touch_randomly(self.region['button_switch_fleet'])
                if not self.reset_screen_by_anchor_point():
                    Logger.log_warning("Fail to reset the screen by anchor. Force retreat and try again.")
                    self.exit = 5
                    self.retreat_handler()
                    return True
                fleet_switched = True
                Utils.script_sleep(1)
                continue 
            if ((self.kills_count >= self.kills_before_boss[self.chapter_map] or (self.config.exercise['enabled'] and self.config.combat['clearing_mode'])) and Utils.find_in_scaling_range("enemy/fleet_boss", similarity=0.9)):
                Logger.log_msg("Boss fleet was found.")

                # get mystery node before attacking boss
                # make sure the boss is visible after screen reset
                if self.chapter_map == '6-1':
                    self.reset_screen_by_anchor_point()
                    mystery_nodes_list = self.get_mystery_nodes()
                    if mystery_nodes_list:
                        target_info = [mystery_nodes_list[0][0], mystery_nodes_list[0][1], 'mystery_node']
                        Utils.touch(target_info[0:2])
                        movement_result = self.movement_handler(target_info)
                        if movement_result == -1:
                            Logger.log_msg('Mystery node is blocked. Skip this collection and proceed to kill boss.')
                        if movement_result == 1:
                            Logger.log_msg('Somehow a fight is needed for collecting mystery node.')
                            if not self.battle_handler():
                                #retreat if lose
                                continue
                            Utils.save_screen('somehow-mystery-enemy')

                    else:
                        Logger.log_msg('No mystery node detected. Proceed to kill boss.')


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
                        Utils.wait_update_screen(0.1)
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
# By me:
# Solution when boss is hidden by player's fleet. This should work for map 4-2, 5-1 and 6-1(any map with bottom left or right tile of a possibly blocked boss empty).
# It's just moving one grid left, and two-times one grid right if boss still not found.
# The width of one grid is roughly 180 pixels.
# Note that this will fail if the boss is hidden by the other fleet.
            #elif self.kills_count >= self.kills_before_boss[self.chapter_map] and self.config.combat['kills_before_boss'] == 0 and self.config.combat['clearing_mode']:
            elif self.kills_count >= self.kills_before_boss[self.chapter_map] and self.config.combat['clearing_mode']:
                Logger.log_warning("Boss fleet is not found. Trying to uncover the boss.")
                #if boss_swipe == 3:
                #    Logger.log_warning("Boss might be hidden by another fleet. Switch to the other fleet and retry.")
                #    Utils.touch_randomly(self.region['button_switch_fleet'])
                #    Utils.wait_update_screen(2)
                self.fleet_location = None
                single_fleet_location = self.get_fleet_location()
                location_left_or_right_of_fleet = [0, 0]
                if boss_swipe <= 0:
                    # move to the left
                    Logger.log_msg("Move to the left")
                    location_left_or_right_of_fleet[0] = single_fleet_location[0] - 180
                else:
                    # move to the right 
                    location_left_or_right_of_fleet[0] = single_fleet_location[0] + 180
                    Logger.log_msg("Move to the right")
                location_left_or_right_of_fleet[1] = single_fleet_location[1]
                Utils.touch(location_left_or_right_of_fleet)
                # We must give some time for the fleet to move, otherwise the screen update right after continue will still fail to see boss.
                Utils.wait_update_screen(2)
                #if Utils.find_in_scaling_range("enemy/fleet_boss", similarity=0.9):
                #    Logger.log_msg("Boss uncovered")
                boss_swipe += 1
                if boss_swipe >= 3:
                    Logger.log_error("Boss cannot be uncovered. Force retreating...")
                    self.exit = 5
                continue
            if target_info == None:
                if self.chapter_map == '6-1':
                    target_info = self.get_closest_target(self.blacklist, mystery_node=(not self.config.combat["ignore_mystery_nodes"]), focus_main_fleet=True)
                else:
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
                Utils.script_sleep(1)
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
                    if not self.battle_handler() and self.chapter_map == '6-1' and False:
                        # reset screen if defeated
                        self.reset_screen_by_anchor_point()
                # This swipe for map 2-3 makes bot more likely to target key enemies blocking the boss
                if self.chapter_map == '2-3' and target_info_tmp[2] == 'mystery_node':
                    Logger.log_msg("Relocating screen of 2-3 after picking the mystery node.")
                    Utils.swipe(1000, 350, 1000, 700, 1500)

                target_info = None

                self.blacklist.clear()

                #Utils.script_sleep(3)
                continue

    def clear_map_special_2_1(self):
        """ Clears map.
        """
        self.fleet_location = None
        self.combats_done = 0
        self.kills_count = 0
        self.enemies_list.clear()
        self.mystery_nodes_list.clear()
        self.blacklist.clear()
        self.swipe_counter = 0
        kill_all = True
        boss_swipe = 0
        Logger.log_msg("Started special map clear for 2-1.")
        Utils.script_sleep(2.5)

        while Utils.find_with_cropped("menu/button_confirm"):
            Logger.log_msg("Found commission info message.")
            self.stats.increment_commissions_occurance()
            Utils.touch_randomly(self.region["combat_com_confirm"])
            Utils.wait_update_screen()

        
        while self.config.combat['clearing_mode'] and not Utils.find("combat/fleet_lock", 0.99):
            Utils.touch_randomly(self.region["fleet_lock"])
            Logger.log_warning("Using fleet lock.")
            Utils.wait_update_screen()
        

        if self.config.combat['fleet_switch_at_beinning']:
            Utils.touch_randomly(self.region['button_switch_fleet'])
            Utils.script_sleep(2)

        # disable subs' hunting range
        if self.config.combat["hide_subs_hunting_range"]:
            Utils.script_sleep(0.5)
            Utils.touch_randomly(self.region["open_strategy_menu"])
            Utils.script_sleep()
            Utils.touch_randomly(self.region["disable_subs_hunting_radius"])
            Utils.script_sleep()
            Utils.touch_randomly(self.region["close_strategy_menu"])



        # kill all case
        # starting with mob fleet in control
        if kill_all:
            # kill 2 mobs
            self.kill_specific_number_of_mob(2, mystery_node_as_target=False)
            if self.exit != 0: self.retreat_handler(); return True
            # reset screen due to boss appearance
            self.reset_screen_by_anchor_point()
            # kill 3 mobs
            self.kill_specific_number_of_mob(3, mystery_node_as_target=False)
            if self.exit != 0: self.retreat_handler(); return True
            # move to D3 to avoid possible blocking on the final enemy
            self.is_reachable(self.key_map_region['2-1']['D3'].get_center())
            # kill 1 mobs
            self.kill_specific_number_of_mob(1, mystery_node_as_target=True)
            if self.exit != 0: self.retreat_handler(); return True
            # switch to boss fleet, reset screen, and kill boss
            Utils.touch_randomly(self.region['button_switch_fleet'])
            self.reset_screen_by_anchor_point()
            self.kill_boss()
            if self.exit != 0: self.retreat_handler(); return True
            return True 




        # starting with boss fleet in control
        # is mystery node reachable?
        if self.is_reachable(self.key_map_region['2-1']['F2'].get_center()): # take mystery node
            Logger.log_debug("Route B")
            # is D3 reachable?
            if self.is_reachable(self.key_map_region['2-1']['D3'].get_center()): # boss fleet moves to D3
                Logger.log_debug("Route B2")
                # switch to mob fleet
                Utils.touch_randomly(self.region['button_switch_fleet'])
                self.reset_screen_by_anchor_point()
                # kill 2 mobs
                self.kill_specific_number_of_mob(2)
                if self.exit != 0: self.retreat_handler(); return True
                # boss appears, switch to boss fleet(screen reset is not needed as boss fleet is at D3)
                Utils.touch_randomly(self.region['button_switch_fleet'])
                #self.reset_screen_by_anchor_point()
                # kill boss
                self.kill_boss()
                if self.exit != 0: self.retreat_handler(); return True
                return True            
            else:
                Logger.log_debug("Route B1")
                # kill E3 enemy
                self.kill_the_specific_enemy(self.key_map_region['2-1']['E3'].get_center()); 
                if self.exit != 0: self.retreat_handler(); return True
                # switch to mob fleet
                Utils.touch_randomly(self.region['button_switch_fleet'])
                self.reset_screen_by_anchor_point()
                # kill C3 enemy
                self.kill_the_specific_enemy(self.key_map_region['2-1']['C3'].get_center())
                if self.exit != 0: self.retreat_handler(); return True
                # boss appears, kill it with mob fleet
                self.kill_boss()
                if self.exit != 0: self.retreat_handler(); return True
                return True
        else:
            Logger.log_debug("Route A")
            # is D3 reachable?
            if self.is_reachable(self.key_map_region['2-1']['D3'].get_center()): # boss fleet moves to D3
                Logger.log_debug("Route A2")
                # switch to mob fleet
                Utils.touch_randomly(self.region['button_switch_fleet'])
                self.reset_screen_by_anchor_point()
                # kill E3 enemy
                self.kill_the_specific_enemy(self.key_map_region['2-1']['E3'].get_center())
                if self.exit != 0: self.retreat_handler(); return True
                # is mystery node reachable?
                if self.is_reachable(self.key_map_region['2-1']['F2'].get_center()): # take mystery node
                    Logger.log_debug("Route A2b")
                    # kill 1 mob
                    self.kill_specific_number_of_mob(1)
                    if self.exit != 0: self.retreat_handler(); return True
                    # boss appears, switch to boss fleet(no need to reset screen as boss fleet is at D3)
                    Utils.touch_randomly(self.region['button_switch_fleet'])
                    #self.reset_screen_by_anchor_point()
                    # kill boss
                    self.kill_boss()
                    if self.exit != 0: self.retreat_handler(); return True
                    return True
                else:
                    Logger.log_debug("Route A2a")
                    # kill E2 enemy
                    self.kill_the_specific_enemy(self.key_map_region['2-1']['E2'].get_center())
                    if self.exit != 0: self.retreat_handler(); return True
                    # boss appears, reset screen
                    # this may not be necessary as the mystery node is still in the screen
                    self.reset_screen_by_anchor_point()
                    # take mystery node
                    self.is_reachable(self.key_map_region['2-1']['F2'].get_center())
                    # switch to boss fleet(no need to reset screen as boss fleet is at D3)
                    Utils.touch_randomly(self.region['button_switch_fleet'])
                    #self.reset_screen_by_anchor_point()
                    # kill boss
                    self.kill_boss()
                    if self.exit != 0: self.retreat_handler(); return True
                    return True
            else:
                Logger.log_debug("Route A1")
                # switch to mob fleet
                Utils.touch_randomly(self.region['button_switch_fleet'])
                self.reset_screen_by_anchor_point()
                # kill C3 enemy
                self.kill_the_specific_enemy(self.key_map_region['2-1']['C3'].get_center())
                if self.exit != 0: self.retreat_handler(); return True
                # is mystery node reachable?
                if self.is_reachable(self.key_map_region['2-1']['F2'].get_center()): # take mystery node
                    Logger.log_debug("Route A1b")
                    # kill C1 enemy
                    self.kill_the_specific_enemy(self.key_map_region['2-1']['C1'].get_center())
                    if self.exit != 0: self.retreat_handler(); return True
                    # boss appears, kill it with mob fleet
                    self.kill_boss()
                    if self.exit != 0: self.retreat_handler(); return True
                    return True               
                else:
                    Logger.log_debug("Route A1a")
                    # E3 enemy exist?
                    if self.enemy_exist_here(self.key_map_region['2-1']['E3']):
                        Logger.log_debug("Route A1a2")
                        # move to D3 to avoid possible blocking of C1 enemy
                        Utils.touch(self.key_map_region['2-1']['D3'].get_center(), sleep=1)
                        # C1 enemy exist?
                        if self.enemy_exist_here(self.key_map_region['2-1']['C1']):
                            Logger.log_debug("Route A1a2b")
                            # kill E3 enemy
                            self.kill_the_specific_enemy(self.key_map_region['2-1']['E3'].get_center())
                            if self.exit != 0: self.retreat_handler(); return True
                            # boss appears, reset screen
                            self.reset_screen_by_anchor_point()
                            # kill E2 enemy
                            self.kill_the_specific_enemy(self.key_map_region['2-1']['E2'].get_center())
                            if self.exit != 0: self.retreat_handler(); return True
                            # take mystery node
                            self.is_reachable(self.key_map_region['2-1']['F2'].get_center())
                            # kill boss
                            self.kill_boss()
                            if self.exit != 0: self.retreat_handler(); return True
                            return True
                        else:
                            Logger.log_debug("Route A1a2a")
                            # kill E1 enemy
                            self.kill_the_specific_enemy(self.key_map_region['2-1']['E1'].get_center())
                            if self.exit != 0: self.retreat_handler(); return True
                            # boss appears, reset screen
                            self.reset_screen_by_anchor_point()
                            # take mystery node
                            self.is_reachable(self.key_map_region['2-1']['F2'].get_center())
                            # switch to boss fleet
                            Utils.touch_randomly(self.region['button_switch_fleet'])
                            self.reset_screen_by_anchor_point()
                            # kill boss
                            self.kill_boss()
                            if self.exit != 0: self.retreat_handler(); return True
                            return True
                    else:
                        Logger.log_debug("Route A1a1")
                        # kill E2 enemy
                        self.kill_the_specific_enemy(self.key_map_region['2-1']['E2'].get_center())
                        if self.exit != 0: self.retreat_handler(); return True
                        # boss appears, reset screen
                        self.reset_screen_by_anchor_point()
                        # take mystery node
                        self.is_reachable(self.key_map_region['2-1']['F2'].get_center())
                        # switch to boss fleet
                        Utils.touch_randomly(self.region['button_switch_fleet'])
                        self.reset_screen_by_anchor_point()
                        # kill boss
                        self.kill_boss()
                        if self.exit != 0: self.retreat_handler(); return True
                        return True

    def kill_the_specific_enemy(self, coord):
        target_info = [coord[0], coord[1], 'enemy']
        count = 0
        while True:
            count += 1
            if count >= 10:
                Logger.log_error("Too many loops in kill_the_specific_enemy. Force retreating...")
                self.exit = 5
                return 
            Utils.touch(target_info[0:2])
            Utils.update_screen()
            movement_result = self.movement_handler(target_info)
            if movement_result == 1:
                self.battle_handler()
                target_info = None
                self.blacklist.clear()
                return
            if movement_result == 2:
                return

    def kill_specific_number_of_mob(self, number, mystery_node_as_target=False):
        present_kill_count = self.kills_count
        target_info = None
        count = 0
        while True:
            count += 1
            if count >= 100:
                Logger.log_error("Too many loops in kill_specific_number_of_mob. Terminating...")
                exit()
            if self.exit != 0:
                return
            if self.kills_count >= present_kill_count + number:
                return
            Utils.update_screen()
            if target_info == None:
                target_info = self.get_closest_target(self.blacklist, mystery_node=mystery_node_as_target)
                if target_info == None:
                    Logger.log_warning("No enemy detected(reqest kill: {}; actual kill: {})".format(number, self.kills_count - present_kill_count))
                    return
                continue
            if target_info:
                Utils.touch(target_info[0:2])
                Utils.update_screen()
            else:
                continue
            if Utils.find_with_cropped("combat/alert_unable_reach"):
                Logger.log_warning("Unable to reach the target.")
                self.blacklist.append(target_info[0:2])
                target_info = None
                continue
            else:
                movement_result = self.movement_handler(target_info)
                if movement_result == 1:
                    self.battle_handler()
                target_info = None
                self.blacklist.clear()
                continue

    def kill_boss(self):
        Utils.wait_update_screen(0.5)
        boss_region = Utils.find_in_scaling_range("enemy/fleet_boss", similarity=0.9)
        if boss_region == None:
            Logger.log_warning("Cannot find boss. Retrying...")
            Utils.script_sleep(2)
            Utils.update_screen()
            boss_region = Utils.find_in_scaling_range("enemy/fleet_boss", similarity=0.9)
            if not boss_region:
                Logger.log_msg("Boss is found successfully")
            else:
                Logger.log_error("Cannot find boss! Force retreating...")
                self.exit = 5
                return
        boss_info = [boss_region.x + 50, boss_region.y + 25, "boss"]
        #self.kill_the_specific_enemy([boss_])
        self.clear_boss(boss_info)

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
        fleet_switched = False
        A3_enemy_exist_at_beginning = False

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
        Logger.log_msg("Started special map clear for 7-2.")
        Utils.script_sleep(2.5)

        while Utils.find_with_cropped("menu/button_confirm"):
            Logger.log_msg("Found commission info message.")
            self.stats.increment_commissions_occurance()
            Utils.touch_randomly(self.region["combat_com_confirm"])
            Utils.wait_update_screen()

        while self.config.combat['clearing_mode'] and not Utils.find("combat/fleet_lock", 0.99):
            Utils.touch_randomly(self.region["fleet_lock"])
            Logger.log_warning("Using fleet lock.")
            Utils.wait_update_screen()

        if self.config.combat['fleet_switch_at_beinning']:
            Utils.touch_randomly(self.region['button_switch_fleet'])
            Utils.script_sleep(2)
            if not self.reset_screen_by_anchor_point():
                Logger.log_warning("Fail to reset the screen by anchor. Force retreat and try again.")
                self.exit = 5
                self.retreat_handler()
                return True
            Utils.script_sleep(1)     

        # move to the boss position to avoid blocking A3 enemy
        # FIXME: This might fail if the initial spawns happen to block our fleet from moving to boss position
        Utils.touch(position_boss)
        Utils.script_sleep(2.5)

        target_info = None

        while True:
            Utils.update_screen()

            if Utils.find_with_cropped("combat/alert_unable_battle"):
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
                    target_info = None
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
            if (self.kills_count == 999 and self.config.combat['retreat_after'] == 3 and not fleet_switched) or (self.kills_count >= 5 and self.config.combat['retreat_after'] == 0 and not fleet_switched and question_mark_all_obtained):
                # switch fleet after killing 2 enemies for 3-fight farming
                # this makes farming easier by switching to a healthy fleet
                Logger.log_msg("Fleet switching after 2/4 fights for easier 3-fight/full 7-2 farming.")
                Utils.touch_randomly(self.region['button_switch_fleet'])
                Utils.script_sleep(2)
                if not self.reset_screen_by_anchor_point():
                    Logger.log_warning("Fail to reset the screen by anchor. Force retreat and try again.")
                    self.exit = 5
                    self.retreat_handler()
                    return True
                fleet_switched = True
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
                    Utils.wait_update_screen(3)
                    if not self.reset_screen_by_anchor_point():
                        Logger.log_warning("Fail to reset the screen by anchor. Force retreat and try again.")
                        self.exit = 5
                        self.retreat_handler()
                        return True
                    
                    boss_region = Utils.find_in_scaling_range("enemy/fleet_boss", similarity=0.9)

                    while not boss_region:
                        if s > 3: s = 0
                        swipes.get(s)()
                        Utils.wait_update_screen(0.1)
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
                Utils.update_screen() # just to ensure screenis updated when detecting enemies
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
                    if self.battle_handler():
                        if targeting_block_right:
                            block_right_clear = True 
                        if targeting_block_left:
                            block_left_clear = True 
                        if targeting_block_A3:
                            block_A3_clear = True  
                    else:
                        # reset screen when lost
                        self.reset_screen_by_anchor_point()
                    Utils.script_sleep(3)
                """    
                if targeting_block_right:
                    block_right_clear = True 
                if targeting_block_left:
                    block_left_clear = True 
                if targeting_block_A3:
                    block_A3_clear = True  
                """

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
                    3: lambda: Utils.swipe(960, 240, 960, 940, 500), # swipe down
                    2: lambda: Utils.swipe(1560, 540, 260, 540, 500), # swipe left
                    1: lambda: Utils.swipe(960, 940, 960, 240, 500), # swipe up
                    0: lambda: Utils.swipe(260, 540, 1560, 540, 500) # swipe right
                }
        if self.chapter_map == "7-2":
            anchor_position = [1564, 677]
            anchor_tolerance = [30, 30]
        elif self.chapter_map == "6-1":
            anchor_position = [313, 738]
            anchor_tolerance = [10, 10]
        elif self.chapter_map == "2-1":
            anchor_position = [500, 557]
            anchor_tolerance = [30, 30]
        elif self.chapter_map == "E-C1":
            anchor_position = [1410, 252]
            anchor_tolerance = [30, 30]
        elif self.chapter_map == "E-C3":
            anchor_position = [1748, 406]
            anchor_tolerance = [30, 30]
        elif self.chapter_map == "E-D3":
            anchor_position = [818, 748]
            anchor_tolerance = [30, 30]
        else:
            Logger.log_error('No anchor point is set for map {}.'.format(self.chapter_map))
            return False

        swipe_reset = 0
        Utils.update_screen()

        # this special treatment for 7-2 is to improve efficiency of screen reset
        if self.chapter_map == "7-2":
            # sometimes swipe will fail due to ADB not responding, so we try 3 times
            if Utils.find_with_cropped("map_anchors/map_7-2_top_right", similarity=0.95):
                    # fleet at top right
                    #Utils.swipe(600, 800, 1456, 494, 300)
                    #Utils.swipe(600, 800, 1449, 496, 300)
                    #Utils.swipe(600, 800, 1415, 509, 300)
                Utils.swipe(600, 800, 1425, 500, 600)
            else:
                    # fleet at bottom left
                    #Utils.swipe(1400, 400, 756, 700, 300)
                    #Utils.swipe(1400, 400, 767, 693, 300)
                    #Utils.swipe(1400, 400, 761, 697, 300)
                    #Utils.swipe(1400, 400, 769, 692, 300)
                Utils.swipe(1400, 400, 765, 695, 600)
            Utils.wait_update_screen()
            anchor = Utils.find("map_anchors/map_7-2", similarity=0.95)
            if anchor:
                if abs(anchor.x - anchor_position[0]) <= anchor_tolerance[0] and abs(anchor.y - anchor_position[1]) <= anchor_tolerance[1]:
                    Logger.log_msg("Screen successfully reset....")
                    screen_is_reset = True
                    return True           
        # if this special treatment fails, the general approach below still applies.

        # this is a general approach for resetting screen        
        anchor = Utils.find_in_scaling_range("map_anchors/map_{}".format(self.chapter_map), similarity=0.95)
        while not screen_is_reset:
            s = 0
            while not anchor:
                swipes.get(s % 4)()
                Utils.wait_update_screen(0.1)
                anchor = Utils.find_in_scaling_range("map_anchors/map_{}".format(self.chapter_map), similarity=0.95)
                s += 1
                if s > 15:
                    Logger.log_error("Swipe too many times for searching anchor point.")
                    return False
            Utils.swipe(1920/2, 1080/2, 1920/2 + anchor_position[0] - anchor.x, 1080/2 + anchor_position[1] - anchor.y, 800)
            swipe_reset += 1
            if swipe_reset > 15:
                Logger.log_error("Swipe too many times for resetting screen.")
                return False
            Utils.wait_update_screen(0.5)
            # check if resetiing screen is really successful
            anchor = Utils.find_in_scaling_range("map_anchors/map_{}".format(self.chapter_map), similarity=0.95)
            if not anchor:
                Logger.log_warning("Anchor found but cannot find anchor after swipes. Retrying...")
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

        if not block_A3_clear and not block_target_obtained:
            for index_target in range(0, len(targets)):
                if self.is_within_zone(targets[index_target], region_block_A3):
                    index_target_chosen = index_target
                    Logger.log_info('Found A3 enemy at: {}'.format(targets[index_target]))
                    targeting_block_A3 = True
                    block_target_obtained = True
                    break
        if not block_right_clear and not block_target_obtained:
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

        swipes = {
            0: lambda: Utils.swipe(960, 240, 960, 940, 300),
            1: lambda: Utils.swipe(1560, 540, 260, 540, 300),
            2: lambda: Utils.swipe(960, 940, 960, 240, 300),
            3: lambda: Utils.swipe(260, 540, 1560, 540, 300)
        }

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
                #swipes = {
                #    0: lambda: Utils.swipe(960, 240, 960, 940, 300),
                #    1: lambda: Utils.swipe(1560, 540, 260, 540, 300),
                #    2: lambda: Utils.swipe(960, 940, 960, 240, 300),
                #    3: lambda: Utils.swipe(260, 540, 1560, 540, 300)
                #}

# By me: This should be a bug. It switch fleet no matter what.
#                Utils.touch_randomly(self.region['button_switch_fleet'])
#                Utils.wait_update_screen(2)
                boss_region = Utils.find_in_scaling_range("enemy/fleet_boss", similarity=0.9)
                s = 0
                while not boss_region:
                    if s > 15: 
                        Logger.log_error("Searching boss for too many times. Start retreating... ")
                        self.exit = 5
                        return
                    swipes.get(s % 4)()
                    Utils.wait_update_screen(0.1)
                    boss_region = Utils.find_in_scaling_range("enemy/fleet_boss", similarity=0.9)
                    s += 1
                boss_info = [boss_region.x + 50, boss_region.y + 25, "boss"]
                continue
            else:
                if self.movement_handler(boss_info) == 2:
                    return
                if self.battle_handler(boss=True):
                    self.exit = 1
                    Logger.log_msg("Boss successfully defeated.")
                else:
                    pass
                    # these 2 lines should be redundant
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
                        swipes.get(s % 4)()
                        Utils.wait_update_screen(0.1)
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

        count = 0
        while not self.enemies_list:
            count += 1
            if count >= 100:
                Logger.log_error("Too many loops in searching enemies. Terminating...")
                exit()
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


        #if len(self.mystery_nodes_list) == 0 and not Utils.find('combat/question_mark', 0.9):
        if len(self.mystery_nodes_list) == 0 and not Utils.find('combat/question_mark', 0.75):
            # if list is empty and a question mark is NOT found
            return self.mystery_nodes_list
        else:
            # list has elements or list is empty but a question mark has been found
            filter_coordinates = True if len(self.mystery_nodes_list) == 0 else False
            sim = 0.95

            while not self.mystery_nodes_list and sim > 0.93:
                Utils.update_screen()

                if self.chapter_map == '6-1':
                    sim = 0.75
                    l1 = list(map(lambda x:[x[0], x[1] + 140], Utils.find_all_with_resize('combat/question_mark', sim)))
                else:
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
        # this line forces to search fleet location when called
        self.fleet_location = None
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

            #print('fleet location: {}'.format(self.fleet_location))

        return self.fleet_location

    def get_closest_target(self, blacklist=[], location=[], mystery_node=False, boss=False, focus_main_fleet=False):
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
                if focus_main_fleet:
                    focused_enemy = self.get_focused_enemies(enemies)
                    if not focused_enemy:
                        targets = enemies + mystery_nodes
                    else:
                        targets = focused_enemy + mystery_nodes
                else:
                    targets = enemies + mystery_nodes
        else:
            # target only enemy mobs
            enemies = self.get_enemies(blacklist, boss)
            if focus_main_fleet:
                focused_enemy = self.get_focused_enemies(enemies)
                if not focused_enemy:
                    targets = enemies
                else:
                    targets = focused_enemy
            else:
                targets = enemies

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

    def get_focused_enemies(self, enemies):
        focused_enemy = []
        for i in range(len(enemies)):
            region_to_search = Utils.get_region_for_enemy_fleet_distinction(enemies[i])
            #if Utils.find_with_cropped('enemy/main_fleet', similarity=0.8, dynamical_region=region_to_search, print_info=True):
            if Utils.find_in_scaling_range('enemy/main_fleet', dynamical_region=region_to_search, similarity=0.8, lowerEnd=0.8, upperEnd=1.2):
                Logger.log_info('Enemy at [{}, {}] is a main fleet'.format(enemies[i][0], enemies[i][1]))
                focused_enemy.append(enemies[i])
        return focused_enemy

    def is_reachable(self, coord):
        # dedicated for 2-1
        # set up region to search the green arrow at destination
        # assume target_info gives the center of the target
        # this method would still mis-judge if the target is 2 tiles above the current fleet(the arrow of current fleet could be mis-judged as target arrow)
        arrow_found = False
        target_arrow_search_region = Utils.get_region_for_target_arrow_search(coord) 
        if self.key_map_region['2-1']['D3'].contains(coord):
            self.targeting_2_1_D3 = True
        Logger.log_msg('Is {} reachable?'.format(coord))
        Utils.touch(coord, sleep=0.45)
        # check 10 frames
        for i in range(10):
            Utils.update_screen()
            if Utils.find_with_cropped('combat/alert_unable_reach', similarity=0.9):
                Logger.log_msg('Unable to reach the target.')
                # wait for the 'unable to reach' dialog to disappear to avoid mis-determination for other algorithm after this call
                Utils.script_sleep(3) 
                self.targeting_2_1_D3 = False
                return False
            if not arrow_found and Utils.find_with_cropped("combat/fleet_arrow", dynamical_region = target_arrow_search_region):
                Logger.log_msg('Target arrow found.')
                arrow_found = True
                break
        self.movement_handler([coord[0], coord[1], 'mystery_node'], try_touch= not arrow_found)
        return True

    def enemy_exist_here(self, region, print_info=False):
        # dedicated for 2-1
        self.enemies_list.clear()
        enemies = self.get_enemies([], False)
        if print_info == True: 
            Logger.log_msg('Region for detecting an enemy: {}, {}, {}, {}.'.format(region.x, region.y, region.w, region.h))
        for index in range(0, len(enemies)):
            if print_info == True: 
                Logger.log_msg('Enemy {} locates at {}, {}:'.format(index, enemies[index][0], enemies[index][1]))
            if region.contains([enemies[index][0], enemies[index][1]]):
                return True
        return False

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
            if (Utils.find_with_cropped(event))
            else False)
