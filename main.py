import cv2
import time
import collections
from kivy.app import App
from kivy.uix.image import Image
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.graphics.texture import Texture
import os

# بارگذاری مدل‌های Haar
cascade_face = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
cascade_smile = cv2.CascadeClassifier('haarcascade_smile.xml')

# تنظیمات دوربین و فیلم
frame_width = 640
frame_height = 480
fps = 20
buffer_seconds = 10  # 10 ثانیه قبل از خنده
record_seconds_after_smile = 5  # 5 ثانیه بعد از خنده
frame_buffer = collections.deque(maxlen=buffer_seconds * fps)

recording = False
recording_start_time = None
video_writer = None
video_filename = None
last_smile_time = 0

# تنظیمات دوربین
capture = cv2.VideoCapture(0)  # برای دوربین جلو
capture.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
capture.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)

if not capture.isOpened():
    print("Webcam not found!")
    exit()

class CameraApp(App):
    def build(self):
        self.img = Image()
        self.layout = BoxLayout(orientation='vertical')
        self.layout.add_widget(self.img)

        # دکمه برای تغییر دوربین
        self.switch_button = Button(text="Switch Camera")
        self.switch_button.bind(on_press=self.switch_camera)
        self.layout.add_widget(self.switch_button)

        Clock.schedule_interval(self.update, 1.0 / 30.0)  # 30 فریم در ثانیه
        return self.layout

    def switch_camera(self, instance):
        global capture
        if capture.isOpened():
            capture.release()

        # تغییر دوربین
        if capture.get(cv2.CAP_PROP_POS_FRAMES) == 0:  # اگر دوربین جلو است، دوربین پشتی را انتخاب کن
            capture = cv2.VideoCapture(1)  # دوربین پشتی
        else:
            capture = cv2.VideoCapture(0)  # دوباره دوربین جلو
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)

    def detect_smile(self, grayscale, img):
        global recording, recording_start_time, video_writer, video_filename, last_smile_time

        face = cascade_face.detectMultiScale(grayscale, 1.3, 5)
        for (x_face, y_face, w_face, h_face) in face:
            cv2.rectangle(img, (x_face, y_face), (x_face + w_face, y_face + h_face), (255, 130, 0), 2)
            roi_grayscale = grayscale[y_face:y_face + h_face, x_face:x_face + w_face]
            roi_color = img[y_face:y_face + h_face, x_face:x_face + w_face]
            smile = cascade_smile.detectMultiScale(roi_grayscale, 1.7, 9)  # بهبود تشخیص خنده با تنظیمات بهتر

            for (x_smile, y_smile, w_smile, h_smile) in smile:
                cv2.rectangle(roi_color, (x_smile, y_smile), (x_smile + w_smile, y_smile + h_smile), (255, 0, 130), 2)
                cv2.putText(roi_color, "Smiling", (x_smile, y_smile - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 130), 2, cv2.LINE_AA)

                # زمانی که برای اولین بار خنده تشخیص داده شد، ضبط شروع می‌شود
                if not recording and (time.time() - last_smile_time > 5):  # جلوگیری از ضبط مجدد به مدت 5 ثانیه
                    self.start_recording()  # شروع ضبط فیلم
                    last_smile_time = time.time()  # ذخیره زمان خنده آخر

        return img

    def update(self, dt):
        global recording, recording_start_time, video_writer, video_filename
        ret, frame = capture.read()
        if not ret:
            return

        frame = cv2.flip(frame, 1)  # چرخاندن تصویر برای دوربین جلویی
        grayscale = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        frame = self.detect_smile(grayscale, frame)

        frame_buffer.append(frame)

        buf = cv2.flip(frame, 0).tobytes()  # نمایش تصویر در کیوی
        texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
        texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
        self.img.texture = texture

        if recording:
            video_writer.write(frame)

        # توقف ضبط بعد از 5 ثانیه
        if recording and time.time() - recording_start_time >= record_seconds_after_smile:
            self.stop_recording()

    def start_recording(self):
        global recording, recording_start_time, video_writer, video_filename
        if not recording:
            recording = True
            recording_start_time = time.time()

            if not os.path.exists('videos'):
                os.makedirs('videos')  # ایجاد پوشه ذخیره ویدیو

            video_filename = f"videos/smile_{int(recording_start_time)}.avi"
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            video_writer = cv2.VideoWriter(video_filename, fourcc, fps, (frame_width, frame_height))

            # اضافه کردن فریم‌ها از 10 ثانیه قبل از خنده
            for frame in frame_buffer:
                video_writer.write(frame)

    def stop_recording(self):
        global recording, video_writer, video_filename
        if recording:
            recording = False
            video_writer.release()
            print(f"Video saved as: {video_filename}")
            video_writer = None

if __name__ == '__main__':
    CameraApp().run()

