import os
import shutil
from pprint import pprint

from PIL import Image
from tqdm import tqdm

from ai_image_name import ImageNameGenerator

ing = ImageNameGenerator(host="192.168.1.50:11435")


def get_image_dimensions(image_path):
    """Get dimensions of an image"""
    with Image.open(image_path) as img:
        return img.size


def resize_image(image_path, target_size):
    """Resize image to target dimensions and save as JPG"""
    try:
        with Image.open(image_path) as img:
            # Convert to RGB if image is in RGBA mode
            if img.mode == "RGBA":
                img = img.convert("RGB")

            # Resize image
            resized_img = img.resize(target_size, Image.Resampling.LANCZOS)

            # Get new AI-generated filename
            new_name = ing.generate_name(image_path)

            # Create full path for new file with .jpg extension
            new_path = os.path.join(os.path.dirname(image_path), new_name + ".jpg")

            # Save the resized image in JPG format
            resized_img.save(new_path, "JPEG", quality=95, optimize=True)

            # Remove the original file if it's different from the new jpg
            if image_path != new_path:
                os.remove(image_path)

            # print(f"Successfully resized {image_path} to {target_size}")

    except Exception as e:
        print(f"Error processing {image_path}: {str(e)}")


def process_folder(folder_path):
    """Process all images in a folder and its subfolders"""
    # First, collect all valid folders with exactly 3 images
    valid_folders = []
    for root, dirs, files in os.walk(folder_path):
        image_files = [
            f
            for f in files
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp"))
        ]
        if len(image_files) == 3:
            valid_folders.append((root, image_files))
        else:
            pprint(
                f"Skipping folder {root}: Contains {len(image_files)} images instead of 3"
            )

    # Process the valid folders with progress bar
    for root, image_files in tqdm(valid_folders, desc="Processing folders"):
        # Get dimensions of all images
        image_dimensions = {}
        for img_file in image_files:
            img_path = os.path.join(root, img_file)
            dimensions = get_image_dimensions(img_path)
            image_dimensions[img_file] = dimensions

        # Sort images by total pixel count (width * height)
        sorted_images = sorted(
            image_dimensions.items(), key=lambda x: x[1][0] * x[1][1], reverse=True
        )

        # Resize the largest image to 1200x502
        largest_image = os.path.join(root, sorted_images[0][0])
        resize_image(largest_image, (1200, 502))

        # Resize the remaining two images to 720x480
        for img_info in sorted_images[1:]:
            img_path = os.path.join(root, img_info[0])
            resize_image(img_path, (720, 480))


def copy_images_to_single_folder(source_path, destination_folder):
    """
    Copy all images from nested folders to a single destination folder.

    Args:
        source_path (str): Path to the root folder containing nested folders with images
        destination_folder (str): Name of the new folder where images will be moved
    """
    # Create destination folder if it doesn't exist
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)

    # List of common image extensions
    image_extensions = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff")

    # Walk through all directories and subdirectories
    for root, dirs, files in os.walk(source_path):
        for file in files:
            # Check if the file is an image
            if file.lower().endswith(image_extensions):
                # Get the full path of the source file
                source_file = os.path.join(root, file)

                # Generate a unique filename to avoid overwrites
                base_name = os.path.basename(file)
                name, ext = os.path.splitext(base_name)
                counter = 1
                new_name = base_name

                # If file with same name exists, add number to filename
                while os.path.exists(os.path.join(destination_folder, new_name)):
                    new_name = f"{name}_{counter}{ext}"
                    counter += 1

                # Copy the file to destination
                destination_file = os.path.join(destination_folder, new_name)
                shutil.copy(source_file, destination_file)
                print(f"Copied: {source_file} -> {destination_file}")


def main():
    # Get the folder path from user input
    folder_path = input("Enter the folder path: ")
    folder_path = os.path.abspath(
        os.path.expanduser(
            os.path.join("~/", folder_path)
        )
    )

    pprint(f"folder path: {folder_path}")

    # Check if the folder exists
    if not os.path.exists(folder_path):
        print("Error: The specified folder does not exist.")
        return

    pprint(f"Processing folders in {folder_path}...")
    process_folder(folder_path)
    pprint("Image processing completed!")

    base_folder_name = os.path.basename(folder_path)
    new_folder_name = f"{base_folder_name} - images"

    destination_folder = os.path.dirname(folder_path)
    destination_folder = os.path.join(destination_folder, new_folder_name)

    # Check if folder exists
    if os.path.exists(destination_folder):
        for item in os.listdir(destination_folder):
            item_path = os.path.join(destination_folder, item)
            if os.path.isfile(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
    else:
        os.makedirs(destination_folder, exist_ok=True)

    copy_images_to_single_folder(folder_path, destination_folder)


if __name__ == "__main__":
    main()
