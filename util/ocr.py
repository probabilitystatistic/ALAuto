import pytesseract
import cv2
import numpy as np
import requests
import json
import time
import re
import os
from util.utils import Region, Utils
from util.logger import Logger


class OCR(object):

    def __init__(self):
        # if tesseract is not set with system PATH
        #pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        self.this_is_just_a_place_holder = 1

    @classmethod
    def screen_to_string(self, region, language="eng+chi_tra"):

        save_process_to_file = True
        skip_enlarge = False
        skip_binary = False
        skip_erosion_dilation = False
        enlarge_factor = 10

        x1 = region.x
        x2 = region.x + region.w
        y1 = region.y
        y2 = region.y + region.h
        source = Utils.screen[y1:y2, x1:x2]
        feed = source

        # resize image
        if not skip_enlarge:
            source = feed
            NewWidth=source.shape[1]*enlarge_factor
            NewHeight=source.shape[0]*enlarge_factor
            enlarged = cv2.resize(source,(int(NewWidth),int(NewHeight)))
            if save_process_to_file:
                cv2.imwrite("1_enlarged.png", enlarged)
            feed = enlarged


        # to binary map(only black and white)
        if not skip_binary:
            source = feed
            source, img_bin = cv2.threshold(source,128,255,cv2.THRESH_BINARY | cv2.THRESH_OTSU)
            binary = cv2.bitwise_not(img_bin)
            if save_process_to_file:
                cv2.imwrite("2_binary.png", binary)
                feed = binary

            # erosion and dilation to erase noise
            if not skip_erosion_dilation:
                source = feed
                kernel = np.ones((2, 1), np.uint8)
                eroded = cv2.erode(source, kernel, iterations=1)
                dilated = cv2.dilate(eroded, kernel, iterations=1)
                if save_process_to_file:
                    cv2.imwrite("3_erode_dilate.png", dilated)
                feed = dilated

        # detection with tesseract
        if language == "number":
            result = pytesseract.image_to_string(feed, lang='eng', config="-c tessedit_char_whitelist=0123456789")
        else:
            result = pytesseract.image_to_string(feed, lang=language)
        Logger.log_debug("OCR return:")
        Logger.log_debug(str(result))
        return str(result)


    @classmethod
    def screen_to_string_by_OCRspace(self, region, mode="cht", phrase_to_search=[]):

        key = '7e9f7ffb3988957'

        x1 = region.x
        x2 = region.x + region.w
        y1 = region.y
        y2 = region.y + region.h

        image = Utils.screen[y1:y2, x1:x2]
        cv2.imwrite("ocrspace_temporary.png", image)
        filename = 'ocrspace_temporary.png'

        if mode == "cht":
            payload = {'isOverlayRequired': False,
                    'apikey': key,
                    'scale': True,
                    'language': 'cht',
                    'OCRengine': 1,
               }
        elif mode == "eng+number" or mode == "number":
            payload = {'isOverlayRequired': False,
                    'apikey': '7e9f7ffb3988957',
                    'scale': True,
                    'language': 'eng',
                    'OCRengine': 2,
               }   

        start_time = time.time()
        with open(filename, 'rb') as f:
            response = requests.post('http://api.ocr.space/parse/image',
                                     files={'filename': f},
                                     data=payload,
                                    )
        end_time = time.time()   
        Logger.log_msg('OCR takes {} seconds to process.'.format(end_time - start_time))
        response_json = response.json()
        parsed_text = response_json["ParsedResults"][0]["ParsedText"]

        if os.path.exists("ocrspace_temporary.png"):
            os.remove("ocrspace_temporary.png")
        
        Logger.log_debug('===== Parsed text =====')
        Logger.log_debug(parsed_text)

        # return parsed text if no phrase to search is specified, otherwise return a list of integer
        #   specifying the index of matched phrase in the phrase_to_search list.
        if phrase_to_search == []:
            if mode == "number":
                if re.sub("[^0-9]", "", parsed_text) == "":
                    Logger.log_warning("No number read by OCR. Returning 99999.")
                    return 99999
                else:
                    return re.sub("[^0-9]", "", parsed_text)
            else:
                return parsed_text
        else:
            match_list = []
            for i in range(len(phrase_to_search)):
                if phrase_to_search[i] in parsed_text:
                    match_list.append(i)
            return match_list
        

        
        
        
        

    
    
    
    
    
    
    
    
    

    
    
    
    
    
    
    
    


    
    
    
    
