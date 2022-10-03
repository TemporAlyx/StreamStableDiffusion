# straight ripped from how the webui does it
# (which in fairness appears to just be how stablediffusion does it by default)

from diffusers.pipelines.stable_diffusion.safety_checker import StableDiffusionSafetyChecker
from transformers import AutoFeatureExtractor
from PIL import Image, ImageFilter

safety_model_id = "CompVis/stable-diffusion-safety-checker"
safety_feature_extractor = None
safety_checker = None

def numpy_to_pil(images):
    """
    Convert a numpy image or a batch of images to a PIL image.
    """
    if images.ndim == 3:
        images = images[None, ...]
    images = (images * 255).round().astype("uint8")
    pil_images = [Image.fromarray(image) for image in images]

    return pil_images

# check and replace nsfw content
def check_safety(x_image):
    global safety_feature_extractor, safety_checker
    if safety_feature_extractor is None:
        safety_feature_extractor = AutoFeatureExtractor.from_pretrained(safety_model_id)
        safety_checker = StableDiffusionSafetyChecker.from_pretrained(safety_model_id)
    safety_checker_input = safety_feature_extractor(numpy_to_pil(x_image), return_tensors="pt")
    x_checked_image, has_nsfw_concept = safety_checker(images=x_image, clip_input=safety_checker_input.pixel_values)
    for i in range(len(has_nsfw_concept)):
        if has_nsfw_concept[i]: # use a guassian blur to blur out potentially nsfw content in image
            x_checked_image[i] = x_image[i].filter(ImageFilter.GaussianBlur(radius=25))
    return x_checked_image, has_nsfw_concept