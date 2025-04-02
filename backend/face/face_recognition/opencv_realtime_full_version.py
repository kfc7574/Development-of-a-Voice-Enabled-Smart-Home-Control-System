import ntpath
import sys
import pickle
import argparse
import numpy as np
import os
import time
from urllib.request import urlretrieve
import cv2
from imutils.video import WebcamVideoStream
from imutils.video import FPS
from sklearn.preprocessing import LabelEncoder
from sklearn.svm import SVC
import shutil

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
main_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from load_face_detection.opencv_dnns import detect
from face_dataset.load_dataset import load_images
from load_face_detection.utils import *

embedder_model = main_dir + "/nn4.small2.v1.t7"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "-i",
        "--input",
        type=str,
        default=main_dir + "/face_dataset/caltech_faces",
        help=main_dir + "/face_dataset/caltech_faces",
    )
    args = vars(ap.parse_args())

    embedder = cv2.dnn.readNetFromTorch(embedder_model)

    add_faces = input("Do you want to add new faces? (yes/no): ").strip().lower()
    if add_faces == 'yes':
        output_dir = input("Enter the directory to save new faces: ").strip()
        print("[INFO] Capturing new faces... (Please ensure at least 10 photos are captured.)")
        capture_new_faces(output_dir)
        new_faces_dir = output_dir

        # Check if the directory contains at least 10 photos
        num_photos = len([name for name in os.listdir(new_faces_dir) if os.path.isfile(os.path.join(new_faces_dir, name))])
        if num_photos < 10:
            print(f"[ERROR] Minimum of 10 photos required, only {num_photos} photos found.")
            # Optionally delete the directory if not meeting the requirement
            shutil.rmtree(new_faces_dir)
            new_faces_dir = None
        else:
            # Move entire directory to the dataset directory
            if os.path.exists(new_faces_dir) and os.path.isdir(new_faces_dir):
                target_dir = args["input"]
                shutil.move(new_faces_dir, target_dir)
                print(f"[INFO] Moved {new_faces_dir} to {target_dir}")
                print("[INFO] New faces moved to dataset directory.")
            else:
                print("[ERROR] Failed to move new faces: Invalid directory or directory does not exist.")
    else:
        new_faces_dir = None

    print("[INFO] Loading dataset....")
    (faces, names, _) = load_images(args["input"], min_size=10)
    print(f"[INFO] {len(faces)} images in dataset")

    # Check if we need to retrain the model based on photo count change or missing pickle files
    recognizer_path = os.path.join(main_dir, "recognizer.pickle")
    le_path = os.path.join(main_dir, "le.pickle")
    pickle_files_exist = os.path.exists(recognizer_path) and os.path.exists(le_path)

    needs_training = bool(new_faces_dir) or not pickle_files_exist
    print(f"[INFO] Needs training: {needs_training}")
    
    if needs_training:
        known_embeddings = []
        known_names = []

        print("[INFO] Serializing embeddings...")
        start = time.time()
        for img, name in zip(faces, names):
            if len(img.shape) == 2:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
            elif len(img.shape) == 3 and img.shape[2] == 1:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
            rects = detect(img)  # Assuming detect function is defined somewhere
            for rect in rects:
                (x, y, w, h) = rect["box"]
                roi = img[y : y + h, x : x + w]
                faceBlob = cv2.dnn.blobFromImage(
                    roi, 1.0 / 255, (96, 96), (0, 0, 0), swapRB=True, crop=False
                )
                embedder.setInput(faceBlob)
                vec = embedder.forward()

                known_embeddings.append(vec.flatten())
                known_names.append(name)

        end = time.time()
        print(
            f"[INFO] Serializing embeddings done, took {round(end - start, 3)} seconds"
        )

        le = LabelEncoder()
        labels = le.fit_transform(known_names)

        print("[INFO] Training model...")

        recognizer = SVC(C=1.0, kernel="linear", probability=True)
        recognizer.fit(known_embeddings, labels)

        with open(recognizer_path, "wb") as f:
            pickle.dump(recognizer, f)
        with open(le_path, "wb") as f:
            pickle.dump(le, f)
    else:
        print("[INFO] loading existing model...")
        if not main_dir + "/recognizer.pickle" or not main_dir + "/le.pickle":
            print("[ERROR] Model files not found. Please train the model first.")
            return

        with open(main_dir + "/recognizer.pickle", "rb") as f:
            recognizer = pickle.load(f)
        with open(main_dir + "/le.pickle", "rb") as f:
            le = pickle.load(f)

    vs = WebcamVideoStream().start()
    time.sleep(2.0)
    fps = FPS().start()

    while True:
        frame = vs.read()
        rects = detect(frame)  # Assuming detect function is defined somewhere
        for rect in rects:
            (x, y, w, h) = rect["box"]
            roi = frame[y : y + h, x : x + w]
            faceBlob = cv2.dnn.blobFromImage(
                roi, 1.0 / 255, (96, 96), (0, 0, 0), swapRB=True, crop=False
            )
            embedder.setInput(faceBlob)
            vec = embedder.forward()

            preds = recognizer.predict_proba(vec)[0]
            i = np.argmax(preds)
            proba = preds[i]
            name = le.classes_[i]

            # 設定辨識率門檻，若低於 90%，則顯示為未知
            if proba < 0.9:
                text = "Unknown: {:.2f}%".format(proba * 100)
            else:
                text = "{}: {:.2f}%".format(name, proba * 100)

            _y = y - 10 if y - 10 > 10 else y + 10
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv2.putText(
                frame, text, (x, _y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 2
            )

        fps.update()

        cv2.imshow("Frame", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break

    fps.stop()
    print("[INFO] Approximate FPS: {:.2f}".format(fps.fps()))

    cv2.destroyAllWindows()
    vs.stop()

if __name__ == "__main__":
    main()