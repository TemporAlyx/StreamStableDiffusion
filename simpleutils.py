import matplotlib.pyplot as plt
import os
import time
from PIL import Image

import numpy as np
import torch
import torch.nn as nn
from torch import autocast

import inspect
import warnings
from typing import List, Optional, Union

import torch

from transformers import CLIPFeatureExtractor, CLIPTextModel, CLIPTokenizer

from diffusers.models import AutoencoderKL, UNet2DConditionModel
from diffusers.pipeline_utils import DiffusionPipeline
from diffusers import StableDiffusionPipeline
from diffusers.schedulers import DDIMScheduler, LMSDiscreteScheduler, PNDMScheduler

import warnings
from collections import OrderedDict
from dataclasses import fields
from typing import Any, Tuple


import PIL
from PIL import Image

from transformers import CLIPConfig, CLIPVisionModel, PreTrainedModel
def strip_prompt(prompt):
    return prompt.replace('\n', '').strip('.').strip().replace('/', '-')

def save_image(img, path, overwrite=False):
    if not overwrite:
        if os.path.isfile(path):
            x = 0
            path = path[:-4] + '_' + str(x) + '.png'
            while os.path.isfile(path):
                x += 1
                path = path[:-5] + str(x) + '.png'  # this will wig out after 9 identical calls, but itll still work
        img.save(path)
    else:  # overwrite images displayed directly to stream
        path = path[:-4] + '.jpg'
        img.save(path)  # perhaps other file formats wont break as easily? apparently yes


def generate_images(prompt, pipe, steps=50, guidance=8.0, grid_size=(2, 2), H=512, W=512, seed=None,
      batch_columns=False, update_as_generated=True, save_all_images=True, save_grid=True, output_folder_name="output",
                    disable_safety_checker=False, safety_adjustment=0.5, blank_nsfw=False):

    if not os.path.isdir(os.path.join(os.getcwd(), output_folder_name)):
        os.mkdir(os.path.join(os.getcwd(), output_folder_name))
    if not os.path.isdir(os.path.join(os.getcwd(), output_folder_name, 'stream')):
        os.mkdir(os.path.join(os.getcwd(), output_folder_name, 'stream'))

    stripped_prompt = strip_prompt(prompt)

    if batch_columns:
        prompt = [stripped_prompt] * grid_size[1]
    else:
        prompt = [stripped_prompt]

    if seed is not None:
        generator = torch.Generator("cuda").manual_seed(seed)

    output_name = stripped_prompt[:250]  # windows max filename
    # should change to using image metadata to save prompt and settings

    all_images = []
    all_image_nsfw = []
    print('"' + stripped_prompt + '"' + ' - StableDiffusion v1.4')
    loops = grid_size[0] if batch_columns else grid_size[0] * grid_size[1]
    for i in range(loops):
        with autocast("cuda"):
            if seed is None:
                images, is_nsfw = pipe(prompt,
                              num_inference_steps=steps,  # more steps = potentially more quality default=50
                              guidance_scale=guidance,  # controls how strictly ai adheres to the prompt default=7.5
                              height=H, width=W,  # can extend or contract, but will likely break global coherence
                              disable_safety_checker=disable_safety_checker,
                              safety_adjustment=safety_adjustment,
                              blank_nsfw=blank_nsfw
                              )
            else:
                images, is_nsfw = pipe(prompt, num_inference_steps=steps, guidance_scale=guidance, height=H, width=W,
                              generator=generator,
                              disable_safety_checker=disable_safety_checker,
                              safety_adjustment=safety_adjustment,
                              blank_nsfw=blank_nsfw
                              )  # should use tuple of args to add generator instead of ifelse
        all_images.extend(images)
        all_image_nsfw.extend(is_nsfw)
        if update_as_generated:
            gimgs = [images[i] if not is_nsfw[i] else Image.new('RGB', images[i].size, color=0)
                     for i in range(len(images))]
            grid = image_grid(gimgs, rows=1, cols=len(gimgs))
            save_image(grid, os.getcwd() + '\\' + output_folder_name + '\\stream\\' + 'stream' + '.jpg', overwrite=True)
        grid = image_grid(images, rows=1, cols=len(images))
        fig, ax = plt.subplots(figsize=(9, 3))
        ax.imshow(grid)
        plt.show()
        if save_all_images:
            for j in range(len(images)):  # add check for already saved pictures and add identifier for repeat prompts
                save_image(images[j],
                           os.getcwd() + '\\' + output_folder_name + '\\' + output_name + str(i) + str(j) + '.png')

    #     clear_output(wait=True)
    print('"' + stripped_prompt + '"' + ' - StableDiffusion v1.4')
    grid = image_grid(all_images, rows=grid_size[0], cols=grid_size[1])
    fig, ax = plt.subplots(figsize=(9, 9))
    ax.imshow(grid)
    plt.show()

    if save_grid:
        save_image(grid, os.getcwd() + '\\' + output_folder_name + '\\' + output_name + '.png')
    time.sleep(0.5)
    gimgs = [all_images[i] if not all_image_nsfw[i] else Image.new('RGB', all_images[i].size, color=0)
             for i in range(len(all_images))]
    save_image(grid, os.getcwd() + '\\' + output_folder_name + '\\stream\\' + 'stream_unf' + '.jpg', overwrite=True)
    grid = image_grid(gimgs, rows=grid_size[0], cols=grid_size[1])
    save_image(grid, os.getcwd() + '\\' + output_folder_name + '\\stream\\' + 'stream' + '.jpg', overwrite=True)

def image_grid(imgs, rows, cols):
    assert len(imgs) == rows * cols

    w, h = imgs[0].size
    grid = Image.new('RGB', size=(cols * w, rows * h))

    for i, img in enumerate(imgs):
        grid.paste(img, box=(i % cols * w, i // cols * h))
    return grid