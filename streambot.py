# simple way to get oauth token is via https://twitchapps.com/tmi/ 
# however a more 'proper route would handle authorization itself'
# may have to update token every few months

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


os.chdir(os.path.dirname(os.path.abspath(__file__)))

default_config = {
    "server": "irc.chat.twitch.tv",
    "port": 6667,
    "nickname": "put_your_twitch_username_here",
    "token": "oauth:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "channel": "#put_the_channel_name_here",
    "webui_url": "http://localhost:7860",
    "webui_os": "windows",
    "output_folder_name": "streamable_output",
    "default_args": {
        "prompt": "",
        "n_imgs": 4,
        "sampler": "Euler a",
        "steps": 20
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
    webui_os = config['webui_os']

def reload_config():
    global server, port, nickname, token, channel, output_folder_name, default_args, webui_url
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
    webui_os = config['webui_os']

    

# handles splitting complex additional arguments in command request
def parse_arguments(copied_string):
    params = {}
    for arg in copied_string.split(' '):
        if ':' in arg:
            key, val = arg.split(':')
            params[key] = val
    params['prompt'] = ' '.join([x for x in copied_string.split(' ') if ':' not in x])
    return params

# cfc: check for command, trims any whitespace and checks whether first characters match any of the commands in *cmd
def cfc(msg, *cmd):
    msg = msg.strip()
    for c in cmd:
        if msg.lower().startswith(c):
            return True
    return False

def command_lookup(msg, usr):
    global default_args, active_image
    if msg[0] == '!':  # is command
        msg = msg[1:]
        print('found !command: ' + msg.split(' ')[0])
        args = ' '.join(msg.split(' ')[1:]).replace('\r', '').replace('\n', '')
        
        if cfc(msg, 'generate', 'gen', 'g'):
            parsed_args = parse_arguments(args)
            params = default_args.copy()
            params.update(parsed_args)
            params['user'] = usr
            params['full_message'] = msg
            
            command_queue.append([generate, params])
            print('added generate command to queue')
            
        elif cfc(msg, 'clear', 'c') and usr == nickname:
            clear(); print('cleared image')
            
        elif cfc(msg, 'approve', 'a') and usr == nickname:
            approve(); print('approved image')

        elif cfc(msg, 'params'):
            if type(active_image[1]) is list:
                active_params = get_active_params(active_image[1])
            else:
                active_params = get_active_params([active_image[1]])
            send_message(active_params)
            print('sent params')

        elif cfc(msg, 'seed'):
            if type(active_image[1]) is list:
                seed = [x['seed'] for x in active_image[1]]
            else:
                seed = active_image[1]['seed']
            out_msg = f"seed: {seed}"
            print(out_msg)
            send_message(out_msg)

        elif cfc(msg, 'prompt'):
            if type(active_image[1]) is list:
                prompt = [x['prompt'] for x in active_image[1]]
                if all(x == prompt[0] for x in prompt): # https://stackoverflow.com/questions/3787908/python-determine-if-all-items-of-a-list-are-the-same-item
                    prompt = prompt[0]
            else:
                prompt = active_image[1]['prompt']
            out_msg = f"prompt: {prompt}"
            print(out_msg)
            send_message(out_msg)

        elif cfc(msg, 'reconfig'):
            reload_config()
            print('reloaded config')

        else:
            print('command not found')

# takes a list of param dicts and grabs essential print information, condenses duplicates
def get_active_params(list_of_dicts):
    important_params = ['prompt', 'seed', 'steps', 'cfg_scale', 'sampler']
    out = []
    for p in important_params:
        part = []
        for d in list_of_dicts:
            if p in d:
                part.append(d[p])
        if len(part) == 1:
            out.append(f"{p}: {part[0]}")
        elif len(part) > 1:
            if all(x == part[0] for x in part):
                out.append(f"{p}: {part[0]}")
            else:
                out.append(f"{p}: {part}")
    return ', '.join(out)

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

# sends message to channel
def send_message(msg):
    global sock, channel
    msg = str(msg) # make sure it's a string
    sock.send(f"PRIVMSG {channel} :{msg}\r\n".encode('utf-8'))


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
            # if image is a grid we also want to split the grid up into individual images and return them
            
            n_imgs = params[0]['n_imgs']
            grid_size = int(np.ceil(np.sqrt(n_imgs)))

            # split image into grid based on number of images
            # set M and N according the size of the image divided by the grid size
            M, N = img.size[0] // grid_size, img.size[1] // grid_size

            im = np.array(img) # https://stackoverflow.com/questions/5953373/how-to-split-image-into-multiple-pieces-in-python
            tiles = [im[x:x+M,y:y+N] for x in range(0,im.shape[0],M) for y in range(0,im.shape[1],N)]  # unsure if this will untule the grid correctly
            img = [Image.fromarray(x) for x in tiles]

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
def update_image(images, params, override=None):  # should rewrite this to be two different functions, one for single images, and one for grids
    global active_image

    if type(images) is not list: # janky
        images = [images]
    if type(params) is not list:
        params = [params]

    assert len(images) == len(params) # makes things much easier if they are the same length, although could be instances where its multiple images with one set of params

    # could maybe take part of this block out as a function for checking/approving images with override
    checked_images = []
    checked_params = []
    for i in range(len(images)):
        if override is None: 
            if 'is_safe' in params[i].keys():
                override = params[i]['is_safe']
            else: 
                override = False

        if override: # should add if override is None, and if False then just blur image here instead of sending to safety checker
            checked_image = images[i]
            is_safe = True
        else:
            checked_image, is_not_safe = check_safety(images[i])
            if type(checked_image) is list: # sanity check
                if len(checked_image) == 1:
                    checked_image = checked_image[0]
                    is_safe = not is_not_safe[0]
        cparams = params[i].copy()
        cparams['is_safe'] = is_safe
        checked_images.append(checked_image)
        checked_params.append(cparams)
    active_image = [images, checked_params]

    if len(checked_images) == 1:
        img = checked_images[0]
        par = json.dumps(checked_params[0]).encode('utf-8')
        output_list.append([images[0], checked_params[0]])
    else:
        grid_size = int(np.ceil(np.sqrt(len(checked_images))))
        if grid_size ** 2 != len(checked_images):
            print('grid size not square, will have empty squares')
        img = image_grid(checked_images, grid_size, grid_size)
        par = ('gridflag' + '||||'.join([json.dumps(x) for x in checked_params])).encode('utf-8') # don't know if this will work but it's worth a shot
        output_list.append([images, checked_params]) # if its a grid we want to add it to the output list so that we can access it later

        image_grid(images, grid_size, grid_size).save(os.path.join(os.getcwd(), output_folder_name, 'stream_unf.jpg'), exif=par)
        os.startfile(os.path.join(os.getcwd(), output_folder_name, 'stream_unf.jpg'))

    # find the exif tag for user comment and add params to it
    exif = img.getexif() # should use ExifTags to search for UserComments so its clearer
    exif[0x9286] = par
    img.save(os.path.join(os.getcwd(),output_folder_name,'stream/stream.jpg'), quality=95, exif=exif)

    # save user who requested image to a text file, along with a truncated version of the prompt
    with open(os.path.join(os.getcwd(),output_folder_name,'stream/user.txt'), 'w') as f:
        from_user = checked_params[0]['user']
        prompt = checked_params[0]['prompt']
        if len(prompt) > 40:
            prompt = prompt[:40] + '\n' + prompt[40:]
            if len(prompt) > 82:
                prompt = prompt[:82] + '\n' + prompt[82:]
                if len(prompt) > 124:
                    prompt = prompt[:124] + '...'
        f.write(from_user + ':\n' + prompt)
    


def update_generate_text(txt):
    with open(os.path.join(os.getcwd(),output_folder_name,'stream/generate.txt'), 'w') as f:
        f.write(txt)


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

if not os.path.isfile(os.path.join(os.getcwd(),output_folder_name,'stream/stream.jpg')):
    # save blank image to stream.jpg
    img = Image.new('RGB', size=(512, 512), color=(0, 0, 0))
    exif = img.getexif() # should use ExifTags to search for UserComments so its clearer
    exif[0x9286] = json.dumps({}).encode('utf-8')
    img.save(os.path.join(os.getcwd(),output_folder_name,'stream/stream.jpg'), quality=95, exif=exif)
else:
    active_image = load_image(os.path.join(os.getcwd(),output_folder_name,'stream/stream.jpg'))

# check if generate.txt exists, if not create it
if not os.path.isfile(os.path.join(os.getcwd(),output_folder_name,'stream/generate.txt')):
    with open(os.path.join(os.getcwd(),output_folder_name,'stream/generate.txt'), 'w') as f:
        f.write('!generate stablediffusion v1.5')

# check if user.txt exists, if not create it
if not os.path.isfile(os.path.join(os.getcwd(),output_folder_name,'stream/user.txt')):
    with open(os.path.join(os.getcwd(),output_folder_name,'stream/user.txt'), 'w') as f:
        f.write('')

# # check if prompt.txt exists, if not create it
# if not os.path.isfile(os.path.join(os.getcwd(),output_folder_name,'stream/prompt.txt')):
#     with open(os.path.join(os.getcwd(),output_folder_name,'stream/prompt.txt'), 'w') as f:
#         f.write('')

from websocket_interface import Interfacer
Webui_Interface = Interfacer(webui_url, webui_os=webui_os)
sock = None #aught to just rewrite this all to be a class
    
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
    global active_image, active_command, commands_left_in_batch, command_queue, output_list, Webui_Interface, nickname, channel, server, port, token, sock

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
                update_generate_text('!generate stablediffusion v1.5') # should make sure this isnt repeatedly called if it's already set to this
        else:
            images, params = check_outputs(Webui_Interface, active_command)
            if len(images) > 0: 

                print(f'!{active_command[0].__name__} command is done..', end='')
                # update_generate_text(f'approving image '+str((active_command[1]['n_imgs'] - commands_left_in_batch) + 1)+'/'+str(active_command[1]['n_imgs']))

                # check whether images are PIL Images or base64 strings
                # if isinstance(images[0], str):
                #     images = process_images(images)

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
                    # print(f'running next command: !{active_command[0].__name__} \nwith args: {active_command[1]}')
                    print(f'{commands_left_in_batch} images left in batch, {len(command_queue)} remaining commands left in queue') 
                    active_command[0](Webui_Interface, active_command[1])
            else:
                u = f'generating image '+str((active_command[1]['n_imgs'] - commands_left_in_batch) + 1)+'/'+str(active_command[1]['n_imgs'])
                if len(command_queue) > 0:
                    u += f', queued: {len(command_queue)}'
                update_generate_text(u)


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