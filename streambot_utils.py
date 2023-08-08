import os, json, time
import socket
import numpy as np
import base64
import io
from PIL import Image, ExifTags




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
        "n_imgs": 4,
        "sampler": "Euler a",
        "steps": 20
        }
    }

def load_config():
    if not os.path.isfile(os.path.join(os.getcwd(), 'config.json')): # if no config is found, create default one and save it
        with open(os.path.join(os.getcwd(), 'config.json'), 'w') as f:
            json.dump(default_config, f, indent=4)
        
        # exit program
        print('config.json not found, default config created, please fill in the details and restart the script')
        time.sleep(5)
        exit()

    # load config
    with open(os.path.join(os.getcwd(), 'config.json')) as f:
        config = json.load(f)

        if config == default_config:
            print('config.json has not been configured, or is incorrectly configured, please fill in the details and restart the script')
            time.sleep(30)
            exit()
    return config

def reload_config():
    with open(os.path.join(os.getcwd(), 'config.json')) as f:
        config = json.load(f)
    return config

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


def make_check_folders(config):
    active_image = None

    if not os.path.isdir(os.path.join(os.getcwd(),config['output_folder_name'])):
        os.mkdir(os.path.join(os.getcwd(),config['output_folder_name']))
    if not os.path.isdir(os.path.join(os.getcwd(),config['output_folder_name'],'stream')):
        os.mkdir(os.path.join(os.getcwd(),config['output_folder_name'],'stream'))

    if not os.path.isfile(os.path.join(os.getcwd(),config['output_folder_name'],'stream/stream.jpg')):
        # save blank image to stream.jpg
        img = Image.new('RGB', size=(512, 512), color=(0, 0, 0))
        exif = img.getexif() # should use ExifTags to search for UserComments so its clearer
        exif[0x9286] = json.dumps({}).encode('utf-8')
        img.save(os.path.join(os.getcwd(),config['output_folder_name'],'stream/stream.jpg'), quality=95, exif=exif)
    else:
        active_image = load_image(os.path.join(os.getcwd(),config['output_folder_name'],'stream/stream.jpg'))

    # check if generate.txt exists, if not create it
    if not os.path.isfile(os.path.join(os.getcwd(),config['output_folder_name'],'stream/generate.txt')):
        with open(os.path.join(os.getcwd(),config['output_folder_name'],'stream/generate.txt'), 'w') as f:
            f.write('!generate stablediffusion v1.5')

    # check if user.txt exists, if not create it
    if not os.path.isfile(os.path.join(os.getcwd(),config['output_folder_name'],'stream/user.txt')):
        with open(os.path.join(os.getcwd(),config['output_folder_name'],'stream/user.txt'), 'w') as f:
            f.write('')

    return active_image

    
def create_socket(config):
    print('connecting to twitch...', end='')
    try:
        sock = socket.socket()
        sock.connect((config['server'], config['port']))
        sock.settimeout(1.0)

        sock.send(f"PASS {config['token']}\n".encode('utf-8'))
        sock.send(f"NICK {config['nickname']}\n".encode('utf-8'))
        sock.send(f"JOIN {config['channel']}\n".encode('utf-8'))
    except:
        print('failed')
        return None
    print('success')
    return sock

def close_socket(sock, msg='error'):
    sock.close()
    print(f'{msg}; socket has been closed')
    return None



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


def image_grid(imgs, rows, cols):
    # assert len(imgs) == rows * cols

    w, h = imgs[0].size
    grid = Image.new('RGB', size=(cols * w, rows * h))

    for i, img in enumerate(imgs):
        grid.paste(img, box=(i % cols * w, i // cols * h))
    return grid

def check_outputs(webui, command):
    return webui.get_outputs(command)


def update_generate_text(txt, config):
    with open(os.path.join(os.getcwd(),config['output_folder_name'],'stream/generate.txt'), 'w') as f:
        f.write(txt)


# process images from webui by converting from base64 to PIL image
def process_images(images):
    processed_images = []
    for image in images:
        processed_images.append(Image.open(io.BytesIO(base64.b64decode(image))))
    return processed_images