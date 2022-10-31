import re
import os, time
import requests
from PIL import Image


class Interfacer:

    # need to handle cmd prompts
    def start_webui(self):
        print('starting webui...')
        cwd = os.getcwd()
        os.chdir(self.webui_loc)
        os.startfile('webui-user.bat')
        print('webui is starting, wait until it is ready')
        os.chdir(cwd)
    
    def __init__(self, url, webui_loc):
        self.webui_loc = webui_loc
        self.url = url

        self.default_request_data = {
            "fn_index": 13,
            "data": [
                "",        # prompt
                "",        # negative prompt
                "None",
                "None",
                20,        # steps
                "Euler a", # sampler
                False,     # restore faces
                False,
                1,         # batch count ?
                1,         # batch size ? 
                7,         # cfg scale
                -1,
                -1,
                0,
                0,
                0,
                False,
                512,       # height
                512,       # width
                False,     # high res fix?
                0.7,       # high res denoise strength
                512,
                512,
                "None",
                False,
                False,
                None,
                "",
                "Seed",
                "",
                "Nothing",
                "",
                True,
                False,
                False,
                None,
                "",
                ""
            ],
            "session_hash": "fjrjpcj8z1"
        }

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

        self.output_location = os.path.join(self.webui_loc, 'outputs', 'txt2img-images')

        self.last_output = None
        
        self.start_webui()
        


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

        try:
            r = requests.post(self.url + '/api/predict/', json=new_request, timeout=0.05)
        except requests.exceptions.ReadTimeout:
            pass
        # print(r.text, r.status_code, r.reason)
        
    def get_outputs(self, args):
        # check if done generating
        # get most recent image from the output_location
        most_recent_img = os.listdir(self.output_location)[-1]


        if most_recent_img != self.last_output:
            self.last_output = most_recent_img

            img = Image.open(os.path.join(self.output_location, most_recent_img))

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

# def get_images():
#     pass

# def set_tab():
#     pass

# def variation():
#     pass

# def upscale():
#     pass