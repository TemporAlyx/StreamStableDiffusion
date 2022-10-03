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
        
        self.driver = webdriver.Firefox()
        self.driver.get(self.url)
        
        # time.sleep(1) # wait for page to load
        
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
            'copy_params': lambda x: x.find_element(By.CSS_SELECTOR, "button[id*='49']"),
            'generate_button': lambda x: x.find_element(By.CSS_SELECTOR, "button[id*='generate']"),
        }
        
    def get_element(self, name):
        self.update_content()  # probably overkill to run every get
        # aught to test before and after timings
        
        el = self.elements[name](self.content)
        
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
            # el is a button element, which copies the params to the clipboard
            # we want to directly get the params without having to use the clipboard
            # so we need to get the params from the button's onclick attribute
            onclick = el.get_attribute('onclick')
            print(onclick)

            return  onclick # feels so hacky to do this
        
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
        imgs = self.get_element('images')
        if imgs:
            params = self.get_element('copy_params')
        else:
            params = None
        return imgs, params


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