import pytesseract
import cv2
import numpy as np
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

