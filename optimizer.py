#!/usr/bin/env python3
# Simple image compression script for folder processing
# Compresses all images in a folder for faster loading on slow networks
# Usage: python folder_image_compressor.py input_folder output_folder
# Requirements: pip install pillow

import os
import sys
from PIL import Image, ImageOps
import concurrent.futures
import time
from pathlib import Path

def compress_image(input_path, output_path, quality=75, max_width=1000):
    # Compress a single image for web optimization
    # Returns tuple of (success, original_size, new_size, reduction_percentage)
    
    try:
        # Get original file size
        original_size = os.path.getsize(input_path)
        
        # Create output directory if needed
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Open and process the image
        with Image.open(input_path) as img:
            # Convert RGBA to RGB if saving as JPEG
            if img.mode == 'RGBA' and output_path.lower().endswith(('.jpg', '.jpeg')):
                # Use white background for transparency
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
                img = background
            
            # Resize if needed (maintain aspect ratio)
            if max_width and img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.LANCZOS)
            
            # Determine format based on extension
            extension = os.path.splitext(output_path)[1].lower()
            
            # Save with appropriate settings based on format
            if extension in ('.jpg', '.jpeg'):
                # Use progressive JPEG for faster perceived loading
                img.save(output_path, 'JPEG', quality=quality, optimize=True, progressive=True)
            elif extension == '.png':
                img.save(output_path, 'PNG', optimize=True, compress_level=9)
            elif extension == '.webp':
                img.save(output_path, 'WEBP', quality=quality, method=6)
            else:
                # Default save with format detection
                img.save(output_path, quality=quality, optimize=True)
        
        # Get new file size
        new_size = os.path.getsize(output_path)
        reduction = (original_size - new_size) / original_size * 100 if original_size > 0 else 0
        
        return (True, original_size, new_size, reduction)
    
    except Exception as e:
        print(f"Error processing {input_path}: {e}")
        return (False, 0, 0, 0)

def process_folder(input_folder, output_folder, quality=75, max_width=1000):
    # Process all images in a folder
    # Returns number of successfully processed images
    
    # Find all image files
    extensions = ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif']
    image_paths = []
    
    # Walk through all files in directory
    for root, _, files in os.walk(input_folder):
        for file in files:
            if any(file.lower().endswith(ext) for ext in extensions):
                # Get full path of image
                image_path = os.path.join(root, file)
                # Get relative path to maintain folder structure
                rel_path = os.path.relpath(image_path, input_folder)
                # Create output path
                output_path = os.path.join(output_folder, rel_path)
                # Add to list
                image_paths.append((image_path, output_path))
    
    total_files = len(image_paths)
    if total_files == 0:
        print(f"No images found in {input_folder}")
        return 0
    
    print(f"Found {total_files} images to process")
    
    # Process images using thread pool
    successful = 0
    total_original_size = 0
    total_new_size = 0
    
    # Create threadpool for parallel processing
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        
        # Submit all compression tasks
        for img_path, out_path in image_paths:
            future = executor.submit(compress_image, img_path, out_path, quality, max_width)
            futures.append((future, img_path, out_path))
        
        # Process results as they complete
        for i, (future, img_path, _) in enumerate(futures):
            success, original_size, new_size, reduction = future.result()
            
            if success:
                successful += 1
                total_original_size += original_size
                total_new_size += new_size
                
                # Output progress
                print(f"[{i+1}/{total_files}] {os.path.basename(img_path)}: "
                      f"{original_size/1024:.1f}KB → {new_size/1024:.1f}KB "
                      f"({reduction:.1f}% reduction)")
    
    # Print summary
    if successful > 0:
        total_reduction = (total_original_size - total_new_size) / total_original_size * 100
        print(f"\nSummary:")
        print(f"Processed {successful}/{total_files} images successfully")
        print(f"Total size reduction: {total_original_size/1024/1024:.2f}MB → "
              f"{total_new_size/1024/1024:.2f}MB ({total_reduction:.1f}%)")
    
    return successful

if __name__ == "__main__":
    # Simple command line interface
    if len(sys.argv) < 2:
        print("Usage: python folder_image_compressor.py input_folder [output_folder] [quality] [max_width]")
        sys.exit(1)
    
    # Get input folder (required)
    input_folder = sys.argv[1]
    
    # Get output folder (optional, defaults to 'optimized' subfolder)
    output_folder = sys.argv[2] if len(sys.argv) > 2 else os.path.join(input_folder, 'optimized')
    
    # Get quality (optional, default=75)
    quality = int(sys.argv[3]) if len(sys.argv) > 3 else 75
    
    # Get max width (optional, default=1000)
    max_width = int(sys.argv[4]) if len(sys.argv) > 4 else 1000
    
    # Verify input folder exists
    if not os.path.isdir(input_folder):
        print(f"Error: Input folder '{input_folder}' does not exist")
        sys.exit(1)
    
    # Create output folder if needed
    os.makedirs(output_folder, exist_ok=True)
    
    print(f"Processing images from: {input_folder}")
    print(f"Saving optimized images to: {output_folder}")
    print(f"Quality: {quality}, Max width: {max_width}px")
    
    # Process and time the operation
    start_time = time.time()
    processed = process_folder(input_folder, output_folder, quality, max_width)
    elapsed = time.time() - start_time
    
    print(f"\nCompleted processing {processed} images in {elapsed:.1f} seconds")