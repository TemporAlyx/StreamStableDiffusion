# SimpleStableDiffusionNotebook
A simple ipython notebook using stable diffusion for text to image synthesis

A Massive thank you and shoutout to the open source communities, with collaboration between Stability.ai, LAION, EleutherAI, and HuggingFace to create the StableDiffusion model that makes this possible.
Code largely based entirely off of the examples provided here https://huggingface.co/CompVis/stable-diffusion-v1-4

As I continue to play around with this software I'll add try and add features and conveniance for this notebook to be a simple way of using StableDiffusion.

This notebook only requires a few python libraries, including ipython/jupyter notebooks and pytorch installed. 

# Core Concepts (some still to develop)
- Simple interface to quickly queue and test prompts and ideas
- Any image displayed is saved in some form, along with the prompt for easy copy/paste with credits and optional settings. Ideally anyone who is given the image can recreate the same settings for their own variations.
- I include basic code that optionally disables the integrated safety filter, while I fully support that this is included by default, I also appreciate the ease to remove it.
- I do not make any attempts to disable the integrated invisible encoding that embeds information in the image to denote the image as ai generated. This is good. Please do not intentially avoid this functionality.
- attempts are made to determine maximum and minimum ram settings for various functions and batch sizes.


# Planned Features:
- refactor so that generating calls a function, and various parameters are modifiable via that
- fix naming so as to never overwrite any files, and output
- build a queuing system
