import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Global variables
bg_color = '#e5e5e5'
text_color = '#26495c'
icons = ['\u4a1f', '\u4a8b', '\u4a90', '\u4320']

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def create_image_with_text(text, font_path, font_size, bg_color='#000000', text_color='#FFFFFF', image_size=(1920, 1080)):
    bg_color = hex_to_rgb(bg_color)
    text_color = hex_to_rgb(text_color)

    # Create an empty image
    image = np.zeros((image_size[1], image_size[0], 3), dtype=np.uint8)
    image[:] = bg_color
    pil_image = Image.fromarray(image)
    draw = ImageDraw.Draw(pil_image)

    # Draw text in center
    font = ImageFont.truetype(font_path, font_size)
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    text_x = (image_size[0] - text_width) // 2
    text_y = (image_size[1] - text_height) // 2
    draw.text((text_x, text_y), text, font=font, fill=text_color)

    image = np.array(pil_image)
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    return image

for idx, icon in enumerate(icons):
    image = create_image_with_text(icon, '../assets/fonts/hugeicons.ttf', 1000, bg_color, text_color)
    cv2.imwrite(f'dummy{idx}.png', image)