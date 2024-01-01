import base64
import io
import time, sys, traceback
from requests_futures.sessions import FuturesSession
from PIL import Image


class Interfacer:
    
    def __init__(self, url):
        self.url = url
        self.session = FuturesSession(max_workers=1)

        self.default_request_data = {
            'prompt': "",
            'negative_prompt': "",
            'cfg_scale': 7.0,
            'sampler': "Euler a",
            'steps': 28,
            'height': 512,
            'width': 512,
        }

        self.current_request = None
        self.current_params = {}


    def generate(self, args):
        # submit a post request to the url
        
        # new_request_list = self.default_request_data.copy()

        # check for negative weight deliminator in prompt '###'
        if '###' in args['prompt']:
            args['prompt'], args['negative_prompt'] = args['prompt'].split('###')
            args['negative_prompt'] = args['negative_prompt'].strip()

        new_request = self.default_request_data.copy()
        new_request.update(args)

        self.current_params = args
        self.current_request = self.session.post(self.url + '/sdapi/v1/txt2img/', json=new_request)
        

    def get_outputs(self, args=None):
        # check if current request is done
        if self.current_request is not None:
            if self.current_request.done():
                # get the response
                resp = self.current_request.result()
                img = None
                b64img = None

                # check if the response is valid, and if not throw an error prompting the user to check if '--api' flag is set
                try:
                    b64img = resp.json()['images'][0]
                except:
                    # print the base key error stack trace first
                    traceback.print_exc()
                    # then print the error message
                    print("Error: Invalid response from webui. Check if the '--api' flag is set for COMMANDLINE_ARGS in webui-user.bat")
                    # wait 5 seconds before exiting
                    time.sleep(5)
                    sys.exit(1)
                
                imagebytes = base64.b64decode(b64img)
                img = Image.open(io.BytesIO(imagebytes))

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