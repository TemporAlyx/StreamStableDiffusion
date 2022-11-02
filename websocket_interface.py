import base64
import io
import re
import os, time
from requests_futures.sessions import FuturesSession
import requests
from PIL import Image


class Interfacer:
    
    def __init__(self, url, webui_os='windows'):
        self.url = url
        self.webui_os = webui_os
        self.session = FuturesSession(max_workers=1)

        self.default_request_data = {
            "fn_index": 13,
            "data": [
                "",        # prompt
                "",        # negative prompt
                "None", "None",
                20,        # steps
                "Euler a", # sampler
                False,     # restore faces
                False,
                1,         # batch count ?
                1,         # batch size ? 
                7.0,         # cfg scale
                -1, -1, 0, 0, 0, False,
                512,       # height
                512,       # width
                False,     # high res fix?
                0.7,       # high res denoise strength
                512, 512, "None", False, False, None, "", "Seed", "", "Nothing", "", True, False, False, None, "", ""
            ]
        }
        if self.webui_os == 'linux':
            self.default_request_data['fn_index'] = 100

        self.arg_mapping = {
            'prompt': 0,
            'negative_prompt': 1,
            'seed': 11,
            'steps': 4,
            'height': 17,
            'width': 18,
            'cfg_scale': 10,
            'sampler': 5,
        }

        self.current_request = None
        self.current_params = {}


    def generate(self, args):
        # submit a post request to the url
        
        new_request_list = self.default_request_data['data'].copy()

        # check for negative weight deliminator in prompt '###'
        if '###' in args['prompt']:
            args['prompt'], args['negative_prompt'] = args['prompt'].split('###')
            args['negative_prompt'] = args['negative_prompt'].strip()

        for arg in args:
            if arg in self.arg_mapping:
                new_request_list[self.arg_mapping[arg]] = args[arg]
        new_request = self.default_request_data.copy()
        new_request['data'] = new_request_list

        self.current_params = args
        self.current_request = self.session.post(self.url + '/api/predict/', json=new_request)
        

    def get_outputs(self, args=None):
        # check if current request is done
        if self.current_request is not None:
            if self.current_request.done():
                # get the response
                resp = self.current_request.result()

                if self.webui_os == 'windows':
                    b64img = resp.json()['data'][0][0][22:]
                    imagebytes = base64.b64decode(b64img)
                    img = Image.open(io.BytesIO(imagebytes))

                if self.webui_os == 'linux':
                    imgloc = resp.json()['data'][0][0]['name']
                    img = requests.get(self.url + '/file=' + imgloc)
                    img = Image.open(io.BytesIO(img.content))

                self.current_request = None
                params = self.current_params

                return [img], [params]
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

# def variation():
#     pass

# def upscale():
#     pass