# simple way to get oauth token is via https://twitchapps.com/tmi/ 
# however a more 'proper route would handle authorization itself'
# may have to update token every few months

# should probably change this to load from a txt config
# should also probably stop testing in production buuuuut *shrug*
import base64
import io
import json
import os
import re
import socket
import numpy as np
from emoji import demojize
from PIL import Image, ExifTags
from safetyfilter import check_safety


# load config
with open(os.path.join(os.getcwd(), 'config.json')) as f:
    config = json.load(f)
    server = config['server']
    port = config['port']
    nickname = config['nickname']
    token = config['token']
    channel = config['channel']
    output_folder_name = config['output_folder_name']
    default_args = config['default_args']
    webui_url = config['webui_url']


def parse_arguments(args): # will handle splitting complex additional arguments
    return {'prompt': args} # but for now assume its just all the prompt

def command_lookup(msg, usr):
    global default_args
    if msg[0] == '!':  # is command
        cmd = msg.split(' ')[0].lower()[1:]
        args = ' '.join(msg.split(' ')[1:]).replace('\r', '').replace('\n', '')

        print('found !command: ' + cmd + ', with args: ' + args)
        
        if cmd == 'generate' or cmd == 'gen':
            parsed_args = parse_arguments(args)
            params = default_args.copy()
            params.update(parsed_args)
            params['user'] = usr
            params['full_message'] = msg
            
            for i in range(params['n_imgs']):
                command_queue.append([generate, params])
            
        elif (cmd == 'clear' or cmd == 'cl' or cmd == 'c') and usr == nickname:
            clear()
            
        elif (cmd == 'approve' or cmd == 'app' or cmd == 'a') and usr == nickname:
            approve()

def generate(webui, args):
    webui.generate(args)

def approve():
    global active_image
    update_image(active_image[0], active_image[1], override=True)

def clear():
    # update image with blank black image
    # create numpy black image and convert to PIL image
    update_image(Image.fromarray(np.zeros((512,512,3), dtype=np.uint8)), 
                {'prompt': '', 'user': '', 'is_safe': True})

