import os

from PIL import Image


class ImageProcessor:
    """A class to handle image processing operations like resizing and format conversion"""

    def __init__(self, default_quality=95, default_format="JPEG"):
        """
        Initialize ImageProcessor with default settings

        Args:
            default_quality (int): Default JPEG quality (1-100)
            default_format (str): Default output format
        """
        self.default_quality = default_quality
        self.default_format = default_format

    def get_image_dimensions(self, image_path):
        """
        Get dimensions of an image

        Args:
            image_path (str): Path to the image file

        Returns:
            tuple: (width, height) of the image
        """
        with Image.open(image_path) as img:
            return img.size

    def resize_and_rename_image(
        self, image_path, target_size, new_name=None, quality=None, remove_original=True
    ):
        """
        Resize image to target dimensions, save as JPG, and optionally rename

        Args:
            image_path (str): Path to the original image
            target_size (tuple): Desired (width, height)
            new_name (str, optional): New filename without extension
            quality (int, optional): JPEG quality (1-100)
            remove_original (bool): Whether to remove the original file

        Returns:
            str: Path to the processed image
        """
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if image is in RGBA mode
                if img.mode == "RGBA":
                    img = img.convert("RGB")

                # Resize image
                resized_img = img.resize(target_size, Image.Resampling.LANCZOS)

                # Determine the new path
                if new_name:
                    directory = os.path.dirname(image_path)
                    new_path = os.path.join(directory, f"{new_name}.jpg")
                else:
                    new_path = os.path.splitext(image_path)[0] + ".jpg"

                # Use provided quality or fall back to default
                final_quality = quality if quality is not None else self.default_quality

                # Save the resized image
                resized_img.save(
                    new_path, self.default_format, quality=final_quality, optimize=True
                )

                # Remove the original file if requested and different from new path
                if remove_original and image_path != new_path:
                    os.remove(image_path)

                return new_path

        except Exception as e:
            print(f"Error processing {image_path}: {str(e)}")
            return None

    def process_directory(self, directory_path, target_size, quality=None):
        """
        Process all images in a directory

        Args:
            directory_path (str): Path to directory containing images
            target_size (tuple): Desired (width, height)
            quality (int, optional): JPEG quality (1-100)

        Returns:
            list: Paths to all processed images
        """
        processed_files = []

        for filename in os.listdir(directory_path):
            if filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp")):
                image_path = os.path.join(directory_path, filename)
                processed_path = self.resize_and_rename_image(
                    image_path, target_size, quality=quality
                )
                if processed_path:
                    processed_files.append(processed_path)

        return processed_files


# Usage example:
if __name__ == "__main__":
    # Create an instance with custom defaults
    processor = ImageProcessor(default_quality=90)

    # Process a single image
    image_path = "path/to/image.png"
    dimensions = processor.get_image_dimensions(image_path)
    print(f"Original dimensions: {dimensions}")

    # Resize to 800x600
    new_path = processor.resize_and_rename_image(
        image_path, target_size=(800, 600), new_name="resized_image"
    )

    # Process all images in a directory
    directory_path = "path/to/images"
    processed_files = processor.process_directory(
        directory_path, target_size=(1024, 768), quality=85
    )
    print(f"Processed {len(processed_files)} images")
