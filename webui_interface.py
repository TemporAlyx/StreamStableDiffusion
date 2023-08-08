import io
import os
import requests
import base64
from PIL import Image
from requests_futures.sessions import FuturesSession


class API_Interface:
    def __init__(self, url):
        self.url = url
        self.api_version = "/sdapi/v1/"
        self.session = FuturesSession(max_workers=1)

        self.default_request_data = {
            "enable_hr": False,
            "denoising_strength": 0,
            "firstphase_width": 0,
            "firstphase_height": 0,
            "hr_scale": 2,
            "hr_upscaler": "string",
            "hr_second_pass_steps": 0,
            "hr_resize_x": 0,
            "hr_resize_y": 0,
            "prompt": "",
            "styles": [
                "string"
            ],
            "seed": -1,
            "subseed": -1,
            "subseed_strength": 0,
            "seed_resize_from_h": -1,
            "seed_resize_from_w": -1,
            "sampler_name": "string",
            "batch_size": 1,
            "n_iter": 1,
            "steps": 50,
            "cfg_scale": 7,
            "width": 512,
            "height": 512,
            "restore_faces": False,
            "tiling": False,
            "negative_prompt": "string",
            "eta": 0,
            "s_churn": 0,
            "s_tmax": 0,
            "s_tmin": 0,
            "s_noise": 1,
            "override_settings": {},
            "override_settings_restore_afterwards": True,
            "script_args": [],
            "sampler_index": "Euler",
            "script_name": "string"
        }

        self.current_request = None
        self.current_params = {}
        

    def send_txt2img(self, prompt, args=None):
        self.current_params = self.default_request_data
        # separate potential negative prompt
        if "###" in prompt:
            prompt, negative_prompt = prompt.split("###")
            self.current_params["negative_prompt"] = negative_prompt.strip()
        self.current_params["prompt"] = prompt.strip()

        self.current_params["script_name"] = "txt2img" # unsure if this is necessary

        if args is not None:
            # args is a dictionary of arguments to override in the default request data
            for key, value in args.items():
                self.current_params[key] = value

        iti_url = os.path.join(self.url, self.api_version, "txt2img")

        self.current_request = self.session.post(iti_url, json=self.current_params, timeout=10)

    def get_result(self):
        if self.current_request is None:
            return None
        if self.current_request.done():
            result = self.current_request.result()
            self.current_request = None
            return result
        return None
    
    # assume the result is an image
    def get_result_image(self):
        if self.current_request is None:
            return None
        if self.current_request.done():
            result = self.current_request.result()
            self.current_request = None
            result = result.json()['images']
            result = [Image.open(io.BytesIO(base64.b64decode(img))) for img in result]
            return result
        return None