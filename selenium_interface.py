import re
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

import os, time
import tkinter as tk

class Interfacer:

    # need to handle cmd prompts
    # def start_webui(self):
    #     os.system(os.path.join(self.webui_loc, 'webui.cmd'))
        # time.sleep(60)
    
    def __init__(self, url="http://localhost:7860/", webui_loc=os.getcwd()):
        self.webui_loc = webui_loc  # probably dont need
        self.url = url
        
        # self.start_webui()
        
        print("Opening browser...", end='')

        self.driver = webdriver.Firefox()
        self.driver.get(self.url)
        
        print("done")
        
        self.update_content()
        
        self.elements = {
            'prompt': lambda x: x.find_element(By.CSS_SELECTOR, "input[class*='gr-text-input']"),
            'active_tab': lambda x: x.find_element(By.CSS_SELECTOR, "button[class*='bg-white']"),
            'all_tabs': lambda x: x.find_elements(By.CSS_SELECTOR, "button[class*='px-4 pb-2']"),
            'guidance_slider': lambda x: x.find_element(By.CSS_SELECTOR, "input[step*='0.5']"),
            # 'imgs_per_batch_slider': lambda x: x.find_element(By.CSS_SELECTOR, "input[id*='range_id_109']"),
            # 'num_batches_slider': lambda x: x.find_element(By.CSS_SELECTOR, "input[id*='range_id_110']"),
            'n_gen_sliders': lambda x: x.find_elements(By.CSS_SELECTOR, "input[max*='50']"),
            'steps_slider': lambda x: x.find_element(By.CSS_SELECTOR, "input[max*='250']"),
            'sampler_dropdown': lambda x: x.find_element(By.CSS_SELECTOR, "select[class*='gr-input']"),
            'refresh_finished': lambda x: x.find_element(By.CSS_SELECTOR, "button[class*='bg-white']"),
            'images': lambda x: x.find_elements(By.CSS_SELECTOR, "img[class*='h-full w-full']"),
            'copy_params': lambda x: x.find_element(By.CSS_SELECTOR, "div[data-testid*='textfield']"),
            'is_finished_generating': lambda x: x.find_element(By.CSS_SELECTOR, "textarea[placeholder*='Job Status']"),
            'generate_button': lambda x: x.find_element(By.CSS_SELECTOR, "button[id*='generate']"),
        }
        
    def get_element(self, name):
        self.update_content()  # probably overkill to run every get
        # aught to test before and after timings
        try:
            el = self.elements[name](self.content)
        except:
            el = 'falied to find element' # should probably add logic later on to handle this better
        
        # if name == 'prompt':
        #     return el
        # elif name == 'active_tab':
        #     return el

        if 'slider' in name:
            if el is list:
                return [x.get_property('value') for x in el]
            return el.get_property('value')
        # elif name == 'sampler_dropdown':
        #     return el
        # elif name == 'refresh_finished':
        #     return el
        elif name == 'images':
            return [re.sub('^data:image/.+;base64,', '', x.get_attribute('src')) for x in el]
        elif name == 'copy_params':
            return el.get_attribute('textContent')
        elif name == 'is_finished_generating':
            if el == 'falied to find element':
                return False
            else:
                return True 
        return None

    def set_element(self, name, val=None):
        el = self.elements[name](self.content)
        
        if name == 'prompt':
            el.click()
            el.clear()
            self.driver.switch_to.active_element.send_keys(val)
        elif name == 'generate_button':
            el.click()
            
        # elif name == 'active_tab':
            
        # elif 'slider' in name:
            # if el is list:
            #     return [x.get_property('value') for x in el]
            # return el.get_property('value')
        # elif name == 'sampler_dropdown':
        #     return el
        # elif name == 'refresh_finished':
        #     return el
        # elif name == 'images':
        #     return [re.sub('^data:image/.+;base64,', '', x.get_attribute('src')) for x in el]
        # elif name == 'copy_params':
        #     return el
        
        # return None # could use a return to confirm success
        
    
    def update_content(self):
        app_parent = self.driver.find_element(By.XPATH, "/html/body/gradio-app")
        app_children = self.driver.execute_script('return arguments[0].shadowRoot.children', app_parent)
        self.content = app_children[-1]

    def generate(self, args):
        self.set_element('prompt', args['prompt'])
        self.set_element('generate_button')
        
    def get_outputs(self, args):
        # check if done generating
        if self.get_element('is_finished_generating'):
            imgs = self.get_element('images')
            if len(imgs) > 0:
                params = self.get_element('copy_params')
                params = self.get_params(params) # should check to make sure this is a valid params string
                params = [params for _ in range(len(imgs))]
                return imgs, params
        return [], {}

    # takes a string of params, with the format:
    # example: 
    # '''halloween cat, awesome painting
    # seed:  3609555222   width:  512   height:  512   steps:  50   cfg_scale:  7.5   sampler:  k_lms'''
    # returns a dict of the values
    def get_params(self, copied_string):
        prompt = copied_string.split('\n')[0]
        params = {}
        args = ''.join(copied_string.split('\n')[1].split('\xa0')).split('  ')
        for line in args:
            line = line.split(':')
            if len(line) == 2:
                params[line[0].strip()] = line[1].strip()
        params['prompt'] = prompt
        return params


# def get_settings():
#     pass

# def set_settings():
#     pass

# def get_images():
#     pass

# def set_tab():
#     pass

# def variation():
#     pass

# def upscale():
#     pass