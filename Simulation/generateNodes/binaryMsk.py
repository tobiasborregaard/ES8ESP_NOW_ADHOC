from PIL import Image, ImageFilter, ImageOps
import numpy as np
import matplotlib.pyplot as plt
import cv2

# Load the original image
image_path = "images/Notext.png"
original = Image.open(image_path).convert("L")  # convert to grayscale

# Convert to numpy array and apply adaptive thresholding using OpenCV
image_np = np.array(original)
blurred = cv2.GaussianBlur(image_np, (5, 5), 0)
_, binary_mask = cv2.threshold(blurred, 180, 255, cv2.THRESH_BINARY_INV)
invertedMask = cv2.bitwise_not(binary_mask)
# Save binary mask
binary_image = Image.fromarray(invertedMask)
binary_image_path = "images/floorplan_binary_mask.png"
binary_image.save(binary_image_path)

binary_image_path
