import cv2
import numpy as np

def resize_and_crop(image, target_size):
    # Calculate aspect ratio
    aspect_ratio_image = image.shape[1] / image.shape[0]

    if target_size[0] == None:
        # Calculate the new height based on the provided target width and original aspect ratio
        new_width = target_size[1]
        new_height = int(new_width / aspect_ratio_image)

        # Resize the image to the new dimensions
        return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
    elif target_size[1] == None:
        # Calculate the new width based on the provided target height and original aspect ratio
        new_height = target_size[0]
        new_width = int(new_height * aspect_ratio_image)

        # Resize the image to the new dimensions
        return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
    else:
        aspect_ratio_target = target_size[1] / target_size[0]
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

        return resized_image[crop_y:crop_y + target_size[0], crop_x:crop_x + target_size[1]]

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

def process_image(image_paths, target_size=(3840, 1240), margin_percent=5, overlay=None, square=False):
    # Calculate margin size
    margin_height = int(target_size[0] * (margin_percent / 100))
    margin_width = int(target_size[1] * (margin_percent / 100))
    margin_width = margin_height = min(margin_height, margin_width)

    # Calculate new size considering margins
    new_height = target_size[0] - 2 * margin_height
    new_width = target_size[1] - 2 * margin_width

    # Load images
    images = [cv2.imread(img_path) for img_path in image_paths]

    # Resize images to square
    if square:
        images = [resize_and_crop(img, (new_width, new_width)) for img in images]
    else:
        # TODO : Does not work. Image fill the full height. I need to keep aspect.
        images = [resize_and_crop(img, (None, new_width)) for img in images]
    print(images[0].shape)

    # Create a new image with the target size and fill it with white
    new_img = np.full((target_size[0], target_size[1], 3), 255, dtype=np.uint8)

    # Calculate vertical position to align images
    total_height = sum(img.shape[0] for img in images)
    current_y = margin_height
    for img in images:
        height, width = img.shape[:2]
        if current_y + height <= target_size[0]:  # Check if there's enough space vertically
            new_img[current_y:current_y + height, margin_width:margin_width + width] = img
            current_y += height + margin_height
        else:
            break

    # Add overlay
    if overlay: new_img = apply_overlay(new_img, overlay)

    return new_img

# Main program to process the images
if __name__ == "__main__":
    image_paths = ['../doc/dummy.png', '../doc/dummy.png', '../doc/dummy.png', '../doc/dummy.png', '../doc/dummy.png', '../doc/dummy.png']
    resized_img = process_image(image_paths, overlay='../overlay.png', square=True)

    # Display the final image
    cv2.imshow('test', resized_img)
    cv2.waitKey(0)
