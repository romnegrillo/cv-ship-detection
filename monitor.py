from PyQt5 import QtWidgets, QtGui
from PyQt5.uic import loadUi
import sys
import boto3
from botocore.config import Config
from typing import List, Set, Dict, Tuple, Optional, Union
import threading
import time
import configparser

config = configparser.RawConfigParser()
config.read("config.ini")

class ShipRecords:
    _AWS_ACCESS_KEY = config["General"]["AWS_ACCESS_KEY"]
    _AWS_SECRET_ACCESS = config["General"]["AWS_SECRET_ACCESS"]
    _BUCKET_NAME = config["General"]["BUCKET_NAME"]

    def __init__(self) -> None:
        self.config = Config(connect_timeout=3600, read_timeout=3600)
        self.s3 = boto3.client('s3',
                               aws_access_key_id=ShipRecords._AWS_ACCESS_KEY,
                               aws_secret_access_key=ShipRecords._AWS_SECRET_ACCESS,
                               config=self.config)

    def get_recent_image(self) -> Union[str, None]:
        response = self.s3.list_objects(
            Bucket=ShipRecords._BUCKET_NAME)

        image_dict = {}
        for content in response.get('Contents', []):
            image_dict[content["Key"]] = content["LastModified"]

        img_list_sorted = sorted(image_dict.items(), key=lambda item: item[1], reverse=True)

        if len(img_list_sorted) > 0:
            latest_image_name_s3_path = img_list_sorted[0][0]
            print(latest_image_name_s3_path)

            # detected_ships/10-01-2022-10-45-AM-2.png
            # Split the path to get the date, time and number of ships.
            filename = latest_image_name_s3_path.split(
                "/")[1].replace(".png", "")
            date_detected = filename[0:10]
            time_detected = filename[11:19]
            num_ships = filename[20:]

            self.s3.download_file(ShipRecords._BUCKET_NAME, latest_image_name_s3_path,
                                  "./current_image/current_image.png")

            return ("./current_image/current_image.png", date_detected, time_detected, num_ships)

        return (None, None, None, None)

    def get_image_list(self) -> List[str]:
        response = self.s3.list_objects(
            Bucket=ShipRecords._BUCKET_NAME, Prefix="detected_ships/")
        
        image_dict = {}
        for content in response.get('Contents', []):
            image_dict[content["Key"]] = content["LastModified"]

        img_list_sorted = sorted(image_dict.items(), key=lambda item: item[1], reverse=True)
        img_list_sorted = [i[0] for i in img_list_sorted]

        return img_list_sorted

    def get_selected_image(self, image_s3_path) -> str:

        # detected_ships/10-01-2022-10-45-AM-2.png
        # Split the path to get the date, time and number of ships.
        filename = image_s3_path.split(
            "/")[1].replace(".png", "")
        date_detected = filename[0:10]
        time_detected = filename[11:19]
        num_ships = filename[20:]

        try:
            self.s3.download_file(ShipRecords._BUCKET_NAME, image_s3_path,
                                  "./current_image/selected_image.png")

            return ("./current_image/selected_image.png", date_detected, time_detected, num_ships)
        except Exception as error:
            pass

        return None, None, None, None


class StartWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super(StartWindow, self).__init__()
        loadUi("startwindow.ui", self)
        self.init_widgets()

    def init_widgets(self):
        self.start_button.clicked.connect(self.start_button_clicked)
        self.exit_button.clicked.connect(self.exit_button_clicked)

    def start_button_clicked(self) -> None:
        self.w = RecentLogWindow()
        self.w.show()
        self.close()

    def exit_button_clicked(self) -> None:
        self.close()


class RecentLogWindow(QtWidgets.QMainWindow):
    IMAGE_REFRESH_INTERVAL = 5

    def __init__(self) -> None:
        super(RecentLogWindow, self).__init__()
        loadUi("recentlogwindow.ui", self)
        self.init_widgets()

        self.ship_records = ShipRecords()

        self.thread = threading.Thread(target=self.display_recent_image)
        self.thread.start()
        self.stop_thread = False

    def init_widgets(self) -> None:
        self.view_log_button.clicked.connect(self.view_log_button_clicked)
        self.back_button.clicked.connect(self.back_button_clicked_clicked)
        # self.image_placeholder

    def display_recent_image(self):
        while True:
            image_path, date_detected, time_detected, num_ships = self.ship_records.get_recent_image()

            if image_path is not None:
                print(image_path)
                
                try:
                    self.image_placeholder.setStyleSheet(
                        f"border-image: url({image_path}) 0 0 0 0 stretch stretch;")
                except RuntimeError as error:
                    break

            time.sleep(RecentLogWindow.IMAGE_REFRESH_INTERVAL)

            if self.stop_thread:
                break

    def view_log_button_clicked(self) -> None:
        self.w = PastLogWindow()
        self.w.show()
        self.stop_thread = True
        self.close()

    def back_button_clicked_clicked(self) -> None:
        self.w = StartWindow()
        self.w.show()
        self.stop_thread = True
        self.close()


class PastLogWindow(QtWidgets.QMainWindow):
    IMAGE_REFRESH_INTERVAL = 60

    def __init__(self) -> None:
        super(PastLogWindow, self).__init__()
        loadUi("pastlogwindow.ui", self)
        self.init_widgets()

        self.ship_records = ShipRecords()

        self.thread = threading.Thread(target=self.update_image_list)
        self.thread.start()
        self.stop_thread = False

    def init_widgets(self) -> None:
        self.back_button.clicked.connect(self.back_button_clicked)
        self.image_list_widget.itemClicked.connect(
            self.image_list_widget_item_clicked)
        # self.image_placeholder
        # self.date_label
        # self.num_ship_label

    def update_image_list(self):
        while True:
            self.image_list_widget.clear()
            self.image_list_widget.addItems(self.ship_records.get_image_list())

            time.sleep(PastLogWindow.IMAGE_REFRESH_INTERVAL)

            if self.stop_thread:
                break

    def image_list_widget_item_clicked(self, item):
        image_path, date_detected, time_detected, num_ships = self.ship_records.get_selected_image(item.text())

        if image_path is not None:
            
            self.image_placeholder.setStyleSheet(
                f"border-image: url({image_path}) 0 0 0 0 stretch stretch;")

            self.date_label.setText(f"Date: {date_detected} {time_detected}")
            self.num_ship_label.setText(f"No. Ships Detected: {num_ships}")

    def back_button_clicked(self):
        self.w = RecentLogWindow()
        self.w.show()
        self.stop_thread = True
        self.close()


def main():
    app = QtWidgets.QApplication(sys.argv)
    w = StartWindow()
    w.show()
    app.exec_()


if __name__ == "__main__":
    main()
