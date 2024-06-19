import cv2
import tempfile
import numpy as np

def process_image(image_path, target_size=(2480, 3840), margin_percent=5, overlay=None):
    # Read the original image
    img = cv2.imread(image_path, cv2.IMREAD_COLOR)

    # Calculate margin size
    margin_height = int(target_size[0] * (margin_percent / 100))
    margin_width = int(target_size[1] * (margin_percent / 100))

    # Calculate new size considering margins
    new_height = target_size[0] - 2 * margin_height
    new_width = target_size[1] - 2 * margin_width

    # Resize the image
    img_resized = resize_and_crop(img, (new_height, new_width))

    # Create a new image with the target size and fill it with white
    new_img = np.full((target_size[0], target_size[1], 3), 255, dtype=np.uint8)

    # Paste the resized image onto the new image with margins
    new_img[margin_height:margin_height + new_height, margin_width:margin_width + new_width] = img_resized

    # Add overlay
    if overlay: new_img = apply_overlay(new_img, overlay)

    return new_img

def resize_and_crop(image, target_size):
    # Calculate the aspect ratios
    aspect_ratio_target = target_size[1] / target_size[0]
    aspect_ratio_image = image.shape[1] / image.shape[0]

    if aspect_ratio_image > aspect_ratio_target:
        # Image is wider than the target: fit height, crop width
        new_height = target_size[0]
        new_width = int(new_height * aspect_ratio_image)
    else:
        # Image is taller than the target: fit width, crop height
        new_width = target_size[1]
        new_height = int(new_width / aspect_ratio_image)

    # Resize image to the new size
    resized_image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)

    # Center crop to the target size
    crop_x = (new_width - target_size[1]) // 2
    crop_y = (new_height - target_size[0]) // 2

    cropped_image = resized_image[crop_y:crop_y + target_size[0], crop_x:crop_x + target_size[1]]

    return cropped_image

def apply_overlay(image, overlay_path):
    # Read the overlay image
    overlay = cv2.imread(overlay_path, cv2.IMREAD_UNCHANGED)

    # Ensure the overlay is the same size as the target image
    overlay = cv2.resize(overlay, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_AREA)

    if overlay.shape[2] == 4:  # If overlay has alpha channel
        alpha_overlay = overlay[:, :, 3] / 255.0
        alpha_image = 1.0 - alpha_overlay

        for c in range(0, 3):
            image[:, :, c] = (alpha_overlay * overlay[:, :, c] +
                              alpha_image * image[:, :, c])
    else:
        # If no alpha channel, just blend with some transparency (optional)
        alpha_overlay = 0.5  # This can be adjusted
        image = cv2.addWeighted(image, 1 - alpha_overlay, overlay, alpha_overlay, 0)

    return image

# Resize image, add margins and apply overlay
resized_img = process_image('../doc/dummy.png', overlay='../overlay.png')

# Display the final image
cv2.imshow('test', resized_img)
cv2.waitKey(0)
