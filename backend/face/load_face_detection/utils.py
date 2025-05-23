import cv2
import os
import time
import numpy as np
from imutils.video import WebcamVideoStream

def capture_new_faces(output_dir, num_photos_per_direction=4, delay=1):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    directions = ["look straight", "look up", "look down", "look left", "look right"]
    num_augmented_per_direction = 2  # Number of images per direction to augment
    
    vs = WebcamVideoStream(src=0).start()
    time.sleep(2.0)

    count = 0
    for direction in directions:
        print(f"[INFO] Please {direction}")
        time.sleep(3)

        for _ in range(num_photos_per_direction):
            frame = vs.read()
            filename = os.path.join(output_dir, f"face_{count+1}.jpg")
            cv2.imwrite(filename, frame)
            count += 1
            print(f"[INFO] Captured photo {count}")
            time.sleep(delay)
        
        # Augment some of the captured images
        for i in range(num_augmented_per_direction):
            filename_to_augment = os.path.join(output_dir, f"face_{count - num_photos_per_direction + i + 1}.jpg")
            augment_image(filename_to_augment, output_dir)
    
    vs.stop()
    
def augment_image(image_path, output_dir):
    image = cv2.imread(image_path)
    basename = os.path.basename(image_path).split('.')[0]
    
    # Original image (already saved during capture, no need to save again)
    
    # Flip horizontally
    flipped = cv2.flip(image, 1)
    cv2.imwrite(os.path.join(output_dir, f"{basename}_flipped.jpg"), flipped)
    
    # Rotate 15 degrees
    rows, cols, _ = image.shape
    M = cv2.getRotationMatrix2D((cols / 2, rows / 2), 15, 1)
    rotated = cv2.warpAffine(image, M, (cols, rows))
    cv2.imwrite(os.path.join(output_dir, f"{basename}_rotated15.jpg"), rotated)
    
    # Rotate -15 degrees
    M = cv2.getRotationMatrix2D((cols / 2, rows / 2), -15, 1)
    rotated = cv2.warpAffine(image, M, (cols, rows))
    cv2.imwrite(os.path.join(output_dir, f"{basename}_rotated-15.jpg"), rotated)

    # Adjust brightness
    # Increase brightness
    brighter = cv2.convertScaleAbs(image, alpha=1.2, beta=30)
    cv2.imwrite(os.path.join(output_dir, f"{basename}_brighter.jpg"), brighter)
    
    # Decrease brightness
    darker = cv2.convertScaleAbs(image, alpha=0.8, beta=-30)
    cv2.imwrite(os.path.join(output_dir, f"{basename}_darker.jpg"), darker)

    # Resize - zoom in
    zoomed_in = cv2.resize(image, None, fx=1.2, fy=1.2, interpolation=cv2.INTER_LINEAR)
    cv2.imwrite(os.path.join(output_dir, f"{basename}_zoomed_in.jpg"), zoomed_in)
    
    # Resize - zoom out
    zoomed_out = cv2.resize(image, None, fx=0.8, fy=0.8, interpolation=cv2.INTER_LINEAR)
    cv2.imwrite(os.path.join(output_dir, f"{basename}_zoomed_out.jpg"), zoomed_out)