def image_grid(imgs, rows, cols):
    # assert len(imgs) == rows * cols

    w, h = imgs[0].size
    grid = Image.new('RGB', size=(cols * w, rows * h))

    for i, img in enumerate(imgs):
        grid.paste(img, box=(i % cols * w, i // cols * h))
    return grid

# function that loads image from disk and grabs attributes from custom metadata
def load_image(path):
    img = Image.open(path)
    exif = { ExifTags.TAGS[k]: v for k, v in img._getexif().items() if k in ExifTags.TAGS}
    params = json.loads(exif['UserComment'].decode('utf-8'))
    return [img, params]

def check_outputs(webui, command):
    images, params = webui.get_outputs(command)
    if images:
        return images, params
    return False, None

            
# update stream.jpg image on disk using PIL and saving params to metadata
# depending on length of list create image grid of appropriate size
# then save to disk with metadata exif comment tag
def update_image(images, params, override=None):
    global active_image
    if images is list:
        if len(images) == 1:
            img = images[0]
        else:
            grid_size = len(images) // 2
            img = image_grid(images, grid_size, grid_size)
    else:
        img = images

    # check if is_safe in params
    if 'is_safe' in params.keys():
        if override is None:
            override = params['is_safe']
        else:
            override = False

    # check image for nsfw 
    if override:
        checked_image = img
        is_safe = True
    else:
        checked_image, is_safe = check_safety(img)
        if not is_safe:
            print('potential NSFW image detected, saving blurred image to stream instead')

    params.update({'is_safe': is_safe})

    # find the exif tag for user comment and add params to it
    exif = checked_image.getexif() # should use ExifTags to search for UserComments instead of hardcoding
    exif[0x9286] = json.dumps(params).encode('utf-8')

    checked_image.save(os.path.join(os.getcwd(),output_folder_name,'stream/stream.jpg'), quality=95, exif=exif)
    active_image = [images, params]

# process images from webui by converting from base64 to PIL image
def process_images(images):
    processed_images = []
    for image in images:
        processed_images.append(Image.open(io.BytesIO(base64.b64decode(image))))
    return processed_images


output_list = []  # list of images to be displayed [PILImage, generation_params] optionally + PILImage of unfiltered?
command_queue = []  # list of commands separated by [command_name, dict_of_args]
active_command = None
commands_left_in_batch = 0  # not sure if this is the best way to do this, but this will track images left in batch for final grid creation
active_image = None

if not os.path.isdir(os.path.join(os.getcwd(),output_folder_name)):
    os.mkdir(os.path.join(os.getcwd(),output_folder_name))
if not os.path.isdir(os.path.join(os.getcwd(),output_folder_name,'stream')):
    os.mkdir(os.path.join(os.getcwd(),output_folder_name,'stream'))

if os.path.isfile(os.path.join(os.getcwd(),output_folder_name,'stream/stream.jpg')):
    active_image = load_image(os.path.join(os.getcwd(),output_folder_name,'stream/stream.jpg'))
else:
    clear()

from selenium_interface import Interfacer
Webui_Interface = Interfacer(webui_url)
    

def main():
    global active_image, active_command, commands_left_in_batch, command_queue, output_list, Webui_Interface, nickname, channel, server, port, token

    sock = socket.socket()
    sock.connect((server, port))
    sock.settimeout(1.0)

    sock.send(f"PASS {token}\n".encode('utf-8'))
    sock.send(f"NICK {nickname}\n".encode('utf-8'))
    sock.send(f"JOIN {channel}\n".encode('utf-8'))
    
    while True:
        try:
            resp = sock.recv(2048, socket.MSG_DONTWAIT).decode('utf-8')
            print(resp)

            if resp.startswith('PING'):
                sock.send("PONG\n".encode('utf-8'))
                
            elif len(resp) > 0:
                last_msg = demojize(resp)
                msg_deconstruct = re.search(':(.*)\!.*@.*\.tmi\.twitch\.tv PRIVMSG #(.*) :(.*)', last_msg)
                if msg_deconstruct is not None:
                    user, chl, msg = msg_deconstruct.groups()
                    command_lookup(msg, user)
                    
        except socket.timeout:
            continue
        except ConnectionAbortedError:
            continue
        except KeyboardInterrupt:
            print('closing connection...')
            sock.close()
            break
            
        if active_command == None:
            if len(command_queue) > 0:
                next_command = command_queue.pop(0)
                next_command[0](Webui_Interface, next_command[1])
                active_command = next_command
                print(f'running command {next_command[0].__name__}, with args {next_command[1]}')
                commands_left_in_batch = next_command[1]['n_imgs']
        else:
            images, params = check_outputs(Webui_Interface, active_command)
            if images:
                output_list.append([images, params])
                active_command = None
                images = process_images(images)
                full_params = next_command[1].copy()
                full_params.update(params)
                update_image(images, full_params)
                comands_left_in_batch -= 1  # only works for generating images in batches of one, which is fine given the ram limitations

                #  if thats the last image in the batch, create grid update image
                if commands_left_in_batch == 0:
                    images_from_this_batch = output_list[-next_command[1]['n_imgs']::]
                    update_image(images_from_this_batch, full_params)


            # might need differeing logic for how to communicate with interface for grabbing data
            
    # how hard would it be to rewrite that while loop as a coroutine?
    # attempt to rewrite loop such that it isnt hung on socket.recv

    while True:
        resp = sock.recv(1024, socket.MSG_DONTWAIT).decode('utf-8')





if __name__ == "__main__":
    main()




# def variation():
#     pass

# def upscale():
#     pass


# def rerun():
#     pass

# def shutdown():
#     pass

# def restart():
#     pass