import csv
import logging
import os
import re
import shutil
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import yaml
from tqdm import tqdm

from ai_image_name import ImageNameGenerator
from utils.image import ImageProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("image_processing.log")],
)
logger = logging.getLogger(__name__)


@dataclass
class ProcessingConfig:
    """Configuration settings for image processing"""

    ai_host: str
    ai_model: str
    image_quality: int
    banner_size: Tuple[int, int]
    regular_size: Tuple[int, int]
    max_retries: int
    retry_delay: int
    supported_extensions: set


def load_config(config_path: str = "config.yaml") -> ProcessingConfig:
    """Load configuration from YAML file or use defaults"""
    defaults = {
        "ai_host": "http://192.168.1.50:11435",
        "ai_model": "llava:7b",
        "image_quality": 95,
        "banner_size": (1200, 502),
        "regular_size": (720, 480),
        "max_retries": 3,
        "retry_delay": 2,
        "supported_extensions": [
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
            ".tiff",
            ".webp",
        ],
    }

    try:
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config_data = yaml.safe_load(f)
                defaults.update(config_data)
    except Exception as e:
        logger.warning(f"Failed to load config file: {e}. Using defaults.")

    return ProcessingConfig(
        **{k: v for k, v in defaults.items() if k != "supported_extensions"},
        supported_extensions=set(defaults["supported_extensions"]),
    )


def extract_folder_id(folder_name: str) -> Optional[str]:
    """Extract the numeric ID from the beginning of a folder name"""
    match = re.match(r"^\d+", folder_name)
    return match.group(0) if match else None


