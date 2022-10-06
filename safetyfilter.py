# straight ripped from how the webui does it

from diffusers.pipelines.stable_diffusion.safety_checker import StableDiffusionSafetyChecker
from transformers import AutoFeatureExtractor
from PIL import Image, ImageFilter

safety_model_id = "CompVis/stable-diffusion-safety-checker"
safety_feature_extractor = None
safety_checker = None

# check and replace nsfw content
def check_safety(x_image):
    global safety_feature_extractor, safety_checker
    if safety_feature_extractor is None:
        safety_feature_extractor = AutoFeatureExtractor.from_pretrained(safety_model_id)
        safety_checker = StableDiffusionSafetyChecker.from_pretrained(safety_model_id)
    safety_checker_input = safety_feature_extractor(x_image, return_tensors="pt")
    x_checked_image, has_nsfw_concept = safety_checker(images=x_image, clip_input=safety_checker_input.pixel_values)
    for i in range(len(has_nsfw_concept)):
        if has_nsfw_concept[i]: # use a guassian blur to blur out potentially nsfw content in image
            x_checked_image[i] = x_image[i].filter(ImageFilter.GaussianBlur(radius=25))
            print('potential NSFW image detected, saving blurred image to stream instead')
    return x_checked_image, has_nsfw_concept

# this all works, but it seems like its loading the model each time
# may be easier to rewrite this as a class and load the model once, keeping it in memory
# that or figure out how bad it would be to run it on cpu