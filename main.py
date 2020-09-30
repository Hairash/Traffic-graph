import base64
import hashlib
import json
import os
from io import BytesIO

from PIL import Image, ImageDraw

# consts
# dict: ball - link color
LOAD_COLORS = {
    -1: 'grey',  # no data
    2: 'green',
    6: 'yellow',
    9: 'red',
    10: (128, 0, 0)
}
LINK_WIDTH = 3
# add margins (relative to image's size)
SCALE_MODIFIER = 0.1


# return the most left, right, top and bottom points
def find_bounds(nodes):
    x_list = []
    y_list = []
    for node in nodes:
        x = node['geometry']['center'][0]
        y = node['geometry']['center'][1]
        x_list.append(x)
        y_list.append(y)
    return {
        'min_x': min(x_list),
        'max_x': max(x_list),
        'min_y': min(y_list),
        'max_y': max(y_list)
    }


# scale and shift point
def scale_point(point, scale, shift_x, shift_y, image_indent):
    return (point[0] + shift_x) * scale + image_indent, (point[1] + shift_y) * scale + image_indent


# return color of link by id
def select_load_color(id, loads):
    if id not in loads:
        cur_ball = -1
    else:
        cur_ball = loads[id]

    for ball in sorted(LOAD_COLORS.keys()):
        if cur_ball <= ball:
            return LOAD_COLORS[ball]
    raise ValueError('Unknown ball')


# create new traffic image and return as base64 string
def create_image():
    # create image
    image_params = data['image']
    img = Image.new('RGB', (image_params['width'], image_params['height']), 'black')
    draw = ImageDraw.Draw(img)

    # calculate scale
    nodes = data['graph']['nodes']
    bounds = find_bounds(nodes)
    scale = min(image_params['width'] / (bounds['max_x'] - bounds['min_x']),
                image_params['height'] / (bounds['max_y'] - bounds['min_y']))
    scale *= (1 - 2 * SCALE_MODIFIER)
    image_indent = min(image_params['width'], image_params['height']) * SCALE_MODIFIER
    shift_x = -bounds['min_x']
    shift_y = -bounds['min_y']
    # scaling formula: ((x + shift_x) * scale, (y + shift_y) * scale)
    scale_params = {
        'scale': scale,
        'shift_x': shift_x,
        'shift_y': shift_y,
        'image_indent': image_indent
    }

    # draw nodes
    for node in nodes:
        if node['geometry']['type'] == 'Circle':
            center = node['geometry']['center']
            radius = node['geometry']['radius']
            draw_points = [
                [center[0] - radius, center[1] - radius],
                [center[0] + radius, center[1] + radius]
            ]
            draw_points = [scale_point(point, **scale_params) for point in draw_points]
            draw.ellipse(draw_points, fill='white')
        else:
            raise ValueError('Unknown node type')

    # create loads dict
    loads = {}
    for load in data['loads']:
        loads[load['link_id']] = load['load']

    # draw links
    links = data['graph']['links']
    for link in links:
        if link['geometry']['type'] == 'LineString':
            points = link['geometry']['coordinates']
            points = [scale_point(point, **scale_params) for point in points]
            if len(points) < 2:
                raise ValueError('Not enough coordinates to create link')
            color = select_load_color(link['id'], loads)
            draw.line(points, fill=color, width=LINK_WIDTH)
        else:
            raise ValueError('Unknown link type')

    # save image to the disk (if needed)
    # img.save(f'traffic.{image_params["format"]}')

    # create base64 string
    buffered = BytesIO()
    if image_params["format"].lower() == 'jpg':
        image_params["format"] = 'jpeg'
    img.save(buffered, format=image_params["format"])
    img_str = str(base64.b64encode(buffered.getvalue()))[2: -1]
    return {'image': img_str}


# program start
# read data from file 'data.json'
with open('data.json') as f:
    data = json.load(f)

# check if file in cache
if not os.path.exists('cache.json'):
    cache = {}
else:
    with open('cache.json') as f:
        cache = json.load(f)

data_str = json.dumps(data).encode()
data_hash = hashlib.sha256(data_str).hexdigest()
if data_hash in cache:
    print('result from cache')
    result = cache[data_hash]
else:
    print('new result')
    result = create_image()

# save image as base64 string to file 'result.json'
with open('result.json', 'w') as f:
    json.dump(result, f)

# save cache
cache.update({data_hash: result})
with open('cache.json', 'w') as f:
    json.dump(cache, f)