class ImageProcessingManager:
    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.processor = ImageProcessor(default_quality=config.image_quality)
        self.name_generator = ImageNameGenerator(
            host=config.ai_host, model=config.ai_model
        )
        self.folder_results = {}  # Store processing results for reporting

    def identify_banner_by_dimensions(self, image_paths: List[Path]) -> Optional[Path]:
        """Identify the banner image based on dimensions"""
        max_area = 0
        banner_image = None

        for img_path in image_paths:
            try:
                dimensions = self.processor.get_image_dimensions(str(img_path))
                area = dimensions[0] * dimensions[1]
                if area > max_area:
                    max_area = area
                    banner_image = img_path
            except Exception as e:
                logger.warning(f"Could not check dimensions of {img_path.name}: {e}")

        return banner_image

    def generate_ai_name(self, image_path: str, retries: int = 0) -> Optional[str]:
        """Generate AI-based name with retry mechanism"""
        try:
            new_name = self.name_generator.generate_name(image_path=image_path)
            if len(new_name) > 60:
                raise ValueError(f"Name '{new_name}' too long")
            return self._clean_filename(new_name)
        except Exception as e:
            if retries < self.config.max_retries:
                logger.warning(f"AI naming attempt {retries + 1} failed: {e}")
                time.sleep(self.config.retry_delay)
                return self.generate_ai_name(image_path, retries + 1)
            return None

    @staticmethod
    def _clean_filename(name: str) -> str:
        """Clean and format filename"""
        clean_name = "".join(c for c in name if c.isalnum() or c in "- ").strip()
        return clean_name.replace(" ", "-").lower()

    def process_single_image(
        self, image_path: Path, is_banner: bool = False
    ) -> Tuple[bool, Optional[Path]]:
        """
        Process a single image including resizing and AI-based renaming

        Args:
            image_path: Path to the image
            is_banner: Whether the image is a banner image

        Returns:
            Tuple[bool, Optional[Path]]: (success status, path to processed image)
        """
        try:
            # Determine target size based on image type
            target_size = (
                self.config.banner_size if is_banner else self.config.regular_size
            )
            logger.info(
                f"Processing: {image_path.name} {'(banner)' if is_banner else ''}"
            )

            # Resize the image
            temp_path = self.processor.resize_and_rename_image(
                str(image_path),
                target_size=target_size,
                remove_original=False,  # Don't remove yet, we'll rename it
            )

            if not temp_path:
                raise Exception("Image processing failed")

            # Generate AI-based name
            new_name = self.generate_ai_name(temp_path)
            if new_name:
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

                logger.info(f"Renamed to: {final_path.name}")
                return True, final_path
            else:
                # If AI naming fails, keep the processed image with original name
                logger.warning("AI naming failed, keeping original name")
                return True, Path(temp_path)

        except Exception as e:
            logger.error(f"Error processing {image_path.name}: {str(e)}")
            return False, None

    def process_directory(
        self, directory: Path, banner_name: Optional[str] = None
    ) -> Tuple[int, int, List[str]]:
        """Process all images in a directory"""
        success_count = 0
        error_count = 0
        errors = []
        processed_banner = None
        processed_inner = []

        try:
            # Collect valid image paths
            image_paths = [
                p
                for p in directory.glob("*")
                if p.suffix.lower() in self.config.supported_extensions
            ]

            if not image_paths:
                logger.info(f"No valid images found in directory: {directory}")
                return success_count, error_count, errors

            # First identify banner image for the directory
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
                    logger.info(f"Found banner image by name: {banner_image.name}")

            if not banner_image:
                # If no banner found by name (or no name provided), use largest image
                banner_image = self.identify_banner_by_dimensions(image_paths)
                if banner_image:
                    logger.info(
                        f"Identified banner image by dimensions: {banner_image.name}"
                    )

            # Process images with progress bar
            for image_path in tqdm(
                image_paths,
                desc=f"Processing {directory.name}",
                position=2,
                leave=False,
            ):
                try:
                    is_banner = image_path == banner_image
                    processed, final_path = self.process_single_image(
                        image_path, is_banner
                    )

                    if processed and final_path:
                        if is_banner:
                            processed_banner = final_path
                        else:
                            processed_inner.append(final_path)
                        success_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    error_msg = f"Error processing {image_path.name}: {str(e)}\n{traceback.format_exc()}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    error_count += 1

            # Store results for reporting
            self.folder_results[directory.name] = (processed_banner, processed_inner)

        except Exception as e:
            error_msg = f"Error processing directory {directory}: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            errors.append(error_msg)
            error_count += 1

        return success_count, error_count, errors

    def create_processing_report(self, output_dir: str = None) -> str:
        """
        Create a CSV report of processed images

        Args:
            output_dir (str, optional): Directory where to save the CSV report.
                                      If None, saves in the current working directory.

        Returns:
            str: Path to the generated CSV file
        """
        try:
            # Determine output directory
            if output_dir:
                output_path = Path(output_dir)
                # Create output directory if it doesn't exist
                output_path.mkdir(parents=True, exist_ok=True)
            else:
                output_path = Path.cwd()

            # Create report path with timestamp
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            report_path = output_path / f"image_processing_report_{timestamp}.csv"

            # Find the maximum number of inner images across all folders
            max_inner_images = max(
                len(inner_images)
                for _, (_, inner_images) in self.folder_results.items()
            )

            # Prepare headers
            headers = ["ID", "Folder Name", "Banner Image"]
            headers.extend([f"Inner Image {i + 1}" for i in range(max_inner_images)])

            with open(report_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)

                # Sort folders by their numeric ID
                sorted_folders = sorted(
                    self.folder_results.items(),
                    key=lambda x: int(extract_folder_id(x[0]))
                    if extract_folder_id(x[0])
                    else float("inf"),
                )

                for folder_name, (banner_image, inner_images) in sorted_folders:
                    folder_id = extract_folder_id(folder_name)
                    if not folder_id:
                        continue

                    # Prepare row data
                    row = [
                        folder_id,
                        folder_name,
                        banner_image.name if banner_image else "",
                    ]

                    # Add inner image names, padding with empty strings if necessary
                    inner_image_names = [img.name for img in inner_images]
                    row.extend(
                        inner_image_names
                        + [""] * (max_inner_images - len(inner_image_names))
                    )

                    writer.writerow(row)

            return str(report_path)

        except Exception as e:
            logger.error(f"Error creating processing report: {str(e)}")
            return ""

    def process_images(
        self,
        root_folder: str,
        banner_name: Optional[str] = None,
        output_dir: Optional[str] = None,
    ) -> Tuple[int, int, List[str], str]:
        """
        Process images in all sub-folders and generate report

        Args:
            root_folder (str): Path to root folder containing sub-folders with images
            banner_name (Optional[str]): Name pattern to identify banner images
            output_dir (Optional[str]): Directory where to save the CSV report

        Returns:
            Tuple[int, int, List[str], str]: (total_success, total_errors, all_errors, report_path)
        """
        start_time = time.time()
        total_success = 0
        total_errors = 0
        all_errors = []

        try:
            root_path = Path(root_folder).resolve()

            # Validate root folder
            if not root_path.exists():
                raise ValueError(f"Path does not exist: {root_path}")
            if not root_path.is_dir():
                raise ValueError(f"Path is not a directory: {root_path}")
            if not os.access(root_path, os.R_OK | os.W_OK):
                raise ValueError(f"Insufficient permissions for path: {root_path}")

            # Count total images across all folders for overall progress
            total_images = 0
            subfolders = [f for f in root_path.iterdir() if f.is_dir()]

            logger.info("Counting total images...")
            for subfolder_path in subfolders:
                image_paths = [
                    p
                    for p in subfolder_path.glob("*")
                    if p.suffix.lower() in self.config.supported_extensions
                ]
                total_images += len(image_paths)

            logger.info(f"Found {total_images} images in {len(subfolders)} folders")

            # Initialize overall progress bar
            overall_progress = tqdm(
                total=total_images, desc="Overall Progress", position=0, leave=True
            )

            # Process each subfolder
            for subfolder_path in tqdm(
                subfolders, desc="Folders", position=1, leave=True
            ):
                logger.info(f"\nProcessing folder: {subfolder_path}")
                try:
                    # Get number of images in current folder for subfolder progress
                    folder_images = [
                        p
                        for p in subfolder_path.glob("*")
                        if p.suffix.lower() in self.config.supported_extensions
                    ]

                    if not folder_images:
                        logger.info(
                            f"No valid images found in directory: {subfolder_path}"
                        )
                        continue

                    # Process directory with progress tracking
                    success, errors, error_list = self.process_directory(
                        subfolder_path, banner_name
                    )

                    # Update counts and progress
                    total_success += success
                    total_errors += errors
                    all_errors.extend(error_list)
                    overall_progress.update(len(folder_images))

                except Exception as e:
                    error_msg = f"Error processing subfolder {subfolder_path}: {str(e)}\n{traceback.format_exc()}"
                    logger.error(error_msg)
                    all_errors.append(error_msg)
                    total_errors += 1

            overall_progress.close()

            # Generate report after processing
            report_path = self.create_processing_report(output_dir)

            # Log completion time
            duration = time.time() - start_time
            logger.info(f"\nProcessing completed in {duration:.2f} seconds")
            logger.info(f"Total images processed: {total_success + total_errors}")
            logger.info(
                f"Success rate: {(total_success / (total_success + total_errors)) * 100:.1f}%"
            )

        except Exception as e:
            error_msg = (
                f"Critical error in process_images: {str(e)}\n{traceback.format_exc()}"
            )
            logger.error(error_msg)
            all_errors.append(error_msg)
            total_errors += 1
            report_path = ""

        return total_success, total_errors, all_errors, report_path


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
    """Main execution function"""
    try:
        # Load configuration
        config = load_config()
        processor = ImageProcessingManager(config)

        # Get user input
        root_folder = input("Enter the root folder path: ").strip()

        if not os.path.exists(root_folder):
            print("Error: The specified folder does not exist.")
            return

        banner_name = input(
            "Enter the banner image name pattern (press Enter to skip): "
        ).strip()

        output_dir = input(
            "Enter the output directory for the CSV report (press Enter for root folder's parent folder): "
        ).strip()

        banner_name = banner_name if banner_name else None
        output_dir = output_dir if output_dir else None

        base_folder_name = os.path.basename(root_folder)
        new_folder_name = f"{base_folder_name} - images"

        destination_folder = os.path.dirname(root_folder)
        destination_folder = os.path.join(destination_folder, new_folder_name)

        if output_dir:
            if not os.path.exists(output_dir):
                print("Error: The specified folder does not exist.")
                return
        else:
            output_dir = base_folder_name

        logger.info("\nStarting image processing...")
        logger.info(
            f"Banner identification: {'Using name pattern: ' + banner_name if banner_name else 'Using image dimensions'}"
        )

        # Process images and generate report
        success_count, error_count, errors, report_path = processor.process_images(
            root_folder, banner_name, output_dir
        )

        # Print summary
        logger.info("\nProcessing Summary:")
        logger.info(f"Successfully processed: {success_count} images")
        logger.info(f"Errors encountered: {error_count}")

        if report_path:
            logger.info(f"Report generated: {report_path}")
        else:
            logger.warning("Failed to generate processing report")

        if errors:
            logger.info("\nError Details:")
            for error in errors:
                logger.error(f"- {error}")

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

        copy_images_to_single_folder(root_folder, destination_folder)

    except KeyboardInterrupt:
        logger.warning("\nProcess interrupted by user")
    except Exception as e:
        logger.error(f"\nCritical error: {str(e)}")
    finally:
        logger.info("Process completed")


if __name__ == "__main__":
    main()
