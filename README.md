# StreamStableDiffusionNotebook
A simple ipython notebook to enable users in a twitch chat to generate images on stream.

# Functionality
Uses stable diffusions safety filter to prevent displaying nsfw content on stream, this notebook uses a cracked open version of the safety filter so that you can adjust the threshold. This is not entirely foolproof, but I've yet to see anything explicitly bad on higher settings of the threshold, although it can misclassify benign images.
Generating an image calls an interface with several editable commands in the notebook, defining whether images get saved, whether to generate a grid of images, and what to do in the event of an nsfw image being detected. 

Generated images are saved to an overwritten stream.jpg file that obs can watch for, as well as a text file to output who requested it, and a text file for the prompt

Can connect to a twitch channel chat to search for commands:
!generate {prompt} # generates an image based off of the given prompt
!clear             # wipes the current image
!approve           # only the account used to connect the bot can use this command, depending on nsfw settings will 'approve' an image or grid of images if they were misclassified
!terminate         # only the account used to connect the bot can use this command, simple command stops the bot from running
!regenerate        # reuses the previous prompt and generates a new image/grid of images

# install process: (still to be tested with a clean install)
Unfortunately getting this up and running will take a bit of techincal knowhow
Requires a python (3.9 or above) install, along with a cuda enabled pytorch, as well as cuda itself (unfortunately will only work with cuda gpu).
Currently is using a python notebook and so requires jupyter, but could probably be converted into a simple .py file.

# To Do:
add proper system that saves generation details in image metadata
add a forward and backward command that lets scrolling through previous images, with optional slideshow
create a system that handles downloading required libraries and programs, so as to make installing a much less difficult process
exhaustively test safety filter settings and present data to give people an idea of how safe (and not safe) it is
create gui? would be nice to have sliders and buttons to handle tuning settings and starting/restarting the bot, would also make it more accessible


A Massive thank you and shoutout to the open source communities that made StableDiffusion possible.
Code is based on examples provided here https://huggingface.co/CompVis/stable-diffusion-v1-4
as well as example code from https://github.com/LearnDataSci/articles/tree/master/How%20to%20Stream%20Text%20Data%20from%20Twitch%20with%20Sockets%20in%20Python
