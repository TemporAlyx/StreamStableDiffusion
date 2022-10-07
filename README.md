# StreamStableDiffusion
Simple Twitch bot for StableDiffusion !generate chat commands, facilitated by interfacing with [stable-diffusion-webui](https://github.com/sd-webui/stable-diffusion-webui) via selenium

# Functionality

Generated images are saved to an overwritten stream.jpg file that obs can watch for, as well as a text file to output the prompt and who requested, and a text file for outputing loading messages

Utilizes StableDiffusion's Safety filter to (ideally) prevent any nsfw prompts making it to stream

built in queuing system allows for multiple requests to be stored and ran sequentually


Can connect to a twitch channel chat to search for commands:
- !generate {prompt} # generates an image based off of the given prompt
- !clear             # wipes the current image and text
- !approve           # only the account used to connect the bot can use this command, depending on nsfw settings will 'approve' an image if they were misclassified
- !params            # outputs parameters used to create displayed image to chat
- !seed, !prompt     # outputs seed or prompt for displayed image to chat

# install process: 
This repo relies on https://github.com/sd-webui/stable-diffusion-webui

once the webui (gradio version for now) is up and running, download this repo and run streambot.py

there may be some dependancies not installed by the webui, these can be obtained easily via pip, I plan on setting up a simple .bat/.sh file to make this easier

after running streambot.py once, it will create a config.json, where you can fill in your twitch api info for the bot, as well as the link to the webui if it is not running on localhost

now running streambot.py again will startup the whole script, and you should see in the terminal window it connecting to twtich

in the streamable_outputs/stream folder, there is a stream.jpg, user.txt, and generate.txt, which can be pointed to from obs to display as sources for your stream

with a little luck that should be it

# To Do:
- add a forward and backward command that lets scrolling through previous grid images, select from grid, maybe even slideshow?
- create a system that handles downloading required libraries and programs, so as to make installing a much less difficult process, and a single run script
- create and integrate an optional discord bot that allows posting all stream generations to a designated discord channel, and post links to chat, so users can download their explorations of the latent space
- redo selenium backend to work with the streamlit version, and (ideally) swap it out for whatever websockets/rest endpoint system that the ui uses instead


A massive shoutout to the open source communities that are making the future of AI open to everyone.
Feel free to modify or reuse the code in this repository, as long as it eventually ends up as publicly accessible code for anyone to use/learn from.
