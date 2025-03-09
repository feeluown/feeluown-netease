import hashlib
import json
import logging
import os

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (QVBoxLayout, QLineEdit,
                             QDialog, QPushButton,
                             QLabel)
from feeluown.gui.widgets.login import (
    CookiesLoginDialog as _CookiesLoginDialog, InvalidCookies,
)

from .login_controller import LoginController
from .provider import provider
from .consts import USER_PW_FILE

logger = logging.getLogger(__name__)


class LoginDialog(QDialog):
    login_success = pyqtSignal([object])

    def __init__(self, verify_captcha, verify_userpw, create_user,
                 parent=None):
        super().__init__(parent)

        self.verify_captcha = verify_captcha
        self.verify_userpw = verify_userpw
        self.create_user = create_user

        self.is_encrypted = False
        self.captcha_needed = False
        self.captcha_id = 0

        self.notes1_label = QLabel(
            '<h3>支持两种登录方式</h3>\n'
            '<li>第一种方式是直接读取浏览器 cookies 来登录，这时你需要确保浏览器已经登录。推荐！</li>',
            self
        )
        self.notes2_label = QLabel(
            '<li>第二种是使用账号密码登录，请填入账号和密码。'
            '当你的账号名是手机号时，你需要注意区号是否正确。'
            '如果你的账号名是邮箱，则可以忽略区号。</li>',
            self
        )
        self.notes1_label.setWordWrap(True)
        self.notes2_label.setWordWrap(True)
        self.notes1_label.setTextFormat(Qt.RichText)
        self.notes2_label.setTextFormat(Qt.RichText)

        self.setMaximumWidth(400)
        self.country_code_input = QLineEdit(self)
        self.username_input = QLineEdit(self)
        self.pw_input = QLineEdit(self)
        self.pw_input.setEchoMode(QLineEdit.Password)
        # self.remember_checkbox = FCheckBox(self)
        self.captcha_label = QLabel(self)
        self.captcha_label.hide()
        self.captcha_input = QLineEdit(self)
        self.captcha_input.hide()
        self.hint_label = QLabel(self)
        self.ok_btn = QPushButton('登录', self)
        self.cookies_login_btn = QPushButton('读取浏览器 cookies 登录', self)
        self._layout = QVBoxLayout(self)

        self.country_code_input.setPlaceholderText('国际电话区号（默认为86）')
        self.username_input.setPlaceholderText('网易邮箱或者手机号')
        self.pw_input.setPlaceholderText('密码')

        self.pw_input.textChanged.connect(self.dis_encrypt)
        self.ok_btn.clicked.connect(self.login)
        self.cookies_login_btn.clicked.connect(self.show_cookies_login_dialog)

        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._layout.addWidget(self.notes1_label)
        self._layout.addWidget(self.cookies_login_btn)
        self._layout.addStretch(0)
        self._layout.addSpacing(20)
        self._layout.addWidget(self.notes2_label)
        self._layout.addWidget(self.country_code_input)
        self._layout.addWidget(self.username_input)
        self._layout.addWidget(self.pw_input)
        self._layout.addWidget(self.captcha_label)
        self._layout.addWidget(self.captcha_input)
        self._layout.addWidget(self.hint_label)
        # self._layout.addWidget(self.remember_checkbox)
        self._layout.addWidget(self.ok_btn)

    def fill(self, data):
        self.country_code_input.setText(data.get('country_code'))
        self.username_input.setText(data['username'])
        self.pw_input.setText(data['password'])
        self.is_encrypted = True

    def show_cookies_login_dialog(self):
        self._dialog = CookiesLoginDialog('https://music.163.com', ['MUSIC_U'])
        self._dialog.login_succeed.connect(self.on_login_succeed)
        self._dialog.show()
        self._dialog.autologin()
        self.hide()

    def on_login_succeed(self):
        try:
            del self._dialog
        except:  # noqa
            pass
        # 理论上，这里肯定不会触发 IO 请求。
        self.login_success.emit(provider.get_current_user())
        self.hide()

    def show_hint(self, text):
        self.hint_label.setText(text)

    @property
    def data(self):
        country_code = self.country_code_input.text()
        username = self.username_input.text()
        pw = self.pw_input.text()
        if self.is_encrypted:
            password = pw
        else:
            password = hashlib.md5(pw.encode('utf-8')).hexdigest()
        d = dict(country_code=country_code, username=username, password=password)
        return d

    def captcha_verify(self, data):
        self.captcha_needed = True
        self.captcha_id = data['captcha_id']
        self.captcha_input.show()
        self.captcha_label.show()
        # FIXME: get pixmap from url
        # self._app.pixmap_from_url(url, self.captcha_label.setPixmap)

    def dis_encrypt(self, text):
        self.is_encrypted = False

    def login(self):
        if self.captcha_needed:
            captcha = str(self.captcha_input.text())
            captcha_id = self.captcha_id
            data = self.verify_captcha(captcha_id, captcha)
            if data['code'] == 200:
                self.captcha_input.hide()
                self.captcha_label.hide()
            else:
                self.captcha_verify(data)

        user_data = self.data
        self.show_hint('正在登录...')
        data = self.verify_userpw(user_data['country_code'],
                                  user_data['username'],
                                  user_data['password'])
        message = data['message']
        self.show_hint(message)
        if data['code'] == 200:
            self.save_user_pw(user_data)
            user = self.create_user(data)
            self.login_success.emit(user)
            self.hide()
        elif data['code'] == 415:
            self.captcha_verify(data)

    def save_user_pw(self, data):
        with open(USER_PW_FILE, 'w+') as f:
            if f.read() == '':
                d = dict()
            else:
                d = json.load(f)
            d['default'] = data['username']
            d[d['default']] = data
            json.dump(d, f, indent=4)

        logger.info('save username and password to %s' % USER_PW_FILE)

    def load_user_pw(self):
        if not os.path.exists(USER_PW_FILE):
            return
        with open(USER_PW_FILE, 'r') as f:
            d = json.load(f)
            data = d[d['default']]
        self.country_code_input.setText(data.get('country_code'))
        self.username_input.setText(data['username'])
        self.pw_input.setText(data['password'])
        self.is_encrypted = True

        logger.info('load username and password from %s' % USER_PW_FILE)


class CookiesLoginDialog(_CookiesLoginDialog):

    def setup_user(self, user):
        provider.auth(user)

    async def user_from_cookies(self, cookies):
        try:
            user = provider.get_user_from_cookies(cookies)
        except ValueError as e:
            raise InvalidCookies(str(e))
        return user

    def load_user_cookies(self):
        user = LoginController.load()
        if user is not None:
            cookies, exists = user.cache_get('cookies')
            assert exists
            return cookies
        return None

    def dump_user_cookies(self, user, cookies):
        LoginController.save(user)
