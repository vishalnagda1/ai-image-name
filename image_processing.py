import os
import pandas as pd
from PIL import Image
from pprint import pprint
from tqdm import tqdm
import shutil
from .main import ai_image_name

def get_image_dimensions(image_path):
    """Get dimensions of an image"""
    with Image.open(image_path) as img:
        return img.size

def resize_and_rename_image(image_path, target_size, new_name=None):
    """Resize image to target dimensions, save as JPG, and optionally rename"""
    try:
        with Image.open(image_path) as img:
            # Convert to RGB if image is in RGBA mode
            if img.mode == 'RGBA':
                img = img.convert('RGB')
                
            # Resize image
            resized_img = img.resize(target_size, Image.Resampling.LANCZOS)
            
            # Determine the new path
            if new_name:
                # Use the provided new name
                directory = os.path.dirname(image_path)
                new_path = os.path.join(directory, f"{new_name}.jpg")
            else:
                # Use original name with .jpg extension
                new_path = os.path.splitext(image_path)[0] + '.jpg'
            
            # Save the resized image in JPG format
            resized_img.save(new_path, 'JPEG', quality=95, optimize=True)
            
            # Remove the original file if it's different from the new jpg
            if image_path != new_path:
                os.remove(image_path)
            
    except Exception as e:
        print(f"Error processing {image_path}: {str(e)}")

def load_image_mapping(csv_path):
    """Load and process the CSV file containing image mappings"""
    try:
        df = pd.read_csv(csv_path)
        # Create a dictionary with folder ID as key and image names as values
        mapping = {}
        for _, row in df.iterrows():
            mapping[str(row['ID'])] = {
                'banner': row['Banner Image'],
                'inner1': row['Inner image 1'],
                'inner2': row['Inner image 2']
            }
        return mapping
    except Exception as e:
        print(f"Error loading CSV file: {str(e)}")
        return None

def process_folder(folder_path, csv_path):
    """Process all images in a folder and its subfolders using CSV mapping"""
    # Load image mapping from CSV
    image_mapping = load_image_mapping(csv_path)
    if not image_mapping:
        print("Failed to load image mapping. Exiting...")
        return

    # First, collect all valid folders with exactly 3 images
    valid_folders = []
    for root, dirs, files in os.walk(folder_path):
        # Extract folder ID from the folder name
        folder_name = os.path.basename(root)
        folder_id = folder_name.split('.')[0].strip()
        
        image_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp'))]
        if len(image_files) == 3:
            valid_folders.append((root, image_files, folder_id))
        else:
            pprint(f"Skipping folder {root}: Contains {len(image_files)} images instead of 3")

    # Process the valid folders with progress bar
    for root, image_files, folder_id in tqdm(valid_folders, desc="Processing folders"):
        if folder_id not in image_mapping:
            print(f"No mapping found for folder {folder_id}. Skipping...")
            continue

        # Get dimensions of all images
        image_dimensions = {}
        for img_file in image_files:
            img_path = os.path.join(root, img_file)
            dimensions = get_image_dimensions(img_path)
            image_dimensions[img_file] = dimensions
        
        # Sort images by total pixel count (width * height)
        sorted_images = sorted(
            image_dimensions.items(),
            key=lambda x: x[1][0] * x[1][1],
            reverse=True
        )
        
        # Get new names from mapping
        new_names = image_mapping[folder_id]
        
        # Resize and rename the largest image to 1200x502 (Banner)
        largest_image = os.path.join(root, sorted_images[0][0])
        resize_and_rename_image(largest_image, (1200, 502), new_names['banner'])
        
        # Resize and rename the remaining two images to 720x480
        resize_and_rename_image(
            os.path.join(root, sorted_images[1][0]), 
            (720, 480), 
            new_names['inner1']
        )
        resize_and_rename_image(
            os.path.join(root, sorted_images[2][0]), 
            (720, 480), 
            new_names['inner2']
        )

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
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff')
    
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
    # Get the folder and CSV paths
    folder_path = os.path.abspath(os.path.expanduser(os.path.join("~/", "Downloads/IT Support")))
    csv_path = os.path.abspath(os.path.expanduser(os.path.join("~/", "Downloads/names.csv")))

    pprint(f"Folder path: {folder_path}")
    pprint(f"CSV path: {csv_path}")
    
    # Check if the paths exist
    if not os.path.exists(folder_path):
        print("Error: The specified folder does not exist.")
        return
    
    if not os.path.exists(csv_path):
        print("Error: The specified CSV file does not exist.")
        return
    
    pprint(f"Processing folders in {folder_path}...")
    process_folder(folder_path, csv_path)
    pprint("Image processing completed!")

    # Original folder ka base name nikalna
    base_folder_name = os.path.basename(folder_path)

    # Naya folder name banana by appending "- images"
    new_folder_name = f"{base_folder_name} - images"

    # Naye folder ka complete path banana
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
