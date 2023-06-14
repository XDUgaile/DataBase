from threading import Thread

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtWidgets import QWidget, QHeaderView, QAbstractItemView, QTableWidgetItem, QMessageBox, QMenu, QAction
from ui.book_borrow_info_window import Ui_Form
from util.dbutil import DBHelp
from util.common_util import BORROW_STATUS_MAP, SYS_STYLE, SEARCH_CONTENT_MAP, msg_box, RETURN, DELAY_TIME, accept_box, \
    DELETE_ICON, PUSH_RETURN, get_current_time
from view.renew_window import RenewWindow
from view.ask_return_window import AskReturnWindow


class BorrowInfoWindow(Ui_Form, QWidget):
    init_data_done_signal = pyqtSignal(list)
    return_book_done_signal = pyqtSignal()

    def __init__(self, user_role=None, username=None):
        super(BorrowInfoWindow, self).__init__()
        self.setupUi(self)
        self.user_role = user_role
        self.username = username
        self.renew_win = None
        self.borrow_info_list = list()
        self.init_data_done_signal.connect(self.show_info)
        self.refresh_pushButton.clicked.connect(self.init_data)
        self.search_borrow_user_pushButton.clicked.connect(self.search_borrow_info)
        self.tableWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tableWidget.customContextMenuRequested.connect(self.generate_menu)
        self.return_flag = []
        self.borrow_info_id = []
        self.init_ui()
        self.init_data()

    def generate_menu(self, pos):
        row_num = -1
        for i in self.tableWidget.selectionModel().selection().indexes():
            row_num = i.row()
        if row_num == -1:
            return
        if self.user_role == '普通用户':
            menu = QMenu()
            return_action = QAction(u'还书')
            return_action.setIcon(QIcon(RETURN))
            menu.addAction(return_action)

            delay_borrow_action = QAction(u'续借')
            delay_borrow_action.setIcon(QIcon(DELAY_TIME))
            menu.addAction(delay_borrow_action)

            # 如果当前条目为已还则菜单栏为不可点击状态
            if self.return_flag[row_num] == 1:
                return_action.setEnabled(False)
                delay_borrow_action.setEnabled(False)
            action = menu.exec_(self.tableWidget.mapToGlobal(pos))

            if action == return_action:
                if accept_box(self, '提示', '确实归还当前书本吗？') == QMessageBox.Yes:
                    th = Thread(target=self.return_book, args=(self.borrow_info_id[row_num],))
                    th.start()

            if action == delay_borrow_action:
                self.renew_win = RenewWindow(borrow_id=self.borrow_info_id[row_num])
                self.renew_win.show()
        else:
            menu = QMenu()
            del_record_action = QAction(u'删除记录')
            del_record_action.setIcon(QIcon(DELETE_ICON))
            menu.addAction(del_record_action)

            ask_return_action = QAction(u'催还')
            ask_return_action.setIcon(QIcon(PUSH_RETURN))
            menu.addAction(ask_return_action)

            # 根据是否已经归还来判断菜单是否为可点击状态
            if self.return_flag[row_num] == 1:
                ask_return_action.setEnabled(False)
            else:
                del_record_action.setEnabled(False)

            action = menu.exec_(self.tableWidget.mapToGlobal(pos))

            if action == del_record_action:
                rep = accept_box(self, '警告', '确定删除该条记录吗?')
                if rep == QMessageBox.Yes:
                    pass

            if action == ask_return_action:
                index = self.tableWidget.currentRow()
                borrow_id = self.borrow_info_id[index]
                borrow_user = self.tableWidget.item(index, 0).text()
                self.ask_win = AskReturnWindow(data=[borrow_user, borrow_id, 0, get_current_time()])
                self.ask_win.show()

    def return_book(self, borrow_id):
        db = DBHelp()
        db.update_borrow_statue(borrow_id)
        db.db_commit()
        db.instance = None
        del db
        self.init_data()

    def search_borrow_info(self):
        if self.borrow_user_search_lineEdit.text() == '':
            msg_box(self, '提示', '请输入需要搜索的内容!')
            return
        if self.user_role == '管理员':
            search_type = self.comboBox.currentText()
            search_content = self.borrow_user_search_lineEdit.text()
            db = DBHelp()
            count, res = db.query_super(table_name='borrow_info', column_name=SEARCH_CONTENT_MAP.get(search_type),
                                        condition=search_content)
            if count == 0:
                msg_box(widget=self, title='提示', msg='未找到相关记录!')
                return
            self.get_data_from_database(db, res=res)

    def init_ui(self):
        self.setWindowFlags(Qt.WindowCloseButtonHint)
        self.setStyleSheet(SYS_STYLE)
        self.refresh_pushButton.setProperty('class', 'Aqua')
        self.search_borrow_user_pushButton.setProperty('class', 'Aqua')
        self.refresh_pushButton.setMinimumWidth(60)
        self.search_borrow_user_pushButton.setMinimumWidth(60)
        self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tableWidget.setEditTriggers(QAbstractItemView.NoEditTriggers)

    def init_data(self):
        self.borrow_user_search_lineEdit.clear()
        th = Thread(target=self.book_info_th)
        th.start()

    def show_info(self, infos):
        for i in range(self.tableWidget.rowCount()):
            self.tableWidget.removeRow(0)
        for info in infos:
            self.tableWidget.insertRow(self.tableWidget.rowCount())
            for i in range(len(info)):
                item = QTableWidgetItem(str(info[i]))
                if info[i] == '未还':
                    item.setBackground(QColor('#ff3333'))
                if info[i] == '已还':
                    item.setBackground(QColor('#33ff33'))
                self.tableWidget.setItem(self.tableWidget.rowCount() - 1, i, item)

        for i in range(self.tableWidget.rowCount()):
            for j in range(self.tableWidget.columnCount()):
                item = self.tableWidget.item(i, j)
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignHCenter)

    def book_info_th(self):
        if self.user_role == '管理员':
            db = DBHelp()
            count, res = db.query_all(table_name='borrow_info')
            self.get_data_from_database(db, res)
        else:
            db = DBHelp()
            count, res = db.query_super(table_name='borrow_info', column_name='borrow_user', condition=self.username)
            self.get_data_from_database(db, res)

    def get_data_from_database(self, db, res):
        self.return_flag = []
        self.borrow_info_id = []
        self.borrow_info_list.clear()
        for record in res:
            book_id = record[1]
            self.borrow_info_id.append(record[0])
            count, book_info = db.query_super(table_name='book', column_name='id', condition=book_id)
            sub_info = [record[3], record[2], book_info[0][3], book_info[0][-1], record[4], str(record[6]),
                        str(record[7]), BORROW_STATUS_MAP.get(str(record[-2]))]
            self.return_flag.append(record[-2])
            self.borrow_info_list.append(sub_info)
        self.init_data_done_signal.emit(self.borrow_info_list)
