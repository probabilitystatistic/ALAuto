import re
from util.logger import Logger
from util.config import Config
from util.utils import Utils, Region
from util.ocr import OCR


class ResearchModule(object):
    def __init__(self, config, stats):
        """Initializes the Research module.

        Args:
            config (Config): ALAuto Config instance
        """
        self.enabled = True
        self.config = config
        self.stats = stats
        self.neglect_series1 = True
        self.neglect_series2 = False
        self.prioritize_30min = True
        self.save_research_result_to_file = True
        self.no_matched_project = False
        self.use_OCR = True
        self.region = {
            'lab_tab': Region(1004, 1013, 162, 39),
            'exit_button': Region(51, 52, 71, 60),
            'research_academy': Region(825, 415, 260, 265),
            'project_click': Region(865, 155, 180, 100),
            'project_code': Region(361, 449, 577, 83),
            'right_arrow': Region(1855, 525, 30, 30),
            'commence_tab': Region(650, 855, 215, 35),
            'main_menu_button': Region(1821, 28, 44, 42),
            'confirm_tab': Region(1095, 760, 190, 50),
            'refresh_button': Region(1653, 975, 180, 60)
        }

    def research_logic_wrapper(self):
        if self.no_matched_project:
            Logger.log_warning("Neglect lab alert as no matched research project detected previously")
            return True
        else:
            Logger.log_msg("Found lab alert.")
        Utils.touch_randomly(self.region["lab_tab"])

        while True:
            Utils.wait_update_screen(1)

            if self.config.research['enabled'] and Utils.find("research/research_academy_alert"):
                Logger.log_msg("Found research academy alert.")
                Utils.touch_randomly(self.region['research_academy'])
                Utils.script_sleep(1)
                Logger.log_msg("Searching for completed research.")

                if not self.collecting_research():
                    Logger.log_msg("Did not found any completed research.")

                started = False
                Logger.log_msg("Searching for project that matches config.")
                if self.use_OCR:
                    project = self.read_project_by_ocr()
                    priority = self.sort_project(project_read=project)
                    current_location = 0
                    count = 1
                    while True:
                        target_project_index = priority.index(min(priority))
                        Logger.log_msg('Current project location: {}'.format(current_location))
                        Logger.log_msg('Project {} is chosen'.format(target_project_index))
                        if target_project_index >= current_location:
                            for i in range(current_location, target_project_index):
                                Utils.touch_randomly(self.region['right_arrow'])
                                Utils.script_sleep(0.5)
                        else:
                            for i in range(current_location, target_project_index + 5):
                                Utils.touch_randomly(self.region['right_arrow'])
                                Utils.script_sleep(0.5)
                        Utils.script_sleep(2)
                        if self.start_project() == True:
                                Logger.log_success("Project started.")
                                started = True
                                break
                        else:
                            Logger.log_warning("Unable to start project. Finding the one of next priority.")
                            priority[target_project_index] = 9999
                            current_location = target_project_index
                            count += 1
                            if count == 5:
                                Logger.log_warning("Tried all projects but still failed to start one.")
                                break
                if not self.use_OCR:
                    for research_loop in range(0,5):
                        if not self.research_cycle():
                            Utils.touch_randomly(self.region['right_arrow'])
                        else:
                            if self.start_project() == True:
                                Logger.log_success("Project started.")
                                started = True
                                break
                            else:
                                Logger.log_warning("Unable to start project. Finding a new one.")
                                Utils.touch_randomly(self.region['right_arrow'])

                if started == False:
                    if self.use_OCR:
                        Logger.log_error("Failed to start a project. Will try it agian latter.")
                    else:
                        Logger.log_error("Unable to find project that matches current configuration.")
                        self.no_matched_project = True
                Logger.log_msg("Going back to main menu.")       
            else:
                Logger.log_msg("Shipyard or Fleet Tech alert detected, ignoring it.")
            Utils.menu_navigate()
            #Utils.touch_randomly(self.region['main_menu_button'])
            #Utils.wait_update_screen(1)
            return True

    def read_project_by_ocr(self):
        use_tesseract = True
        failed = False
        project = []
        for research_loop in range(0,5):
            Utils.wait_update_screen(2)
            season = 0
            if Utils.find_with_cropped("research/series1"):
                season = 1
            elif Utils.find_with_cropped("research/series2"):
                season = 2
            if use_tesseract:
                try:
                    project_code = OCR.screen_to_string(self.region['project_code'], language="english", mode="research", save_process_to_file=False)
                except:
                    Logger.log_warning('OCR by tesseract failed. Project code is assigned as "fail"')
                    project_code = "fail"     
                    Utils.save_screen("OCR-tesseract-fail", crop_region=self.region['project_code'])
                    failed = True
            else:
                try:
                    project_code = OCR.screen_to_string_by_OCRspace(self.region['project_code'], mode="eng+number")     
                except:
                    Logger.log_warning('Online OCR failed. Project code is assigned as "fail"')
                    project_code = "fail"     
                    Utils.save_screen("OCR-OCRspace-fail")
                    failed = True
            if not failed:
                print("Raw OCR reading:", project_code)
                project_code = project_code.replace("\n", "") 
                project_code = project_code.replace("\t", "") 
                project_code = project_code.replace(" ", "") 
                project_code = project_code.replace("-", "") 
                project_code = project_code[0:6]
                if not (project_code[0] in ['B', 'C', 'D', 'E', 'G', 'H', 'Q', 'T']):
                    Logger.log_warning('OCR cannot identify first English letter')
                    Utils.save_screen("OCR-fail-letter", crop_region=self.region['project_code'])
                # special treatment for distinquishing 30min and 2h Q series
                if project_code[0:2] == 'Q0' and 'M' in project_code[-2:]:
                    project_code = 'negl'
                project_code = project_code[0:4]        

            Logger.log_msg('Project {} is: season {}; code {}'.format(research_loop, season, project_code))
            project.append('{}{}'.format(season, project_code))
            Utils.touch_randomly(self.region['right_arrow'])
        return project

    def sort_project(self, project_read, criterion='URII-free'):
        Logger.log_msg('Project priority strategy: {}'.format(criterion))
        if criterion == 'URII':
            # note that specific project should have higher priority than non-specific project of the same kind
            #   eg: 2D757 should be placed before 2D7XX in the priority_list
            priority_list = ['2D0XX', # 30min directional
                             '2H0XX', # 30min cube 
                             '2Q0XX', '1Q0XX', # 30min equip; special treatment in project reading stage is carried out
                             #'2H387', #'2H339', '2H207', # cube-consuming
                             '2D757', '2D779', # 2.5h directional for UR
                             '2D457', '2D479', # 8h directional for UR
                             '2D357', '2D379', # 5h directional for UR
                             '2Q3XX', '1Q3XX', # 1h equip for refresh
                             '2Q2XX', '1Q2XX', # 2h equip for refresh        
                             '2E031', '2E315', '1E031', '1E315', # equip scrape for refresh                   
                             '2G412', # 1.5h money
                             '2G531', # 4h money
                             '2D3XX', # 5h directional
                             '2G236', # 2.5h money
                             '2C038'  # 12h free
                             '2D7XX', # 2.5h directional
                             '2D4XX', # 8h directional
                             ]
        elif criterion == 'URII-free':
            priority_list = ['2D0XX', # 30min directional
                             '2H0XX', # 30min cube 
                             '2Q0XX', '1Q0XX', # 30min equip; special treatment in project reading stage is carried out
                             #'2H387', #'2H339', '2H207', # cube-consuming
                             '2D757', '2D779', # 2.5h directional for UR
                             '2D457', '2D479', # 8h directional for UR
                             '2D357', '2D379', # 5h directional for UR
                             '2C038', '1C038', # 12h free
                             '2C185', '1C185', # 8h free
                             '2C153', '1C153', # 6h free
                             '2Q3XX', '1Q3XX', # 1h equip for refresh
                             '2Q2XX', '1Q2XX', # 2h equip for refresh        
                             '2E031', '2E315', '1E031', '1E315' # equip scrape for refresh   
                             '2G412', # 1.5h money
                             '2D7XX', # 2.5h directional
                             '2G236', # 2.5h money 
                             '2D4XX', # 8h directional                
                             '2G531', # 4h money
                             '2D3XX', # 5h directional  
                             ]
        elif criterion == 'free':
            priority_list = ['2D0XX', # 30min directional
                             '2H0XX', # 30min cube 
                             '2Q0XX', '1Q0XX', # 30min equip; special treatment in project reading stage is carried out
                             '2C038', '1C038', # 12h free
                             '2C185', '1C185', # 8h free
                             '2C153', '1C153', # 6h free
                             '2Q3XX', '1Q3XX', # 1h equip for refresh
                             '2Q2XX', '1Q2XX', # 2h equip for refresh        
                             '2E031', '2E315', '1E031', '1E315' # equip scrape for refresh
                             '2D757', '2D779', # 2.5h directional for UR
                             '2D457', '2D479', # 8h directional for UR
                             '2D357', '2D379', # 5h directional for UR
                             '2D7XX', # 2.5h directional
                             '2D4XX', # 8h directional
                             '2G412', # 1.5h money
                             '2G531', # 4h money
                             '2D3XX', # 5h directional
                             '2G236', # 2.5h money
                             ]
        elif criterion == 'exact-free':
            priority_list = ['2C038', '1C038', # 12h free
                             '2C185', '1C185', # 8h free
                             '2C153', '1C153', # 6h free
                             '2Q3XX', '1Q3XX', # 1h equip for refresh
                             '2Q2XX', '1Q2XX', # 2h equip for refresh        
                             '2E031', '2E315', '1E031', '1E315' # equip scrape for refresh
                             '2D757', '2D779', # 2.5h directional for UR
                             '2D457', '2D479', # 8h directional for UR
                             '2D357', '2D379', # 5h directional for UR
                             '2D7XX', # 2.5h directional
                             '2D4XX', # 8h directional
                             '2G412', # 1.5h money
                             '2G531', # 4h money
                             '2D3XX', # 5h directional
                             '2G236', # 2.5h money                   
                             ]
        else:
            Logger.log_error('Invalid research strategy. Quitting...')
            exit()

        priority = [999, 999, 999, 999, 999]

        for i in range(5):
            for j in range(len(priority_list)):
                #print(priority_list[j][3:5])
                #print('^'+priority_list[j][0:5], project_read[i], bool(re.match('^'+priority_list[j][0:5], project_read[i])), bool(re.match('^'+priority_list[j][0:3], project_read[i])))
                #print('^'+priority_list[j][0:3], project_read[i], bool(re.match('^'+priority_list[j][0:3], project_read[i])))
                if priority_list[j][3:5] != 'XX':
                    if bool(re.match('^'+priority_list[j][0:5], project_read[i])):
                        priority[i] = j
                        Logger.log_debug('Project {} sorted by item {} with priority {}'.format(project_read[i], priority_list[j], j))
                        break
                else:
                    if bool(re.match('^'+priority_list[j][0:3], project_read[i])):
                        priority[i] = j
                        Logger.log_debug('Project {} sorted by item {} with priority {}'.format(project_read[i], priority_list[j], j))
                        break

        Logger.log_msg('Project read    : {}'.format(project_read))
        Logger.log_msg('Project priority: {}'.format(priority))
        return priority

    def research_cycle(self):
            Utils.wait_update_screen(1)
            if self.neglect_series1 and Utils.find_with_cropped("research/series1"):
                Logger.log_msg("Neglecting series I.")
                return False
            if self.neglect_series2 and Utils.find_with_cropped("research/series2"):
                Logger.log_msg("Neglecting series II.")
                return False
            if not self.config.research['8Hours'] and Utils.find("research/8h", 0.99):
                Logger.log_msg("Neglecting 8-hour research.")
                return False
            if not self.config.research['6Hours'] and Utils.find("research/6h", 0.99):
                Logger.log_msg("Neglecting 6-hour research.")
                return False
            if not self.config.research['5Hours'] and Utils.find("research/5h", 0.99):
                Logger.log_msg("Neglecting 5-hour research.")
                return False
            if not self.config.research['4Hours'] and Utils.find("research/4h", 0.99):
                Logger.log_msg("Neglecting 4-hour research.")
                return False
            if not self.config.research['2Hours30Minutes'] and Utils.find("research/2_30h", 0.99):
                Logger.log_msg("Neglecting 2.5-hour research.")
                return False
            if not self.config.research['2Hours'] and Utils.find("research/2h", 0.99):
                Logger.log_msg("Neglecting 2-hour research.")
                return False
            if not self.config.research['1Hour30Minutes'] and Utils.find("research/1_30h", 0.99):
                Logger.log_msg("Neglecting 1.5-hour research.")
                return False
            if not self.config.research['1Hour'] and Utils.find("research/1h", 0.99):
                Logger.log_msg("Neglecting 1-hour research.")
                return False
            if not self.config.research['30Minutes'] and Utils.find("research/30m", 0.99):
                Logger.log_msg("Neglecting 0.5-hour research.")
                return False
            if self.config.research['30Minutes'] and self.prioritize_30min and Utils.find("research/30m", 0.99):
                Logger.log_warning("Prioritizing 0.5-hour research.")
                return True
            if self.config.research['WithoutRequirements'] and not Utils.find("research/nothing", 0.99):
                Logger.log_msg("Not research without requirement.")
                return False
            if not self.config.research['AllowConsumingCoins'] and Utils.find("research/coins", 0.95):
                Logger.log_msg("Neglecting research requiring coins.")
                return False
