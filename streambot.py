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
import time
import numpy as np
from emoji import demojize
from PIL import Image, ExifTags
from safetyfilter import check_safety


default_config = {
    "server": "irc.chat.twitch.tv",
    "port": 6667,
    "nickname": "put_your_twitch_username_here",
    "token": "oauth:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "channel": "#put_the_channel_name_here",
    "webui_url": "http://localhost:7860",
    "output_folder_name": "streamable_output",
    "default_args": {
        "prompt": "",
        "n_imgs": 4
        }
    }

# load config
if not os.path.isfile(os.path.join(os.getcwd(), 'config.json')): # if no config is found, create default one and save it
    with open(os.path.join(os.getcwd(), 'config.json'), 'w') as f:
        json.dump(default_config, f, indent=4)
    
    # exit program
    print('config.json not found, default config created, please fill in the details and restart the program')
    time.sleep(5)
    exit()

# load config
with open(os.path.join(os.getcwd(), 'config.json')) as f:
    config = json.load(f)

    if config == default_config:
        print('config.json has not been configured, or is incorrectly configured, please fill in the details and restart the program')
        time.sleep(30)
        exit()

    server = config['server']
    port = config['port']
    nickname = config['nickname']
    token = config['token']
    channel = config['channel']
    output_folder_name = config['output_folder_name']
    default_args = config['default_args']
    webui_url = config['webui_url']


# handles splitting complex additional arguments in command request
def parse_arguments(copied_string):
    params = {}
    for arg in copied_string.split(' '):
        if ':' in arg:
            key, val = arg.split(':')
            params[key] = val
    params['prompt'] = ' '.join([x for x in copied_string.split(' ') if ':' not in x])
    return params

def command_lookup(msg, usr):
    global default_args
    if msg[0] == '!':  # is command
        cmd = msg.split(' ')[0].lower()[1:]
        args = ' '.join(msg.split(' ')[1:]).replace('\r', '').replace('\n', '')

        print('found !command: !' + cmd + ', with args: ' + args)
        
        if cmd == 'generate' or cmd == 'gen':
            parsed_args = parse_arguments(args)
            params = default_args.copy()
            params.update(parsed_args)
            params['user'] = usr
            params['full_message'] = msg
            
            command_queue.append([generate, params])
            
        elif (cmd == 'clear' or cmd == 'cl' or cmd == 'c') and usr == nickname:
            clear()
            
        elif (cmd == 'approve' or cmd == 'app' or cmd == 'a') and usr == nickname:
            approve()

        else:
            print('command not found')

def generate(webui, args):
    webui.generate(args)

def approve():
    global active_image
    update_image(active_image[0], active_image[1], override=True)

def clear():
    empty_image = Image.fromarray(np.zeros((512,512,3), dtype=np.uint8))
    update_image(empty_image, {'prompt': '', 'user': '', 'is_safe': True})

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
    exif = img.getexif()
    if exif is not None:
        params = exif[0x9286].decode('utf-8')
        if params[:8] == 'gridflag':
            params = params[8:]
            params = params.split('||||')
            params = [json.loads(x) for x in params]
        else:
            params = json.loads(params)
    else:
        params = {} # if no metadata, return empty dict
        print('no metadata found for stream.jpg image')
    return [img, params]

def check_outputs(webui, command):
    return webui.get_outputs(command)
            
# update stream.jpg image on disk using PIL and saving params to metadata
# depending on length of list create image grid of appropriate size, and check if images are safe
# then save to disk with metadata exif comment tag
# images and params can both independantly be lists or single items, would be easier if we could assume that single items are generation requests, and lists are for grids
def update_image(images, params, override=None):  # honestly this function is a mess and should be cleaned up
    global active_image

    if type(images) is not list: # janky
        images = [images]
    if type(params) is not list:
        params = [params]

    assert len(images) == len(params) # makes things much easier if they are the same length, although could be instances where its multiple images with one set of params

    checked_images = []
    checked_params = []
    for i in range(len(images)):
        if 'is_safe' in params[i].keys():
            if override is None: override = params[i]['is_safe']
            else: override = False

        if override:
            checked_image = images[i]
            is_safe = True
        else:
            new_checked_image, is_safe = check_safety(images[i])
            if type(new_checked_image) is list: # sanity check
                if len(new_checked_image) == 1:
                    new_checked_image = new_checked_image[0]
                    is_safe = is_safe[0]
        cparams = params[i].copy()
        cparams['is_safe'] = is_safe
        checked_images.append(new_checked_image)
        checked_params.append(cparams)

    if len(images) == 1:
        img = checked_images[0]
        par = json.dumps(checked_params[0]).encode('utf-8')
    else:
        grid_size = len(images) // 2
        if grid_size ** 2 != len(images):
            print('grid size not square, will have empty squares')
        img = image_grid(images, grid_size, grid_size)
        par = ('gridflag' + '||||'.join([json.dumps(x) for x in checked_params])).encode('utf-8') # don't know if this will work but it's worth a shot
        output_list.append([images, checked_params]) # if its a grid we want to add it to the output list so that we can access it later

    # find the exif tag for user comment and add params to it
    exif = img.getexif() # should use ExifTags to search for UserComments so its clearer
    exif[0x9286] = par
    img.save(os.path.join(os.getcwd(),output_folder_name,'stream/stream.jpg'), quality=95, exif=exif)
    active_image = [images, checked_params]


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
    
