# StreamStableDiffusion
Simple Twitch bot for StableDiffusion !generate chat commands, facilitated by interfacing with [stable-diffusion-webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui) via websockets

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
First install the webui from https://github.com/AUTOMATIC1111/stable-diffusion-webui
Then download this repo and run streambot.py

there may be some dependancies not installed by the webui, these can be obtained via pip, I plan on setting up a simple .bat/.sh file to make this easier in the future

after running streambot.py once, it will create a config.json, where you can fill in your twitch api info for the bot, as well as the url for the webui, and the webui file location (the install location of the webui)

now running streambot.py again will startup the whole script, automatically startup an instance of the webui, and you should see in the terminal window it connecting to twitch

in the streamable_outputs/stream folder, there is a stream.jpg, user.txt, and generate.txt, which can be pointed to from obs to display as sources for your stream

with a little luck that should be it

# To Do:
- create a system that handles downloading required libraries and programs, so as to make installing a much less difficult process, and a single run script
- create and integrate an optional discord bot that allows posting all stream generations to a designated discord channel, and post links to chat, so users can download their explorations of the latent space
- add a forward and backward command that lets scrolling through previous grid images, select from grid, maybe even slideshow?
- clean up the presentation of this repo, with images detailing how it can look in action


A massive shoutout to the open source communities that are making the future of AI open to everyone.
Feel free to modify or reuse the code in this repository, as long as it eventually ends up as publicly accessible code for anyone to use/learn from.
