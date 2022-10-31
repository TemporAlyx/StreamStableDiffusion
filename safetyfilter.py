# straight ripped from how the webui does it
# along with copying from https://github.com/huggingface/diffusers/blob/main/src/diffusers/pipelines/stable_diffusion/safety_checker.py
# in order to overload the safety checker to not automatically black out nsfw content

from diffusers.pipelines.stable_diffusion.safety_checker import StableDiffusionSafetyChecker
from transformers import AutoFeatureExtractor
from PIL import Image, ImageFilter
import torch
import torch.nn as nn
import numpy as np

safety_model_id = "CompVis/stable-diffusion-safety-checker"
safety_feature_extractor = None
safety_checker = None

def numpy_to_pil(images):
    """
    Convert a numpy image or a batch of images to a PIL image.
    """
    if images.ndim == 3:
        images = images[None, ...]

    pil_images = []
    for image in images: # I want more checks in here for dtype, as I'm getting strange color issues, possible dtyle scaling
        if np.max(image) < 1:
            image = (image * 255).round().astype("uint8")
        else:
            image = image.round().astype("uint8")
        pil_images.append(Image.fromarray(image))

    return pil_images


def cosine_distance(image_embeds, text_embeds):
    normalized_image_embeds = nn.functional.normalize(image_embeds)
    normalized_text_embeds = nn.functional.normalize(text_embeds)
    return torch.mm(normalized_image_embeds, normalized_text_embeds.t())

class OverrideStableDiffusionSafetyChecker(StableDiffusionSafetyChecker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @torch.no_grad()
    def forward(self, clip_input, images):
        pooled_output = self.vision_model(clip_input)[1]  # pooled_output
        image_embeds = self.visual_projection(pooled_output)

        special_cos_dist = cosine_distance(image_embeds, self.special_care_embeds).cpu().numpy()
        cos_dist = cosine_distance(image_embeds, self.concept_embeds).cpu().numpy()

        result = []
        batch_size = image_embeds.shape[0]
        for i in range(batch_size):
            result_img = {"special_scores": {}, "special_care": [], "concept_scores": {}, "bad_concepts": []}

            # increase this value to create a stronger `nfsw` filter
            # at the cost of increasing the possibility of filtering benign images
            adjustment = 0.01 # setting this to 0.01 here, I really don't know at all what this does, but it worked before to catch remaining false positives

            for concept_idx in range(len(special_cos_dist[0])):
                concept_cos = special_cos_dist[i][concept_idx]
                concept_threshold = self.special_care_embeds_weights[concept_idx].item()
                result_img["special_scores"][concept_idx] = round(concept_cos - concept_threshold + adjustment, 3)
                if result_img["special_scores"][concept_idx] > 0:
                    result_img["special_care"].append({concept_idx, result_img["special_scores"][concept_idx]})
                    # adjustment = 0.01  # this confuses me, shouldnt it be set above?

            for concept_idx in range(len(cos_dist[0])):
                concept_cos = cos_dist[i][concept_idx]
                concept_threshold = self.concept_embeds_weights[concept_idx].item()
                result_img["concept_scores"][concept_idx] = round(concept_cos - concept_threshold + adjustment, 3)
                if result_img["concept_scores"][concept_idx] > 0:
                    result_img["bad_concepts"].append(concept_idx)

            result.append(result_img)

        has_nsfw_concepts = [len(res["bad_concepts"]) > 0 for res in result]

        # for idx, has_nsfw_concept in enumerate(has_nsfw_concepts): # this is handled below in check_safety, which blurs instead of blacking out, entertainment value
        #     if has_nsfw_concept:
        #         images[idx] = np.zeros(images[idx].shape)  # black image

        # if any(has_nsfw_concepts):  #this is already done in streambot.py
        #     logger.warning(
        #         "Potential NSFW content was detected in one or more images. A black image will be returned instead."
        #         " Try again with a different prompt and/or seed."
        #     )

        return images, has_nsfw_concepts




# check and replace nsfw content
def check_safety(x_image):
    global safety_feature_extractor, safety_checker
    if x_image is not list:
        x_image = [x_image]
    x_image = [np.asarray(x) for x in x_image]
    if safety_feature_extractor is None:
        safety_feature_extractor = AutoFeatureExtractor.from_pretrained(safety_model_id)
        safety_checker = OverrideStableDiffusionSafetyChecker.from_pretrained(safety_model_id)
    safety_checker_input = safety_feature_extractor(x_image, return_tensors="pt")
    x_checked_image, has_nsfw_concept = safety_checker(images=x_image, clip_input=safety_checker_input.pixel_values)
    for i in range(len(has_nsfw_concept)):
        if has_nsfw_concept[i]: # use a guassian blur to blur out potentially nsfw content in image
            x_checked_image[i] = numpy_to_pil(x_image[i])[0].filter(ImageFilter.GaussianBlur(radius=27))
            print('potential NSFW image detected, saving blurred image to stream instead')
        else: 
            x_checked_image[i] = numpy_to_pil(x_image[i])[0]
    return x_checked_image, has_nsfw_concept

# this all works, but it seems like its loading the model each time
# may be easier to rewrite this as a class and load the model once, keeping it in memory
# that or figure out how bad it would be to run it on cpu