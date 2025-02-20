import os
from pathlib import Path

from ai_image_name import ImageNameGenerator
from utils.image import ImageProcessor

# As it is a singleton class, so creating object here
ing = ImageNameGenerator(host="https://aiq-ollama.visions.team", model="llava:34b")

image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}


def identify_banner_by_dimensions(processor, image_paths):
    """
    Identify the banner image in a folder based on image dimensions

    Args:
        processor (ImageProcessor): Instance of ImageProcessor
        image_paths (list): List of Path objects for images

    Returns:
        Path: Path object of the identified banner image
    """
    max_area = 0
    banner_image = None

    for img_path in image_paths:
        try:
            dimensions = processor.get_image_dimensions(str(img_path))
            area = dimensions[0] * dimensions[1]
            if area > max_area:
                max_area = area
                banner_image = img_path
        except Exception as e:
            print(f"Warning: Could not check dimensions of {img_path.name}: {e}")
            continue

    return banner_image


def process_images(root_folder, banner_name=None):
    """
    Process and rename images in all subfolders of the given root folder.

    Args:
        root_folder (str): Path to the root folder containing subfolders with images
        banner_name (str, optional): Name pattern to identify banner images

    Returns:
        tuple: (success_count, error_count, list of errors)
    """
    try:
        # Validate root folder path
        if not os.path.exists(root_folder):
            raise ValueError(f"The specified path does not exist: {root_folder}")
        if not os.path.isdir(root_folder):
            raise ValueError(f"The specified path is not a directory: {root_folder}")

        # Initialize processors
        processor = ImageProcessor(default_quality=95)

        # Statistics tracking
        success_count = 0
        error_count = 0
        errors = []

        # Process each subfolder
        for subfolder_path in Path(root_folder).iterdir():
            if not subfolder_path.is_dir():
                continue

            print(f"\nProcessing folder: {subfolder_path}")

            # Collect all valid image paths in the subfolder
            image_paths = [
                p
                for p in subfolder_path.glob("*")
                if p.suffix.lower() in image_extensions
            ]

            if not image_paths:
                continue

            # Identify banner image
            banner_image = None
            if banner_name:
                # Find banner by name pattern
                banner_candidates = [
                    img
                    for img in image_paths
                    if banner_name.lower() in img.name.lower()
                ]
                if banner_candidates:
                    banner_image = banner_candidates[0]

            if not banner_image:
                # If no banner found by name (or no name provided), use largest image
                banner_image = identify_banner_by_dimensions(processor, image_paths)
                if banner_image:
                    print(f"Identified banner image by dimensions: {banner_image.name}")

            # Process each image in the subfolder
            for image_path in image_paths:
                try:
                    # Determine if this is the banner image
                    is_banner = image_path == banner_image
                    target_size = (1200, 502) if is_banner else (720, 480)

                    print(
                        f"Processing: {image_path.name} {'(banner)' if is_banner else ''}"
                    )

                    # First resize the image
                    temp_path = processor.resize_and_rename_image(
                        str(image_path),
                        target_size=target_size,
                        remove_original=False,  # Don't remove yet, we'll rename it
                    )

                    if not temp_path:
                        raise Exception("Image processing failed")

                    # Generate AI-based name
                    try:
                        new_name = ing.generate_name(image_path=temp_path)
                        if not new_name:
                            raise ValueError("AI name generation returned empty name")

                        # Clean the generated name
                        new_name = "".join(
                            c for c in new_name if c.isalnum() or c in "- "
                        ).strip()
                        new_name = new_name.replace(" ", "-")

                        # Add banner indicator to filename if it's a banner
                        if is_banner:
                            new_name = f"banner-{new_name}"

                        # Create final path with new name
                        final_path = image_path.parent / f"{new_name}.jpg"

                        # Rename the processed image
                        os.rename(temp_path, final_path)

                        # Remove original only after successful rename
                        if os.path.exists(str(image_path)):
                            os.remove(str(image_path))

                        print(f"Renamed to: {final_path.name}")
                        success_count += 1

                    except Exception as e:
                        # If AI naming fails, keep the processed image with original name
                        print(f"Warning: AI naming failed, keeping original name: {e}")
                        success_count += (
                            1  # Still count as success since image was processed
                        )

                except Exception as e:
                    error_msg = f"Error processing {image_path.name}: {str(e)}"
                    print(f"Error: {error_msg}")
                    errors.append(error_msg)
                    error_count += 1

        return success_count, error_count, errors

    except Exception as e:
        return 0, 1, [f"Critical error: {str(e)}"]


def main():
    """Main function to get user input and process images"""
    try:
        # Get user input
        root_folder = input("Enter the root folder path: ").strip()
        banner_name = input(
            "Enter the banner image name pattern (press Enter to skip): "
        ).strip()

        # Convert empty input to None
        banner_name = banner_name if banner_name else None

        print("\nStarting image processing...")
        print(
            f"Banner identification: {'Using name pattern: ' + banner_name if banner_name else 'Using image dimensions'}"
        )

        success_count, error_count, errors = process_images(root_folder, banner_name)

        # Print summary
        print("\nProcessing Summary:")
        print(f"Successfully processed: {success_count} images")
        print(f"Errors encountered: {error_count}")

        if errors:
            print("\nError Details:")
            for error in errors:
                print(f"- {error}")

    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
    except Exception as e:
        print(f"\nCritical error: {str(e)}")
    finally:
        print("\nProcess completed")


if __name__ == "__main__":
    main()
