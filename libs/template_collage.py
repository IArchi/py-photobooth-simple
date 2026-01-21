import os
import cv2
import json
import tempfile
import numpy as np
from kivy.logger import Logger

from libs.file_utils import FileUtils


class TemplateCollage:
    """
    Collage class that loads configuration from JSON template files.
    """
    
    def __init__(self, template_path):
        """
        Initialize the collage from a JSON template file.
        
        Args:
            template_path: Path to the JSON template file
        """
        Logger.info(f'TemplateCollage: __init__({template_path})')
        
        self._template_path = template_path
        self._module_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Load template
        with open(template_path, 'r') as f:
            self._template = json.load(f)
        
        # Cache template properties
        self._name = self._template.get('name', 'Unnamed Template')
        self._description = self._template.get('description', '')
        self._page_width = self._template['page']['width']
        self._page_height = self._template['page']['height']
        self._photos = self._template['photos']
        self._print_params = self._template.get('print_params', {})
        self._margin_percent = self._template.get('margin_percent', 5)
        self._duplicate_horizontal = self._template.get('duplicate_horizontal', False)
        
        # Resolve paths relative to module directory
        self._background = self._template.get('background')
        if self._background:
            self._background = os.path.join(self._module_dir, self._background)
            
        self._foreground = self._template.get('foreground')
        if self._foreground:
            self._foreground = os.path.join(self._module_dir, self._foreground)
        
        # Load dummy images for preview
        self._dummies = [
            os.path.join(self._module_dir, '../assets/icons/dummy0.png'),
            os.path.join(self._module_dir, '../assets/icons/dummy1.png'),
            os.path.join(self._module_dir, '../assets/icons/dummy2.png'),
            os.path.join(self._module_dir, '../assets/icons/dummy3.png')
        ]
    
    def get_name(self):
        """Return the template name."""
        return self._name
    
    def get_description(self):
        """Return the template description."""
        return self._description
    
    def get_photos_required(self):
        """Return the number of photos required."""
        return len(self._photos)
    
    def get_aspect_ratio(self):
        """
        Return the aspect ratio (width/height) of the first photo slot.
        Used for camera preview and capture.
        Returns 1.0 for square, >1.0 for landscape, <1.0 for portrait.
        """
        if len(self._photos) > 0:
            width = self._photos[0]['width']
            height = self._photos[0]['height']
            return width / height
        return 1.0
    
    def get_print_params(self):
        """Return the print parameters."""
        return self._print_params
    
    def get_preview(self):
        """
        Generate a preview image using dummy photos.
        
        Returns:
            Path to the generated preview image
        """
        # Use dummy images for preview
        num_photos = self.get_photos_required()
        image_paths = [self._dummies[min(i, len(self._dummies) - 1)] for i in range(num_photos)]
        
        # Generate collage
        collage = self.assemble(image_paths)
        collage = FileUtils.resize(collage)
        
        # Dump to temp file
        _, tmp_output = tempfile.mkstemp(suffix='.jpg')
        cv2.imwrite(tmp_output, collage)
        return tmp_output
    
    def assemble(self, image_paths, output_path=None, for_print=False):
        """
        Assemble photos into a collage based on the template.
        Simple approach: create canvas, apply background, paste photos (clipping if needed), apply foreground.
        
        Args:
            image_paths: List of paths to input images
            output_path: Optional path to save the output
            for_print: If True, apply duplication for printing. If False (default), don't duplicate.
            
        Returns:
            The assembled collage as a numpy array
        """
        Logger.info(f'TemplateCollage: assemble({len(image_paths)} images)')
        
        # Step 1: Create canvas with white background
        canvas = np.full((self._page_height, self._page_width, 3), 255, dtype=np.uint8)
        
        # Step 2: Apply background image if specified (resize to exact canvas size)
        if self._background and os.path.exists(self._background):
            bg = cv2.imread(self._background, cv2.IMREAD_COLOR)
            if bg is not None:
                bg = cv2.resize(bg, (self._page_width, self._page_height), interpolation=cv2.INTER_AREA)
                canvas = bg
        
        # Step 3: Place each photo according to template (clip if needed)
        for i, photo_spec in enumerate(self._photos):
            if i >= len(image_paths):
                break
                
            # Load image
            img = cv2.imread(image_paths[i], cv2.IMREAD_COLOR)
            if img is None:
                Logger.warning(f'Could not load image: {image_paths[i]}')
                continue
            
            # Get photo specifications
            x = photo_spec['x']
            y = photo_spec['y']
            width = photo_spec['width']
            height = photo_spec['height']
            
            # Resize and crop image to target dimensions
            img_resized = FileUtils.resize_and_crop(img, (height, width))
            
            # Calculate actual dimensions we can paste (clip to canvas boundaries)
            paste_height = min(height, self._page_height - y, img_resized.shape[0])
            paste_width = min(width, self._page_width - x, img_resized.shape[1])
            
            # Only paste if there's space
            if paste_height > 0 and paste_width > 0:
                canvas[y:y + paste_height, x:x + paste_width] = img_resized[0:paste_height, 0:paste_width]
        
        # Step 4: Apply foreground overlay if specified (resize to exact canvas size)
        if self._foreground and os.path.exists(self._foreground):
            overlay = cv2.imread(self._foreground, cv2.IMREAD_UNCHANGED)
            if overlay is not None:
                overlay = cv2.resize(overlay, (self._page_width, self._page_height), interpolation=cv2.INTER_AREA)
                canvas = self._apply_overlay(canvas, overlay)
        
        # Step 5: Duplicate horizontally if specified and printing
        # (Only duplicate for printing, not for preview/display)
        if self._duplicate_horizontal and for_print:
            canvas = cv2.hconcat([canvas, canvas])
        
        # Step 6: Save output
        if output_path:
            cv2.imwrite(output_path, canvas)
            
            # Create small preview
            small = FileUtils.resize(canvas)
            cv2.imwrite(FileUtils.get_small_path(output_path), small)
        
        return canvas
    
    def _apply_overlay(self, image, overlay):
        """
        Apply an overlay image on top of the base image.
        
        Args:
            image: Base image (numpy array)
            overlay: Overlay image (numpy array, already resized to match base image)
            
        Returns:
            Image with overlay applied
        """
        if overlay.shape[2] == 4:  # If overlay has alpha channel
            alpha_overlay = overlay[:, :, 3] / 255.0
            alpha_image = 1.0 - alpha_overlay
            
            for c in range(0, 3):
                image[:, :, c] = (alpha_overlay * overlay[:, :, c] + alpha_image * image[:, :, c])
        else:
            # If no alpha channel, just blend with some transparency (optional)
            alpha_overlay = 0.5  # This can be adjusted
            image = cv2.addWeighted(image, 1 - alpha_overlay, overlay, alpha_overlay, 0)
        
        return image


def load_templates(templates_dir='templates'):
    """
    Load all template files from a directory.
    
    Args:
        templates_dir: Directory containing template JSON files
        
    Returns:
        List of TemplateCollage instances
    """
    templates = []
    module_dir = os.path.dirname(os.path.abspath(__file__))
    templates_path = os.path.join(module_dir, '..', templates_dir)
    
    if not os.path.exists(templates_path):
        Logger.warning(f'Templates directory not found: {templates_path}')
        return templates
    
    # Load all JSON files
    for filename in sorted(os.listdir(templates_path)):
        if filename.endswith('.json'):
            template_path = os.path.join(templates_path, filename)
            try:
                template = TemplateCollage(template_path)
                templates.append(template)
                Logger.info(f'Loaded template: {template.get_name()} from {filename}')
            except Exception as e:
                Logger.error(f'Error loading template {filename}: {e}')
    
    return templates