def create_socket():
    print('connecting to twitch...', end='')
    try:
        sock = socket.socket()
        sock.connect((server, port))
        sock.settimeout(1.0)

        sock.send(f"PASS {token}\n".encode('utf-8'))
        sock.send(f"NICK {nickname}\n".encode('utf-8'))
        sock.send(f"JOIN {channel}\n".encode('utf-8'))
    except:
        print('failed')
        return None
    print('success')
    return sock

def close_socket(sock, msg='error'):
    sock.close()
    print(f'{msg}; socket has been closed')
    return None

def main():
    global active_image, active_command, commands_left_in_batch, command_queue, output_list, Webui_Interface, nickname, channel, server, port, token

    sock = create_socket()
    
    while True:
        try:
            if sock is None:
                print('socket disconnected, retrying connection...')
                sock = create_socket()
            resp = sock.recv(2048).decode('utf-8')
            print(resp)

            if resp.startswith('PING'):
                sock.send("PONG\n".encode('utf-8'))
                print('PONG')
                
            elif len(resp) > 0:
                last_msg = demojize(resp)
                msg_deconstruct = re.search(':(.*)\!.*@.*\.tmi\.twitch\.tv PRIVMSG #(.*) :(.*)', last_msg)
                if msg_deconstruct is not None:
                    user, chl, msg = msg_deconstruct.groups()
                    command_lookup(msg, user)

        except ConnectionAbortedError:
            sock = close_socket(sock, 'connection aborted')
        except ConnectionResetError:
            sock = close_socket(sock, 'connection reset')
        except KeyboardInterrupt:
            sock = close_socket(sock, 'keyboard interrupt')
        except socket.timeout:
            pass
            
        if active_command is None:
            if len(command_queue) > 0:
                next_command = command_queue.pop(0)
                next_command[0](Webui_Interface, next_command[1])
                active_command = next_command
                commands_left_in_batch = active_command[1]['n_imgs']
                print(f'running command {active_command[0].__name__}, with args {active_command[1]}, {commands_left_in_batch} images left in batch')
        else:
            images, params = check_outputs(Webui_Interface, active_command) # the check to prevent grabbing images before generation is done isnt working well
            if len(images) > 0: 

                print(f'!{active_command[0].__name__} command is done..')
                images = process_images(images)
                for i in range(len(images)):
                    output_list.append([images[i], params[i]])
                if not params:
                    print('warning: no params returned from command')

                full_params = []
                for i in range(len(params)):
                    f_params = active_command[1].copy()
                    f_params.update(params[i])
                    full_params.append(f_params)
                update_image(images, full_params)

                commands_left_in_batch -= 1

                #  if thats the last image in the batch, create grid update image
                if commands_left_in_batch == 0:
                    print('batch done, creating grid...', end='')
                    images_from_this_batch = output_list[-active_command[1]['n_imgs']:]
                    output_list = output_list[:-active_command[1]['n_imgs']]

                    # images_from_this_batch are 
                    images = []
                    params = []
                    for i in range(len(images_from_this_batch)):
                        images.append(images_from_this_batch[i][0])
                        params.append(images_from_this_batch[i][1])
                    update_image(images, params)
                    active_command = None
                    print('done')
                else:
                    print(f'running next command: !{active_command[0].__name__} \nwith args: {active_command[1]} \n {commands_left_in_batch} images left in batch')
                    active_command[0](Webui_Interface, active_command[1])


            # might need differeing logic for how to communicate with interface for grabbing data


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