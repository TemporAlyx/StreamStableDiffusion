# simple way to get oauth token is via https://twitchapps.com/tmi/ 
# however a 'proper route would handle authorization itself'
# may have to update token every few months

import json
import os
import re
import socket
import time
import numpy as np
from emoji import demojize
from PIL import Image, ExifTags
from safetyfilter import check_safety

# this is useful to make sure that wherever the script is run from, it can search its surrounding directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))


from streambot_utils import *

# load config
config = load_config()

    # server = config['server']
    # port = config['port']
    # nickname = config['nickname']
    # token = config['token']
    # channel = config['channel']
    # output_folder_name = config['output_folder_name']
    # default_args = config['default_args']
    # webui_url = config['webui_url']


def command_lookup(msg, usr):
    global active_image, config
    if msg[0] == '!':  # is command
        msg = msg[1:]
        print('found !command: ' + msg.split(' ')[0])
        args = ' '.join(msg.split(' ')[1:]).replace('\r', '').replace('\n', '')
        
        if cfc(msg, 'generate', 'gen', 'g'):
            parsed_args = parse_arguments(args)
            params = config['default_args'].copy()
            params.update(parsed_args)
            params['user'] = usr
            params['full_message'] = msg
            
            command_queue.append([generate, params])
            print('added generate command to queue')
            
        elif cfc(msg, 'clear', 'c') and usr == config['nickname']:
            clear(); print('cleared image')
            
        elif cfc(msg, 'approve', 'a') and usr == config['nickname']:
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
            print('reloaded config, note, not all settings can take effect without restarting the script')

        else:
            print('command not found')

def approve():
    global active_image
    update_image(active_image[0], active_image[1], override=True)

def clear():
    empty_image = Image.fromarray(np.zeros((512,512,3), dtype=np.uint8))
    update_image(empty_image, {'prompt': '', 'user': '', 'is_safe': True})

# sends message to channel
def send_message(msg):
    global sock, channel
    msg = str(msg) # make sure it's a string
    sock.send(f"PRIVMSG {config['channel']} :{msg}\r\n".encode('utf-8'))



            
# update stream.jpg image on disk using PIL and saving params to metadata
# depending on length of list create image grid of appropriate size, and check if images are safe
# then save to disk with metadata exif comment tag
# images and params can both independantly be lists or single items, would be easier if we could assume that single items are generation requests, and lists are for grids
def update_image(images, params, override=None):  # should rewrite this to be two different functions, one for single images, and one for grids
    global active_image, config

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

        is_safe = None
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

        image_grid(images, grid_size, grid_size).save(os.path.join(os.getcwd(), config['output_folder_name'], 'stream_unf.jpg'), exif=par)
        os.startfile(os.path.join(os.getcwd(), config['output_folder_name'], 'stream_unf.jpg'))

    # find the exif tag for user comment and add params to it
    exif = img.getexif() # should use ExifTags to search for UserComments so its clearer
    exif[0x9286] = par
    img.save(os.path.join(os.getcwd(),config['output_folder_name'],'stream/stream.jpg'), quality=95, exif=exif)

    # save user who requested image to a text file, along with a truncated version of the prompt
    with open(os.path.join(os.getcwd(),config['output_folder_name'],'stream/user.txt'), 'w') as f:
        from_user = checked_params[0]['user']
        prompt = checked_params[0]['prompt']
        if len(prompt) > 40:
            prompt = prompt[:40] + '\n' + prompt[40:]
            if len(prompt) > 82:
                prompt = prompt[:82] + '\n' + prompt[82:]
                if len(prompt) > 124:
                    prompt = prompt[:124] + '...'
        f.write(from_user + ':\n' + prompt)
    


output_list = []  # list of images to be displayed [PILImage, generation_params] optionally + PILImage of unfiltered?
command_queue = []  # list of commands separated by [command_name, dict_of_args]
active_command = None
commands_left_in_batch = 0  # not sure if this is the best way to do this, but this will track images left in batch for final grid creation
active_image = make_check_folders(config) # creates necessary folders if they don't exist, and returns the active image if it exists


from websocket_interface import Interfacer
Webui_Interface = Interfacer(config['webui_url'])
sock = None #aught to just rewrite this all to be a class

def main():
    global active_image, active_command, commands_left_in_batch, command_queue, output_list, Webui_Interface, config, sock

    sock = create_socket(config)
    
    while True:
        try:
            if sock is None:
                print('socket disconnected, retrying connection...')
                sock = create_socket(config)
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
                update_generate_text('!generate stablediffusion v1.5', config) # should make sure this isnt repeatedly called if it's already set to this
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

                # if there are more commands in the queue, then reduce the number of images in batch so as to speed things up
                if len(command_queue) > 0:
                    commands_left_in_batch = 0

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
                update_generate_text(u, config)


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