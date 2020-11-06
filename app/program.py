import sys, os, platform, time
from PyQt5.QtCore import QThreadPool, QRunnable, pyqtSlot, pyqtSignal, QObject
from dnt_main import *
from dnt_ui import *
from sign_in.db_connection import Database

# TODO: Add a table to server contains userID, computerID, camera_tag, camera_ip, enter_position.
# TODO: Add a scrollable area to profile section that displays IP addresses of Cameras' IPs related to this computer's ID.
class main_program(QObject):
    def __init__(self):
        super(main_program, self).__init__()
        self.video_source = None
        self.ui = Ui_MainWindow()
        self.threadpool = QThreadPool()
        self.threadpool.setMaxThreadCount(8)
        self.database = Database()
        self.combo_list = ["Görüntü kaynağını seçiniz...", "Webcam", "IP Kamera", "IP Kamera 2"]
        self.is_signedin = False

    def button_connections(self):
        # Activate in main.
        self.ui.start_stop_button.clicked.connect(self.Start)
        # self.ui.stop_button.clicked.connect(self.Stop)

        self.ui.to_taskbar_button.clicked.connect(MainWindow.showMinimized)
        self.ui.quit_button.clicked.connect(sys.exit)

        self.ui.btn_page_1.clicked.connect(lambda: self.ui.stackedWidget.setCurrentWidget(self.ui.page_1))

        self.ui.btn_page_2.clicked.connect(lambda: self.ui.stackedWidget.setCurrentWidget(self.ui.page_2))

        self.ui.media_source_combobox.addItems(self.combo_list)
        self.ui.media_source_combobox.activated.connect(self.ComboSelected)
        self.ui.sign_out_button.clicked.connect(self.sign_out_clicked)
        self.ui.sign_in_button.clicked.connect(self.login_func)
        self.ui.reload_table_button.clicked.connect(self.load_report_table)

    @pyqtSlot(QImage)
    def setImage(self, image):
        self.ui.image_frame.setPixmap(QPixmap.fromImage(image))
        if self.detection.stopped:
            self.ui.image_frame.setPixmap(QtGui.QPixmap(":/placeholders/Resources/placeholder2.png"))

    @pyqtSlot(str)
    def setInfo(self, statement):
        self.ui.out_info_box.setText(statement)

    @pyqtSlot(str)
    def setTitleBox(self, statement):
        self.ui.info_title_box.setText(statement)

    def Start(self):
        if self.is_signedin:
            self.ui.out_info_box.setText("")
            if self.check_video_source():
                self.ui.image_frame.setPixmap(QtGui.QPixmap("Resources/please_wait.png"))
                self.detection = Detection()
                self.detection.video_source = self.video_source

                # Connect signals and slots
                self.detection.signals.changeButton.connect(self.change_start_context)
                self.detection.signals.changePixmap.connect(self.setImage)
                self.detection.signals.changeTextBox.connect(self.setInfo)
                self.detection.signals.changeTitleBox.connect(self.setTitleBox)

                self.threadpool.start(self.detection)
                self.change_start_context("stop_button")
            else:
                self.ui.out_info_box.setText("Video kaynağınızı kontrol edin.")
        else:
            self.ui.out_info_box.setText("Lütfen önce giriş yapınız.")

    @pyqtSlot(str)
    def change_start_context(self, mode):
        if mode == "start_button":
            self.ui.start_stop_button.clicked.disconnect()
            self.ui.start_stop_button.clicked.connect(self.Start)
            self.ui.start_stop_button.setStyleSheet("QPushButton {\n"
                                                    "color: rgb(255, 255, 255);\n"
                                                    "border: 0px solid;\n"
                                                    "background-color:  #667BC4;\n"
                                                    "padding:0.5em;\n"
                                                    "font-weight:bold;\n"
                                                    "font-size:12px;\n"
                                                    "}\n"
                                                    "QPushButton:hover {\n"
                                                    "    background-color: #7289DA;\n"
                                                    "}")
            self.ui.start_stop_button.setText("Başlat")

        elif mode == "stop_button":
            self.ui.start_stop_button.clicked.disconnect()
            self.ui.start_stop_button.clicked.connect(self.Stop)
            self.ui.start_stop_button.setStyleSheet("QPushButton {\n"
                                                    "color: rgb(255, 255, 255);\n"
                                                    "border: 0px solid;\n"
                                                    "background-color:  #ff2115;\n"
                                                    "padding:0.5em;\n"
                                                    "font-weight:bold;\n"
                                                    "font-size:12px;\n"
                                                    "}\n"
                                                    "QPushButton:hover {\n"
                                                    "background-color: #ff392e;\n"
                                                    "}")
            self.ui.start_stop_button.setText("Durdur")

    def check_video_source(self):
        if self.video_source is None:
            return False
        else:
            _, frame = cv2.VideoCapture(self.video_source).read()
            if frame is not None:
                return True
            else:
                return False

    # TODO: When loop ends, button context should change.
    def Stop(self):
        try:
            self.detection.stopped = True
            self.threadpool.clear()
            self.threadpool.releaseThread()
            # print("Active thread count last (stop): {}".format(self.threadpool.activeThreadCount()))
            # self.change_start_context("start_button")

        except AttributeError:
            print("Detection is not initialize yet.")

    def ComboSelected(self):
        media_source_str = self.ui.media_source_combobox.currentText()
        current_index = self.ui.media_source_combobox.currentIndex()
        if current_index == 0:
            self.video_source = None
        if current_index == 1:
            self.video_source = 0
        if current_index == 2:
            self.video_source = 'videos/toprakli_fit_buyuk.mp4'
        if current_index == 3:
            self.video_source = "videos/inek_field.mp4"

    ####################################################
    #                    SIGN IN - SIGN OUT            #
    ####################################################

    def starting_page(self):
        """
        This function answer this question: 'Did user sign in before or not?'
        """
        is_matching, file_path = self.database.get_data_n_check()
        if is_matching:
            self.change_profile_button_context(1)
        else:
            try:
                os.remove(file_path)
                self.ui.info_box.setText("Güvenlikle ilgili bir sorun meydana geldi.\nYeniden giriş yapın.")
            except FileNotFoundError:
                print("Usr.md file doesn't exist.")
            self.change_profile_button_context(0)

    def change_profile_button_context(self, status):
        # 0 is for NOT signed in, 1 is for signed in.
        icon = QtGui.QIcon()
        if status == 0:
            self.ui.btn_page_4.disconnect()
            self.ui.btn_page_4.clicked.connect(lambda: self.ui.stackedWidget.setCurrentWidget(self.ui.sign_in_page))
            icon.addPixmap(QtGui.QPixmap(":/icons/Resources/icons/32px/user_alternative.png"), QtGui.QIcon.Normal,
                           QtGui.QIcon.Off)
            self.ui.btn_page_4.setIcon(icon)
            self.is_signedin = False

        elif status == 1:
            self.ui.btn_page_4.disconnect()
            self.ui.btn_page_4.clicked.connect(lambda: self.ui.stackedWidget.setCurrentWidget(self.ui.profile_page))
            icon.addPixmap(QtGui.QPixmap(":/icons/Resources/icons/32px/user_active.png"), QtGui.QIcon.Normal,
                           QtGui.QIcon.Off)
            self.ui.btn_page_4.setIcon(icon)
            self.is_signedin = True
            # cu stands for current user.
            cu_email, cu_name, cu_surname = self.database.get_current_user_info()
            self.ui.current_name_surname.setText("{} {}".format(cu_name, cu_surname))
            self.ui.current_email.setText("{}".format(cu_email))

    def login_func(self):
        self.ui.profile_info_box.setAlignment(QtCore.Qt.AlignCenter)
        if self.ui.email.text() == "" or self.ui.password.text() == "":
            self.ui.info_box.setStyleSheet("color:#ff5048;font-weight: 700;")
            self.ui.info_box.setText("Boş alanları doldurunuz.")
        else:
            encrypted_pass = self.database.encrpt_password(self.ui.password.text())
            email = self.ui.email.text()

            try:
                self.database.cursor.execute(
                    "select name, email, password, userID from User WHERE User.email = %s and User.password=%s"
                    , (email, encrypted_pass))
                x = self.database.cursor.next()
                CURRENT_USER_NAME = x[0]
                CURRENT_USER_EMAIL = x[1]
                CURRENT_USER_ID = x[3]

                # Save user information to local.
                self.save_current_user_local(CURRENT_USER_EMAIL, CURRENT_USER_ID)
                # Change the context and icon of profile button
                self.change_profile_button_context(1)
                # Redirecting to page 2.
                self.ui.stackedWidget.setCurrentWidget(self.ui.profile_page)
                # Complete message.
                self.ui.profile_info_box.setText(f"Giriş başarılı.")

            except StopIteration:
                self.ui.info_box.setStyleSheet("color:#ff5048; font-weight: 700;")
                self.ui.info_box.setText("E-postanız veya parolanız yanlış.")

    def save_current_user_local(self, email, uid):
        file_exist_message = "Old user. [File exist]"
        # Get OS of user.
        platform_name = platform.system()

        if platform_name == "Windows":
            save_dir = os.getenv('APPDATA')
            save_dir += '\\Provactus\\'
            file_path = save_dir + '\\usr.md'

        elif platform_name == "Linux":
            save_dir = '/var/Provactus'
            file_path = '/var/Provactus/usr.md'

        # Trying to create file.
        try:
            os.mkdir(save_dir)
        except FileExistsError:
            print(file_exist_message)
        # Local registry for following usages.
        with open(file_path, 'w+') as file:
            file.write(f"{uid}\n{email}\n")

    def sign_out_clicked(self):
        # Get OS of user.
        platform_name = platform.system()
        if platform_name == "Windows":
            save_dir = os.getenv('APPDATA')
            save_dir += '\\Provactus\\'
            file_path = save_dir + '\\Provactus\\usr.md'

        elif platform_name == "Linux":
            file_path = "/var/Provactus/usr.md"

        os.remove(file_path)
        self.change_profile_button_context(0)
        # Redirecting to page 2.
        self.ui.stackedWidget.setCurrentWidget(self.ui.sign_in_page)
        self.ui.info_box.setText("")

    ####################################################
    #                   Report                         #
    ####################################################
    def load_report_table(self):

        if self.is_signedin:
            t = datetime.now()
            current_time = t.strftime("%d/%m/%y %H:%M:%S.%f")[:-4]
            self.report_page_controls(True)
            self.ui.report_info_box.setText("Son güncellenme tarihi: {}".format(current_time))
            # To update the information, we have to re-initialize the db.
            self.database = Database()
            (report_id, date, elapsed, total_left, total_right, user_id, enter_position) = self.database.get_reports(
                self.database.get_id_local())
            var_collection = [date, elapsed, total_left, total_right]
            var_collection_rev = [date, elapsed, total_right, total_right]

            # reverse vars
            for var in var_collection:
                var.reverse()
            # listing
            if len(report_id) != 0:
                self.ui.report_table.setRowCount(len(report_id))

                for col_n in range(4):
                    for row_n in range(len(report_id)):
                        if enter_position[row_n] == "right":
                            self.ui.report_table.setItem(row_n, col_n,
                                                         QtWidgets.QTableWidgetItem(str(var_collection[col_n][row_n])))
                        elif enter_position[row_n] == "left":
                            self.ui.report_table.setItem(row_n, col_n,
                                                         QtWidgets.QTableWidgetItem(
                                                             str(var_collection_rev[col_n][row_n])))

            else:
                self.report_page_controls(False)
                self.ui.report_info_box.setText("Henüz rapor oluşturmadınız.")
        else:
            self.report_page_controls(False)
            self.ui.report_info_box.setText("Önce giriş yapınız.")

    def report_page_controls(self, is_okay):
        self.ui.report_info_box.setAlignment(QtCore.Qt.AlignCenter)
        if is_okay is True:

            self.ui.report_info_box.setStyleSheet("color: #FFFFFF;\n"
                                                  "font-weight: 700;\n"
                                                  "font-size: 14px;\n"
                                                  "margin:2em;\n"
                                                  "")
            self.ui.report_table.show()
            self.ui.report_info_box.setText("")
        else:
            self.ui.report_info_box.setStyleSheet("color: #ff5048;\n"
                                                  "font-weight: 700;\n"
                                                  "font-size: 14px;\n"
                                                  "margin:2em;\n"
                                                  "")
            self.ui.report_table.close()
            self.ui.report_info_box.show()

    ####################################################
    #                   PROFILE                        #
    ####################################################

    # Todo: Create profile section


exe = main_program()
app = QtWidgets.QApplication(sys.argv)
MainWindow = QtWidgets.QMainWindow()
exe.ui.setupUi(MainWindow)
# invoking start functions
exe.button_connections()
exe.starting_page()
exe.load_report_table()
# Deleting frames
MainWindow.setWindowFlags(QtCore.Qt.FramelessWindowHint)
MainWindow.showFullScreen()

sys.exit(app.exec_())
