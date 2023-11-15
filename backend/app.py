from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from collections import defaultdict
import torch
from PIL import Image, ImageDraw, ImageFont
import os
import base64
from io import BytesIO

# Global variable to store detection history
detection_history = defaultdict(lambda: timedelta(0))


last_detection_time = None
last_cat_position = None
# confidence check
CONFIDENCE_THRESHOLD = 0.1

# store the furniture position in the camera
SOFA_BOUNDING_BOX = {'xmin': 0, 'ymin': 0, 'xmax': 900, 'ymax': 900}
TABLE_BOUNDING_BOX = {'xmin': 400, 'ymin': 150, 'xmax': 600, 'ymax': 300}

# Initialize Flask app
app = Flask(__name__)

UPLOAD_FOLDER = 'img/captured'
PROCESSED_FOLDER = 'img/processed'
# Ensure the folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# Load YOLOv5 model
model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)

@app.route('/detect', methods=['POST'])
def detect():
    global last_detection_time, last_cat_position

    if 'image' not in request.files:
        return jsonify({'error': 'No image part in the request'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        # Construct unique file name
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        image_name = f"{timestamp}.jpg"
        image_path = os.path.join(UPLOAD_FOLDER, image_name)
        file.save(image_path)

        # Read the image with PIL
        image = Image.open(image_path)

        # Perform inference
        results = model(image)
        results_data = results.pandas().xyxy[0]

        # Filter for cat and sofa/table
        results_data = results_data[results_data['name'] == 'cat']


        # def calculate_speed(current_position, current_timestamp):
        #     global last_cat_position, last_timestamp
        #     if last_cat_position is None or last_timestamp is None:
        #         last_cat_position = current_position
        #         last_timestamp = current_timestamp
        #         return 0

        #     # Calculate distance moved (this is a simplified 2D distance calculation)
        #     distance = ((current_position['xmin'] - last_cat_position['xmin']) ** 2 + 
        #                 (current_position['ymin'] - last_cat_position['ymin']) ** 2) ** 0.5

        #     # Calculate time difference in seconds
        #     time_diff = (current_timestamp - last_timestamp).total_seconds()

        #     # Update last position and timestamp
        #     last_cat_position = current_position
        #     last_timestamp = current_timestamp

        #     # Speed = distance/time
        #     if time_diff > 0:
        #         return distance / time_diff
        #     return 0
        
        current_time = datetime.now()
        if last_detection_time is None:
            last_detection_time = current_time

        
        for index, row in results_data.iterrows():
            if row['name'] == 'cat' and row['confidence'] >= CONFIDENCE_THRESHOLD:
                
                current_position = {'xmin': row['xmin'], 'ymin': row['ymin'], 'xmax': row['xmax'], 'ymax': row['ymax']}
                time_since_last_detection = current_time - last_detection_time
                
                # speed = calculate_speed(row, current_time)
                
                if overlaps_sofa(row):  # You'll need to implement overlaps_sofa
                    detection_history['sofa'] += current_time - last_detection_time
                elif overlaps_table(row):  # Similarly, implement overlaps_table
                    detection_history['table'] += current_time - last_detection_time
                else:
                    detection_history['elsewhere'] += current_time - last_detection_time

            
            draw = ImageDraw.Draw(image)

            font_size = 30
            font = ImageFont.load_default()

            label = f"{row['name']} {row['confidence']:.2f}"
            label_width = len(label) * font_size
            label_height = font_size

            # Calculate position for label inside the bounding box
            label_x = max(row['xmin'], row['xmin'] + 5)
            label_y = max(row['ymin'], row['ymin'] + 5)
            # Check if the label fits inside the box, if not adjust
            if label_x + label_width > row['xmax']:
                label_x = row['xmax'] - label_width
            if label_y + label_height > row['ymax']:
                label_y = row['ymax'] - label_height
            
            # Draw rectangle
            draw.rectangle([(row['xmin'], row['ymin']), (row['xmax'], row['ymax'])], outline='red', width=2)
            
            # Draw label rectangle and label text
            
            # draw.rectangle([(row['xmin'], row['ymin'] - label_height), (row['xmin'] + label_width, row['ymin'])], fill='red')
            # draw.text((row['xmin'], row['ymin'] - label_height), label, fill='white', font=font)
            label_background = [(label_x, label_y), (label_x + label_width, label_y + label_height)]
            draw.rectangle(label_background, fill='black')
            draw.text((label_x, label_y), label, fill='white', font=font)

            # draw the bounding box for the sofa and the table
            draw.rectangle([(SOFA_BOUNDING_BOX['xmin'], SOFA_BOUNDING_BOX['ymin']), 
                    (SOFA_BOUNDING_BOX['xmax'], SOFA_BOUNDING_BOX['ymax'])], 
                    outline='blue', width=2)
            
            draw.rectangle([(TABLE_BOUNDING_BOX['xmin'], TABLE_BOUNDING_BOX['ymin']), 
                    (TABLE_BOUNDING_BOX['xmax'], TABLE_BOUNDING_BOX['ymax'])], 
                    outline='green', width=2)
    
        last_detection_time = current_time

        # Determine which has more duration
        if detection_history:
            cat_stay = max(detection_history, key=detection_history.get)
        else:
            cat_stay = 'none'

        processed_image_name = f"processed_{image_name}"
        processed_image_path = os.path.join(PROCESSED_FOLDER, processed_image_name)
        image.save(processed_image_path)

        # Convert results to JSON
        data = results_data.to_json(orient="records")

        print(f'Detection Results: {data},{cat_stay}')

        # Return the response with paths to saved images
        return jsonify({
            'detections': data,
            'image_path': image_path,
            'processed_image_path': processed_image_path,
            'cat_stay': cat_stay
        }), 200

# Functions to check if cat overlaps with sofa or table (requires implementation)
def overlaps_sofa(cat_detection):
    cat_xmin, cat_ymin, cat_xmax, cat_ymax = cat_detection['xmin'], cat_detection['ymin'], cat_detection['xmax'], cat_detection['ymax']
    sofa_xmin, sofa_ymin, sofa_xmax, sofa_ymax = SOFA_BOUNDING_BOX.values()

    # Check if there is any overlap
    return not (cat_xmax < sofa_xmin or cat_xmin > sofa_xmax or cat_ymax < sofa_ymin or cat_ymin > sofa_ymax)

def overlaps_table(cat_detection):
    cat_xmin, cat_ymin, cat_xmax, cat_ymax = cat_detection['xmin'], cat_detection['ymin'], cat_detection['xmax'], cat_detection['ymax']
    table_xmin, table_ymin, table_xmax, table_ymax = TABLE_BOUNDING_BOX.values()

    # Check if there is any overlap
    return not (cat_xmax < table_xmin or cat_xmin > table_xmax or cat_ymax < table_ymin or cat_ymin > table_ymax)

if __name__ == '__main__':
    app.run(debug=True)
