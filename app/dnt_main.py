from pyimagesearch.centroidtracker import CentroidTracker
from pyimagesearch.trackableobject import TrackableObject
from imutils.video import FPS
import numpy as np
import imutils
import dlib
import tensorflow.compat.v1 as tf
from object_detection.utils import label_map_util
from object_detection.utils import visualization_utils as vis_util
import cv2
import sys
from PyQt5.QtCore import QThread, pyqtSignal, Qt, pyqtSlot, QObject, QRunnable, QThreadPool
from PyQt5.QtGui import QImage, QPixmap
from datetime import datetime
from sign_in.db_connection import *


class Signals(QObject):
    changePixmap = pyqtSignal(QImage)
    changeTextBox = pyqtSignal(str)
    changeButton = pyqtSignal(str)
    changeTitleBox = pyqtSignal(str)


class Detection(QRunnable):

    def __init__(self):
        super(Detection, self).__init__()
        self.signals = Signals()
        self.stopped = False
        self.video_source = None
        self.total_elapsed_time = 0
        self.totalLeft = 0
        self.totalRight = 0
        self.enter_position = 'right'
        self.model_path = 'model_dir/ssdnet_86k/frozen_inference_graph.pb'
        self.label_path = 'model_dir/ssdnet_86k/cow_label_map.pbtxt'
        self.num_classes = 1

    @pyqtSlot()
    def run(self):
        self.signals.changeTitleBox.emit(" Sol Toplam\n"
                                         "Sağ Toplam\n"
                                         "       Durum")
        self.vs = cv2.VideoCapture(self.video_source)
        detection_graph = tf.Graph()
        with detection_graph.as_default():
            od_graph_def = tf.GraphDef()
            with tf.gfile.GFile(self.model_path, 'rb') as fid:
                serialized_graph = fid.read()
                od_graph_def.ParseFromString(serialized_graph)
                tf.import_graph_def(od_graph_def, name='')

        label_map = label_map_util.load_labelmap(self.label_path)
        categories = label_map_util.convert_label_map_to_categories(label_map, max_num_classes=self.num_classes,
                                                                    use_display_name=True)
        category_index = label_map_util.create_category_index(categories)

        W = None
        H = None
        ct = CentroidTracker(maxDisappeared=40, maxDistance=50)
        trackers = []
        trackableObjects = {}

        totalFrames = 0
        skip_frame = 10

        fps = FPS().start()

        # Operation
        with detection_graph.as_default():
            with tf.Session(graph=detection_graph) as sess:
                while True:
                    ret, self.frame = self.vs.read()
                    if self.frame is None or self.stopped:
                        print("Video stream ended.")
                        break

                    self.frame = imutils.resize(self.frame, width=1000)  # Less data we have, faster we are.
                    rgb = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
                    self.frame = rgb

                    if W is None or H is None:
                        (H, W, ch) = self.frame.shape

                    self.status = "Bekliyor"
                    rects = []

                    if totalFrames % skip_frame == 0:
                        self.status = "Saptanıyor"
                        trackers = []

                        frame_expanded = np.expand_dims(self.frame, axis=0)
                        image_tensor = detection_graph.get_tensor_by_name('image_tensor:0')
                        boxes = detection_graph.get_tensor_by_name('detection_boxes:0')
                        scores = detection_graph.get_tensor_by_name('detection_scores:0')
                        classes = detection_graph.get_tensor_by_name('detection_classes:0')
                        num_detections = detection_graph.get_tensor_by_name('num_detections:0')

                        (boxes, scores, classes, num_detections) = sess.run(
                            [boxes, scores, classes, num_detections],
                            feed_dict={image_tensor: frame_expanded})

                        ymin = int((boxes[0][0][0] * H))
                        xmin = int((boxes[0][0][1] * W))
                        ymax = int((boxes[0][0][2] * H))
                        xmax = int((boxes[0][0][3] * W))

                        box_area = (xmax - xmin) * (ymax - ymin)
                        total_area = W * H
                        # For eliminating the false positives.
                        if box_area > total_area * 0.5:
                            ymin, xmin, xmax, ymax = (None, None, None, None)

                        if ymin is not None:
                            tracker = dlib.correlation_tracker()
                            rect = dlib.rectangle(xmin, ymin, xmax, ymax)
                            tracker.start_track(rgb, rect)

                            trackers.append(tracker)

                    else:

                        for tracker in trackers:
                            self.status = "Takip Ediliyor"

                            tracker.update(rgb)
                            pos = tracker.get_position()

                            xmin = int(pos.left())
                            ymin = int(pos.top())
                            xmax = int(pos.right())
                            ymax = int(pos.bottom())

                            rects.append((xmin, ymin, xmax, ymax))

                    # cv2.line(self.frame, (W // 2, 0), (W // 2, H), (0, 255, 255), 2)

                    objects = ct.update(rects)

                    for (objectID, centroid) in objects.items():
                        trackable_obj = trackableObjects.get(objectID, None)

                        if trackable_obj is None:
                            trackable_obj = TrackableObject(objectID, centroid)

                        else:
                            x = [c[0] for c in trackable_obj.centroids]
                            direction = centroid[0] - np.mean(x)
                            trackable_obj.centroids.append(centroid)

                            if not trackable_obj.counted:
                                # if the direction is negative (indicating the object
                                # is moving up) AND the centroid is above the center
                                # line, count the object
                                if direction < 0 and centroid[0] < int(W * 0.25):
                                    self.totalLeft += 1
                                    trackable_obj.counted = True
                                elif direction > 0 and centroid[0] > int(W * 0.75):
                                    self.totalRight += 1
                                    trackable_obj.counted = True

                        trackableObjects[objectID] = trackable_obj
                        text = "ID {}".format(objectID)

                        cv2.putText(self.frame, text, (centroid[0] - 10, centroid[1] - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                        cv2.circle(self.frame, (centroid[0], centroid[1]), 4, (0, 255, 0), -1)

                    self.signals.changeTextBox.emit(f"{self.totalLeft}\n{self.totalRight}\n{self.status}")
                    # End of the loop
                    bytesPerLine = ch * W
                    convertToQtFormat = QImage(rgb.data, W, H, bytesPerLine, QImage.Format_RGB888)
                    p = convertToQtFormat.scaled(800, 600, Qt.KeepAspectRatio)
                    self.signals.changePixmap.emit(p)

                    totalFrames += 1
                    fps.update()
        #
        self.signals.changeTitleBox.emit("Durum: ")
        # Clear output
        self.signals.changeTextBox.emit("Rapor kaydedildi.")
        # Alter button to Start.
        self.signals.changeButton.emit("start_button")
        # Stop FPS count.
        fps.stop()
        # Get total elapsed time.
        self.total_elapsed_time = fps.elapsed()
        # Create report to database.
        self.create_report(self.totalLeft, self.totalRight, fps.elapsed())
        # Finally, set placeholder.
        self.signals.changePixmap.emit(QImage('./Resources/placeholder2.png'))

    # Format the elapsed time like: 10h 20m 55s
    def create_report(self, total_left, total_right, elapsed_time):
        db_report = Database()
        t = datetime.now()
        current_time = t.strftime("%d/%m/%y %H:%M:%S.%f")[:-4]
        db_report.insert_report(current_time, self.convert_hour_format(elapsed_time), total_left, total_right,
                                self.get_id_local(), self.enter_position)
        print("create_report: done!")
        db_report.cursor.close()
        db_report.connection.close()

    def get_id_local(self):
        platform_name = platform.system()
        # For Windows
        if platform_name == "Windows":
            save_dir = os.getenv('APPDATA')
            file_path = save_dir + '\\Provactus\\usr.md'

        elif platform_name == "Linux":
            file_path = '/var/Provactus/usr.md'

        try:
            with open(file_path, 'r') as file:
                read_file = file.readlines()
                uid = read_file[0]
                return uid
        except FileExistsError:
            self.signals.changeTextBox.emit("Raporu kaydederken bir hata oluştu.")

    def convert_hour_format(self, second):
        minute = int(second / 60)
        left_second = second % 60
        hour = int(minute / 60)
        left_minute = minute % 60
        out = f"{hour}:{left_minute}:{int(left_second)}"
        return out
