import os
from pprint import pprint

from ollama import Client
from PIL import Image
from tqdm import tqdm

# from .main import ai_image_name


client = Client(
    host="http://0.0.0.0:11435",
)


def ai_image_name(image_path):
    response = client.chat(
        model="llava:7b",
        messages=[
            {
                "role": "user",
                "content": "give a valid name to this image, max length of name should be 30 characters long." \
                            "do not include quotes around the name. The name should be separated by underscores." \
                                "for example, if the image is a picture of a cat, the name should be cat_picture",
                "images": [image_path],
            },
        ],
    )
    return response["message"]["content"]


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
            new_name = ai_image_name(image_path)

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


def main():
    # Get the folder path from user input
    # folder_path = input("Enter the root folder path: ")
    folder_path = os.path.abspath(
        os.path.expanduser(
            os.path.join("~/", "Downloads/IT Support-20250215T130156Z-001/IT Support")
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


if __name__ == "__main__":
    main()