# By me: sometimes bot consume cubes so I lower the similarity down
#            if not self.config.research['AllowConsumingCubes'] and Utils.find("research/cubes", 0.99):
            if not self.config.research['AllowConsumingCubes'] and Utils.find("research/cubes", 0.95):
                Logger.log_msg("Neglecting research requiring cubes.")
                return False
            if self.config.research['AwardMustContainPRBlueprint'] and not Utils.find("research/PRBlueprint", 0.9):
                Logger.log_msg("Neglecting research giving no blue prints.")
                return False
            if not self.config.research['AllowFreeProjects'] and Utils.find("research/free", 0.99):
                Logger.log_msg("Neglecting free research.")
                return False
            if not self.config.research['12Hours'] and Utils.find("research/12h", 0.99):
                Logger.log_msg("Neglecting 12-hour research.")
                return False
            else:
                 return True

    def start_project(self):
        if self.save_research_result_to_file:
            Utils.save_screen("research", need_to_update_screen=True)
        Utils.touch_randomly(self.region['commence_tab'])
        Utils.wait_update_screen(0.5)
        #solution for projects that don't require confirmation.
        if Utils.find("research/terminate", 0.99):
            return True

        if Utils.find("research/confirm", 0.95):
                Utils.touch_randomly(self.region['confirm_tab'])
                Utils.wait_update_screen(0.5)
                if Utils.find("research/terminate", 0.99):
                    return True

                else:
                    return False

    def collecting_research(self):
        Utils.touch_randomly(self.region['project_click'])
        Utils.wait_update_screen(0.5)
        if Utils.find("research/item_found"):
            Logger.log_msg("Found completed research project.")
            if self.save_research_result_to_file:
                Utils.script_sleep(2)
                Utils.save_screen("research", need_to_update_screen=True)
            Utils.touch_randomly(self.region['project_click'])
            Utils.script_sleep(1)
            Utils.touch_randomly(self.region['project_click'])
            return True
        else:
            #solution for azur lane bug
            for searching in range(0,5):
                Utils.touch_randomly(self.region['right_arrow'])
                Utils.wait_update_screen(0.5)
                if Utils.find("research/item_found"):
                    Logger.log_msg("Found completed research project.")
                    if self.save_research_result_to_file:
                        Utils.script_sleep(2)
                        Utils.save_screen("research", need_to_update_screen=True)
                    Utils.touch_randomly(self.region['project_click'])
                    Utils.script_sleep(1)
                    Utils.touch_randomly(self.region['project_click'])
                    return True
