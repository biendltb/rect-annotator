#! /usr/bin/env python
# -*- coding: utf-8 -*-


import sys
import os
import glob
import numpy as np

try:
    from PyQt5 import QtWidgets, QtGui, QtCore
except:
    print('No PyQt-Module installed.')
    quit()


__author__ = "Bien Nguyen"
__copyright__ = "Copyright 2019, Bien Nguyen"
__credits__ = ["Bien Nguyen"]
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Bien Nguyen"
__email__ = "biendltb@gmail.com"
__status__ = "Production"


IMAGE_FOLDER_PATH = '../image_dataset/'

# ###########################

class App(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        # Main window
        self.title = 'Rect Annotator'
        self.width = 640
        self.height = 480

        self.img_label = QtWidgets.QLabel(self)
        self.img_label.setAlignment(QtCore.Qt.AlignCenter)

        # Browse image folder
        self.image_browser = ImageBrowser(IMAGE_FOLDER_PATH)

        # Annotating file
        self.ann_file_manager = AnnotationFileManager(IMAGE_FOLDER_PATH + 'anns.txt')

        # Frezze image when drawing
        self.on_drawing_img = None

        self.initUI()


    def initUI(self):
        self.setWindowTitle(self.title)
        # self.setGeometry(self.left, self.top, self.width, self.height)

        self.load_new_im(show_rect=False)

        self.show()

        self.load_new_im()

        # self.img_label.move(-161,-160)

    def load_new_im(self, show_rect=True):
        im_name = self.image_browser.get_current_im_name()
        real_rects = self.ann_file_manager.get_im_rects(im_name)

        self.display_im = DisplayImage(IMAGE_FOLDER_PATH + im_name, real_rects, self.width, show_rect)

        self.width = self.display_im.pixmap_im.width()
        self.height = self.display_im.pixmap_im.height()

        self.setFixedSize(self.display_im.pixmap_im.width(), self.display_im.pixmap_im.height())
        self.center()

        self.img_label.setPixmap(self.display_im.get_display_im())


    def center(self):
        frameGm = self.frameGeometry()
        centerPoint = QtWidgets.QDesktopWidget().availableGeometry().center()
        frameGm.moveCenter(centerPoint)
        self.move(frameGm.topLeft())


    def keyPressEvent(self, e):

        rotating_angle = 0

        if e.key() == QtCore.Qt.Key_Q:
            # Rotation transform
            rotating_angle = -5
        elif e.key() == QtCore.Qt.Key_W:
            rotating_angle = 5
        elif e.key() == QtCore.Qt.Key_A:
            rotating_angle = -1
        elif e.key() == QtCore.Qt.Key_S:
            rotating_angle = 1
        elif e.key() == QtCore.Qt.Key_T:
            # delete the last rectangles from the rectangle list
            self.display_im.del_last_rect()
            self.img_label.setPixmap(self.display_im.get_display_im())
        elif e.key() == QtCore.Qt.Key_Right:
            # Always save and check first
            self.ann_file_manager.update_im_rects(self.image_browser.get_current_im_name(),
                                                  self.display_im.get_real_rect())
            self.ann_file_manager.save()
            if (self.image_browser.next_im() == -1):
                QtWidgets.QMessageBox.information(self, "", "End of the image list", QtWidgets.QMessageBox.Ok)
                return

            self.load_new_im()
        elif e.key() == QtCore.Qt.Key_Left:
            # Always save and check first
            self.ann_file_manager.update_im_rects(self.image_browser.get_current_im_name(),
                                                  self.display_im.get_real_rect())
            self.ann_file_manager.save()
            if (self.image_browser.prev_im() == -1):
                QtWidgets.QMessageBox.information(self, "", "At the beginning of the image list", QtWidgets.QMessageBox.Ok)
                return

            self.load_new_im()


        if rotating_angle != 0:
            self.display_im.angle += rotating_angle

            # Reset angle when it's a round
            if abs(self.display_im.angle/360) > 1:
                self.display_im %= 360

            tmp_img = self.display_im.get_display_im()
            self.img_label.setPixmap(tmp_img)


    def mousePressEvent(self, e):
        self.rect_start_pos = e.pos()

        self.on_drawing_img = self.display_im.get_display_im()

    def mouseMoveEvent(self, e):
        display_img = self.on_drawing_img

        pos_in_img_x, pos_in_img_y, w, h = self.get_curr_rect_params(e, display_img)

        tmp_pixmap = draw_rect(display_img, pos_in_img_x, pos_in_img_y, w, h)
        self.img_label.setPixmap(tmp_pixmap)

    def mouseReleaseEvent(self, e):
        display_img = self.display_im.get_display_im()
        pos_in_img_x, pos_in_img_y, w, h = self.get_curr_rect_params(e, display_img)

        # minimum size of the rectangle is 5x5
        if w >= 5 and h >= 5:
            self.display_im.add_rect(pos_in_img_x, pos_in_img_y, w, h)

    def mouseDoubleClickEvent(self, e):
        click_pos = [e.pos().x(), e.pos().y()]

        self.check_falling_in(click_pos, self.display_im.angle)


    def closeEvent(self, e):
        # Save data before closing the app
        self.ann_file_manager.update_im_rects(self.image_browser.get_current_im_name(),
                                              self.display_im.get_real_rect())
        self.ann_file_manager.save()

    # Collect current data about the drawn rectangle
    def get_curr_rect_params(self, e, display_img):
        # print('Mouse move')
        w = e.pos().x() - self.rect_start_pos.x()
        h = e.pos().y() - self.rect_start_pos.y()

        # Calculate the real-time rectangle draw by the mouse
        pos_in_img_x = self.rect_start_pos.x() + (display_img.width() - self.width) / 2
        pos_in_img_y = self.rect_start_pos.y() + (display_img.height() - self.height) / 2

        return pos_in_img_x, pos_in_img_y, w, h

    # check if the click falls in one of existing rectangle
    def check_falling_in(self, pos, im_angle):
        # position of the click point to the center of the windows center
        pos_x = pos[0] - self.width/2
        pos_y = pos[1] - self.height/2

        for rect in self.display_im.rects:
            rotate_angle = rect.im_angle - im_angle
            cos = np.cos(np.radians(rotate_angle))
            sin = np.sin(np.radians(rotate_angle))
            rotation_mat = [[cos, -sin],
                            [sin, cos]]

            _p = np.matmul(rotation_mat, [pos_x, pos_y])

            # click position in the new image
            new_w, new_h = self.get_im_size_at_angle(rect.im_angle)

            new_p_x = _p[0] + new_w/2
            new_p_y = _p[1] + new_h/2

            # position of the click position to the top left of the rectangle
            new_p_x -= rect.pos_x
            new_p_y -= rect.pos_y

            if new_p_x > 0 and new_p_x < rect.width and new_p_y > 0 and new_p_y < rect.height:
                print('Fall in')


    # Get image size at an arbitrary angle
    def get_im_size_at_angle(self, angle):
        # Since the rectangle is symmetric and we only care about the image size
        _angle = angle
        if angle < 0:
            _angle = 360 + angle
        if abs(_angle) > 180:
            _angle %= 180

        if abs(_angle) < 90:
            w = self.display_im.pixmap_im.width()
            h = self.display_im.pixmap_im.height()
        else:
            w = self.display_im.pixmap_im.height()
            h = self.display_im.pixmap_im.width()
            _angle %= 90

        cos = np.cos(np.radians(_angle))
        sin = np.sin(np.radians(_angle))

        new_w = w*cos + h*sin
        new_h = w*sin + h*cos

        return round(new_w), round(new_h)






# ##################################

def draw_rect(pixmap_img, x, y, w, h, color=QtCore.Qt.green):
    tmp_pixmap = QtGui.QPixmap(pixmap_img)
    # create painter instance with pixmap
    painterInstance = QtGui.QPainter(tmp_pixmap)
    # set rectangle color and thickness
    penRectangle = QtGui.QPen(color)
    penRectangle.setWidth(2)

    # draw rectangle on painter
    painterInstance.setPen(penRectangle)
    painterInstance.drawRect(x, y, w, h)

    return tmp_pixmap


# ##########################

class DisplayImage():
    def __init__(self, im_path, real_rects, wnd_width, show_rect = True):
        self.pixmap_im = QtGui.QPixmap(im_path)
        self.im_scale_ratio = self.pixmap_im.width() / wnd_width

        self.pixmap_im = self.pixmap_im.scaledToWidth(wnd_width)

        self.angle = 0 # current angle of the displaying image (clockwise: positive, anti-clockwise: negative)

        tmp_rects = []
        for rect in real_rects:
            tmp_rect = rect.scale(1/self.im_scale_ratio)
            tmp_rects.append(tmp_rect)

        self.rects = tmp_rects # current rectangle overlay the image

        self.refresh_im(show_rect)

    def refresh_im(self, show_rect=True):
        display_pixmap = QtGui.QPixmap(self.pixmap_im)

        if show_rect:
            for rect in self.rects:
                original_width = display_pixmap.width()
                original_height = display_pixmap.height()

                # Rotate the image following current angle
                display_pixmap = display_pixmap.transformed(QtGui.QTransform().rotate(rect.im_angle),
                                                            QtCore.Qt.SmoothTransformation)

                display_pixmap = draw_rect(display_pixmap, rect.pos_x, rect.pos_y, rect.width, rect.height)

                # Rotate back to the original image
                display_pixmap = display_pixmap.transformed(QtGui.QTransform().rotate(-rect.im_angle),
                                                            QtCore.Qt.SmoothTransformation)

                # Crop to get only the image
                offset_x = (display_pixmap.width() - original_width)/2
                offset_y = (display_pixmap.height() - original_height)/2
                display_pixmap = display_pixmap.copy(offset_x, offset_y, original_width, original_height)

        self.rect_pixmap_im = display_pixmap

    def get_display_im(self):
        rotate_transform = QtGui.QTransform().rotate(self.angle)
        display_pixmap = self.rect_pixmap_im.transformed(rotate_transform, QtCore.Qt.SmoothTransformation)

        return display_pixmap

    def add_rect(self, pos_in_img_x, pos_in_img_y, w, h):
        self.rects.append(Rectangle(pos_in_img_x, pos_in_img_y, w, h, self.angle))
        self.refresh_im()

    # Get rectangles in the real image size
    def get_real_rect(self):
        real_rects = []
        for rect in self.rects:
            # multiply with image scale ratio to get the real position except the angle
            tmp_rect = rect.scale(self.im_scale_ratio)
            real_rects.append(tmp_rect)

        return real_rects

    def del_last_rect(self):
        self.rects = self.rects[:-1]
        self.refresh_im()



# ########################### Browse images in a folder
class ImageBrowser():
    def __init__(self, im_folder_path):
        self.im_folder_path = im_folder_path
        self.im_names = []
        self._current_im_id = 0

        self.init_im_info()

    def init_im_info(self):
        # Get PNG, JPG files
        for ext in ['png', 'jpg']:
            self.im_names += [os.path.basename(im_path) for im_path in glob.glob(self.im_folder_path + '*' + ext)]

        if len(self.im_names) == 0:
            print('Image folder is empty.')

    def get_current_im_name(self):
        return self.im_names[self._current_im_id]
        # return QtGui.QPixmap(self.im_folder_path + self.im_names[self._current_im_id])

    def next_im(self):
        if self._current_im_id < len(self.im_names) - 1:
            self._current_im_id += 1
        else:
            return -1 # End of image list

        return 0

    def prev_im(self):
        if self._current_im_id > 0:
            self._current_im_id -= 1
        else:
            return -1 # at the beginning of the image list

        return 0


# ############################

class AnnotationFileManager:
    def __init__(self, file_path):
        self.file_path = file_path
        self.anns = []

        self.load_data()

    def load_data(self):

        try:
            with open(self.file_path, 'r') as f:
                self.anns = [self.parse_line(line.rstrip()) for line in f]
            # self.anns = f.read().splitlines()
        except:
            return

    def parse_line(self, line_str):
        data = []
        str_list = line_str.split() # image name - x - y - w - h - angle
        if len(str_list) < 6:
            return []

        data.append(str_list[0])
        data.extend(float(x) for x in str_list[1:])

        return data

    def get_im_rects(self, im_name):
        rects = []
        for im_info in self.anns:
            if im_info[0] == im_name:
                rects.append(Rectangle(im_info[1], im_info[2], im_info[3], im_info[4], im_info[5]))

        return rects

    def update_im_rects(self, im_name, rects):
        tmp_anns = [ line for line in self.anns if line[0] != im_name]

        for rect in rects:
            ann = [im_name]
            ann.extend(rect.get_params())
            tmp_anns.append(ann)

        self.anns = tmp_anns

    def save(self):
        with open(self.file_path, 'w') as f:
            for ann in self.anns:
                f.write(' '.join(str(x) for x in ann) + '\n')

# ############################
# Rectangle overlays image
class Rectangle:
    def __init__(self, pos_x, pos_y, width, height, im_angle):
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.width = width
        self.height = height
        self.im_angle = im_angle

    def scale(self, ratio):
        return Rectangle(self.pos_x*ratio, self.pos_y*ratio, self.width*ratio, self.height*ratio, self.im_angle)

    def get_params(self):
        return [self.pos_x, self.pos_y, self.width, self.height, self.im_angle]



# ############################

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())
