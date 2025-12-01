import os
import cv2
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from deepface import DeepFace
import albumentations as A
import streamlit as st
import logging
from src.config.settings import Config
from src.database.db_manager import DBManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ImageService:
    transform = A.Compose([
        A.HorizontalFlip(p=0.5),
        A.RandomBrightnessContrast(p=0.3),
        A.ShiftScaleRotate(p=0.4),
        A.GaussNoise(p=0.2),
        A.MotionBlur(p=0.2),
        A.Resize(224, 224)
    ])

    @staticmethod
    def save_image_for_student(enrollment_username, name, image, capture_count):
        """Saves a captured image for a student."""
        try:
            folder = os.path.join(str(Config.TRAINING_IMAGES_DIR), str(enrollment_username))
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, f"{capture_count}.jpg")
            image.save(path)
            return path
        except Exception as e:
            logger.error(f"Error saving image: {e}")
            return None

    @staticmethod
    def augment_training_images(enrollment_username, num_originals=10, num_target_total=50):
        """Augments captured images to create a larger dataset."""
        folder = os.path.join(str(Config.TRAINING_IMAGES_DIR), str(enrollment_username))
        if not os.path.exists(folder):
             return False, "Student folder not found."

        all_files = os.listdir(folder)
        
        # Cleanup extra files if any
        for f in all_files:
            try: 
                file_num = int(f.split('.')[0])
                if file_num > num_originals: os.remove(os.path.join(folder, f))
            except ValueError: continue

        original_images = []
        for i in range(1, num_originals + 1):
            img_path = os.path.join(folder, f"{i}.jpg")
            if os.path.exists(img_path): 
                image = cv2.imread(img_path)
                if image is not None:
                    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    original_images.append(image)
        
        if not original_images: return False, "No original images found."

        num_to_generate = num_target_total - len(original_images)
        if num_to_generate <= 0: return True, "Sufficient images exist."

        current_img_count = num_originals + 1
        for _ in range(num_to_generate):
            base_image = original_images[np.random.randint(0, len(original_images))]
            augmented = ImageService.transform(image=base_image)['image']
            save_path = os.path.join(folder, f"{current_img_count}.jpg")
            augmented_bgr = cv2.cvtColor(augmented, cv2.COLOR_RGB2BGR)
            cv2.imwrite(save_path, augmented_bgr)
            current_img_count += 1
            
        return True, f"Generated {num_to_generate} new images."

    @staticmethod
    @st.cache_resource
    def train_model_cached():
        """Wrapper for train_model to allow caching."""
        try:
            pkl_path = os.path.join(str(Config.TRAINING_IMAGES_DIR), "representations_SFace.pkl")
            if os.path.exists(pkl_path):
                os.remove(pkl_path)
            
            training_dir = str(Config.TRAINING_IMAGES_DIR)
            student_dirs = [d for d in os.listdir(training_dir) if os.path.isdir(os.path.join(training_dir, d))]
            
            if not student_dirs: return False, "No student images found for training."
            
            has_images = any(len(os.listdir(os.path.join(training_dir, d))) > 0 for d in student_dirs)
            if not has_images: return False, "Student folders are empty, cannot train."
            
            # Find a sample image
            sample_img_path = None
            for student_dir in student_dirs:
                student_path = os.path.join(training_dir, student_dir)
                images = [f for f in os.listdir(student_path) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
                if images:
                    sample_img_path = os.path.join(student_path, images[0])
                    break
            
            if sample_img_path is None: return False, "Could not find valid sample image to initiate training."
            
            DeepFace.find(img_path=sample_img_path, db_path=training_dir, model_name="SFace", enforce_detection=False, silent=True)
            return True, "Model (re)trained successfully!"
        except Exception as e:
            logger.error(f"Training failed: {e}")
            return False, f"Training failed: {e}"

    @staticmethod
    def train_model():
        """Public facing train_model that clears the cache and calls the cached version."""
        ImageService.train_model_cached.clear()
        return ImageService.train_model_cached()

    @staticmethod
    def recognize_face_in_image(pil_image):
        """Recognizes faces in the given image."""
        try:
            img_np = np.array(pil_image.convert('RGB'))
            training_dir = str(Config.TRAINING_IMAGES_DIR)
            
            results_list = DeepFace.find(img_path=img_np, db_path=training_dir, model_name="SFace", enforce_detection=False, detector_backend='opencv', silent=True)
            recognized_data = []
            
            students_df = DBManager.get_users_by_role('student')
            if students_df.empty: return pd.DataFrame(), pd.DataFrame()
            
            for results_df in results_list:
                if not results_df.empty:
                    for _, top_match in results_df.iterrows():
                        x, y, w, h = top_match['source_x'], top_match['source_y'], top_match['source_w'], top_match['source_h']
                        
                        pad = 10
                        cropped_face = img_np[max(0, y-pad):min(y+h+pad, img_np.shape[0]), max(0, x-pad):min(x+w+pad, img_np.shape[1])]
                        
                        if cropped_face.size == 0: continue
                        
                        is_real = True # Placeholder for liveness detection if implemented
                        
                        file_path = top_match["identity"]
                        if not isinstance(file_path, str): continue
                        
                        enroll_username = file_path.split(os.sep)[-2]
                        
                        student_row = students_df[students_df["Enrollment"].astype(str) == str(enroll_username)]
                        if not student_row.empty: 
                            recognized_data.append({
                                "Enrollment": enroll_username, 
                                "Name": student_row.iloc[0]["name"], 
                                "Distance": round(top_match["distance"], 3), 
                                "x": x, "y": y, "w": w, "h": h, 
                                "is_real": is_real
                            })
            
            if recognized_data: 
                all_results_df = pd.DataFrame(recognized_data)
                live_students_df = all_results_df[all_results_df["is_real"] == True]
                unique_live_students_df = live_students_df.drop_duplicates(subset=["Enrollment"])[["Enrollment", "Name"]]
                return all_results_df, unique_live_students_df
            else: 
                return pd.DataFrame(), pd.DataFrame()
        except Exception as e:
            if "representations_SFace.pkl" in str(e): logger.warning("Model not trained.")
            else: logger.error(f"Recognition error: {e}")
            return pd.DataFrame(), pd.DataFrame()

    @staticmethod
    def draw_on_image(pil_img, results_df):
        """Draws bounding boxes and names on the image."""
        img_draw = pil_img.copy()
        draw = ImageDraw.Draw(img_draw)
        try: font = ImageFont.load_default(size=15)
        except IOError: font = ImageFont.load_default()
        
        if not results_df.empty:
            for _, row in results_df.iterrows():
                x, y, w, h = row['x'], row['y'], row['w'], row['h']
                name, distance, is_real = row['Name'], row['Distance'], row['is_real']
                
                color = "lime" if is_real else "red"
                text = f"{name} ({distance})" if is_real else f"SPOOF ({name})"
                
                draw.rectangle([(x, y), (x + w, y + h)], outline=color, width=3)
                text_bbox = draw.textbbox((x, y - 20), text, font=font)
                draw.rectangle(text_bbox, fill=color)
                draw.text((x + 2, y - 20), text, fill="black", font=font)
        return img_draw
