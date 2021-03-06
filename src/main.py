"""
Config Example
==============
This file contains a simple example of how the use the Kivy settings classes in
a real app. It allows the user to change the caption and font_size of the label
and stores these changes.
When the user next runs the programs, their changes are restored.
"""

import asyncio
import json
import ntpath
import os
import re
import select
import shutil
import socket
import textwrap
import threading
import time
import traceback
import uuid
from contextlib import closing
from os.path import dirname, exists, join
from urllib.parse import quote

from jnius import autoclass
from kivy.app import App
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.uix.popup import Popup
from kivy.uix.settings import SettingsWithTabbedPanel
from kivy.utils import platform
from oscpy.client import send_message
from oscpy.server import OSCThreadServer
from toast import toast

if platform == "android":
    from android.permissions import request_permissions, Permission
    request_permissions([Permission.INTERNET, Permission.READ_EXTERNAL_STORAGE,
                         Permission.WRITE_EXTERNAL_STORAGE])


def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


# We first define our GUI
kv = '''
BoxLayout:
    orientation: 'vertical'
    size_hint: (1,1)
    spacing: dp(10)
    halign: 'center'
    AnchorLayout:
        Button:
            text: 'Configure app (or press F1)'
            on_release: app.open_settings()
            size_hint_x: 0.8
            size_hint_y: None
            halign: 'center'
            height: dp(70)
    AnchorLayout:
        Button:
            id: okbtn
            text: 'Go'
            on_release: app.go()
            size_hint_x: 0.8
            size_hint_y: None
            halign: 'center'
            height: dp(70)
    AnchorLayout:
        Button:
            id: exitbtn
            size_hint_x: 0.8
            size_hint_y: None
            height: dp(70)
            halign: 'center'
            text: 'Exit'
            on_release: app.quit_all()
'''

Builder.load_string('''
#:import RV RV.RV
<MyPopup>:
    auto_dismiss: True
    BoxLayout:
        orientation: 'vertical'
        RV:
            id: idrv
            size_hint: (1, .7)
        Button:
            id: okbtn
            text: 'Go'
            on_release: root.go()
            size_hint: (1, .15)
        Button:
            id: exitbtn
            text: 'Exit'
            on_release: root.dismiss()
            size_hint: (1, .15)
''')

ACTION_RESULT_SH = 'kyvidevdl.result.sh'


class MyPopup(Popup):

    def __init__(self, *args, **kwargs):
        self.register_event_type('on_go')
        super(MyPopup, self).__init__(*args, **kwargs)

    def on_go(self, urls, device_info):
        pass

    def go(self):
        Logger.info("outlist = " + str(self.ids.idrv.data))
        urls = []
        device = dict()
        for sh in self.ids.idrv.data:
            if sh["sel"]:
                device = dict(name=sh['dname'], name2=sh['dname2'], type=sh['dtype'])
                lnk = f'udp://{sh["host"]}:{sh["udpport"]}/{quote(sh["msg"])}'
                urls.append(dict(
                    name=sh['name'],
                    img=sh['ico'],
                    link=lnk
                ))
        self.dismiss()
        self.dispatch('on_go', urls, device)

    def open(self, data, *args, **kwargs):
        self.ids.idrv.data = data
        super(MyPopup, self).open(*args, **kwargs)


class MyApp(App):

    def on_popup_dismiss(self, *args, **kwargs):
        self.popup = None

    def on_go(self, inst, shs, device_info):
        device = self.config.get("device", "device")
        shtemp = self.config.get("device", "shname")
        parts = device.split('/')
        shtemp = shtemp.replace('$p0$', parts[0])
        shtemp = shtemp.replace('$p1$', parts[1] if len(parts) > 1 else '')
        shtemp = shtemp.replace('  ', ' ').replace('__', '_').replace(' - - ', ' - ')
        if platform == 'win':
            outjson = {
                "categories": [
                    {
                        "id": "fdeb3bb8-ae8e-4660-99c5-42420d142580",
                        "name": "Scorciatoie",
                        "shortcuts": [],
                    }
                ],
                "version": 40
            }
            urls = outjson['categories'][0]['shortcuts']
            try:
                os.mkdir('outimages')
            except OSError:
                pass
            for sh in shs:
                imfn = join('outimages', str(uuid.uuid4()) + '.png')
                shutil.copy2(sh['img'], imfn)
                url = dict(
                    id=str(uuid.uuid4()),
                    iconName=f'outimages/{ntpath.basename(imfn)}',
                    name=sh['name'],
                    executionType="scripting",
                    description=shtemp.replace('$sh$', sh['name']),
                    codeOnPrepare='sendIntent({"action":"android.intent.action.SENDTO","type":"activity","dataUri":"%s"});' % sh['link']
                )
                urls.append(url)
            if len(urls):
                with open(device.replace('/', ' - ') + ' - sh.json', 'w') as outfile:
                    outfile.write(json.dumps(outjson, indent=4))
        else:
            send_message(
                '/request',
                (json.dumps(dict(
                    shs=shs,
                    sh_device=device.replace('/', ' - ') + ' - ',
                    sh_temp=shtemp,
                    device_info=device_info,
                    network_info=dict(
                        host=self.config.get('network', 'host'),
                        tcpport=int(self.config.get('network', 'tcpport')),
                        udpport=int(self.config.get('network', 'udpport'))
                    )
                )),),
                '127.0.0.1',
                self.port_osc_service,
                encoding='utf8'
            )

    @staticmethod
    def init_map():
        if platform == "android":
            Color = autoclass("android.graphics.Color")
            MyApp.COLOR_MAP = {
                "Green": Color.GREEN,
                "Red": Color.RED,
                "Yellow": Color.YELLOW,
                "Blue": Color.BLUE,
                "Magenta": Color.MAGENTA}
        else:
            MyApp.COLOR_MAP = {
                "Green": (0, 255, 0),
                "Red": (255, 0, 0),
                "Yellow": (240, 255, 0),
                "Blue": (0, 0, 255),
                "Magenta": (255, 0, 255)}

    def build(self):
        """
        Build and return the root widget.
        """
        # The line below is optional. You could leave it out or use one of the
        # standard options, such as SettingsWithSidebar, SettingsWithSpinner
        # etc.
        self.settings_cls = SettingsWithTabbedPanel

        # We apply the saved configuration settings or the defaults
        root = Builder.load_string(kv)
        icpth = self.default_icon_path()
        if icpth:
            self.config.set("graphics", "icons", icpth)
        self.port_osc = find_free_port()
        if platform == 'android':
            self.port_osc_service = find_free_port()
        self.osc = OSCThreadServer(encoding='utf8')
        self.osc.listen(address='127.0.0.1', port=self.port_osc, default=True)
        self.osc.bind('/dl_finish', self.dl_process)
        self.osc.bind('/sh_put', self.on_sh_put)
        self.popup = None
        return root

    def on_sh_put(self, msg):
        Logger.info(f'Processed received {msg}')
        m = json.loads(msg)
        if m:
            toast(f"Shortucut {m['name']} placed")
        else:
            toast('Launcher does not support pinned shortcuts')

    def on_keyboard(self, win, scancode, *largs):
        if scancode == 27:
            if self.popup:
                self.popup.dismiss()
            else:
                self.quit_all()

    def quit_all(self):
        if platform == "android":
            send_message(
                '/quit',
                (1,),
                '127.0.0.1',
                self.port_osc_service,
                encoding='utf8'
            )
        self.stop()

    def on_start(self):
        Logger.info(f"config file is {self.get_application_config()}")
        if platform == "android":
            from kivy.core.window import Window
            from jnius import autoclass
            Window.bind(on_keyboard=self.on_keyboard)
            package_name = 'org.kivymfz.devicedl'
            service_name = 'ShortcutService'
            service_class = '{}.Service{}'.format(package_name, service_name.title())
            service = autoclass(service_class)
            mActivity = autoclass('org.kivy.android.PythonActivity').mActivity
            arg = dict(port_to_bind=self.port_osc_service,
                       port_to_send=self.port_osc)
            argument = json.dumps(arg)
            Logger.info("Starting %s [%s]" % (service_class, argument))
            service.start(mActivity, argument)

    def default_icon_path(self):
        try:
            icpth = self.config.get("graphics", "icons")
        except Exception:
            icpth = None
            traceback.print_exc()
        if not icpth or not os.path.isdir(icpth):
            if platform == "android":
                Environment = autoclass('android.os.Environment')
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                icpth2 = PythonActivity.mActivity.getExternalFilesDir(
                    Environment.DIRECTORY_PICTURES).getAbsolutePath()
            else:
                icpth2 = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            if icpth != icpth2:
                return icpth2
        return None

    def build_config(self, config):
        """
        Set the default values for the configs sections.
        """
        config.setdefaults('network', {'host': '192.168.1.1', 'tcpport': 10001, 'udpport': 10000, 'mqttport': 8913})
        config.setdefaults('device', {'device': '', 'shname': '$p0$_$p1$_$sh$'})
        config.setdefaults('params', {'home': 'Home'})
        icpth = self.default_icon_path()
        if icpth:
            config.setdefaults('graphics', {'icons': icpth, 'color': 'Magenta'})

    def dl_process(self, msg):
        m = json.loads(msg)
        if 'error' in msg:
            toast("Error in dl: " + m['error'])
        elif 'obj' in msg:
            Logger.debug(m['obj'])
            if len(m['obj']) and len(m['title']):
                self.popup = MyPopup(title=m['title'], on_go=self.on_go, on_dismiss=self.on_popup_dismiss)
                self.popup.open(m['obj'])
            else:
                toast("\n".join(
                      textwrap.wrap(
                          "No matching devices found (" + self.config.get("device", "device") + "). Available filters: " + str(m['filters']), width=60)),
                      True)

        self.root.ids.okbtn.disabled = False

    def build_settings(self, settings):
        """
        Add our custom section to the default configuration object.
        """
        # We use the string defined above for our JSON, but it could also be
        # loaded from a file as follows:
        #     settings.add_json_panel('My Label', self.config, 'settings.json')
        dn = dirname(__file__)
        settings.add_json_panel('Settings', self.config, join(dn, 'settings.json'))  # data=json)

    def on_config_change(self, config, section, key, value):
        """
        Respond to changes in the configuration.
        """
        Logger.info("main.py: App.on_config_change: {0}, {1}, {2}, {3}".format(
            config, section, key, value))

    def close_settings(self, settings=None):
        """
        The settings panel has been closed.
        """
        Logger.info("main.py: App.close_settings: {0}".format(settings))
        super(MyApp, self).close_settings(settings)

    def alter_server_obj(self, o):
        devices = []
        devs = o["action"]["hosts"]
        for _, d in devs.items():
            if 'sh' in d:
                ll = dict()
                for k in d['sh']:
                    sh = k.split(':')[0]
                    ll[sh + ':1'] = 1
                d['sh'] = list(ll.keys())
            if 'dir' in d:
                ll = list()
                for k in d['dir']:
                    sh = k.split(':')
                    ll.append(sh[0] + ':' + sh[1] + ':1')
                d['dir'] = ll
            devices.append(d)
        return devices

    def log(self, m):
        print(m)

# https://stackoverflow.com/questions/45830039/kivy-python-multiple-widgets-in-recycleview-row

    def define_sh(self, dev, shnm, msg):
        mo = re.search("^@[a-z]_([0-9]+)_(.*)", shnm)
        if mo:
            shnm = "@" + mo.group(1) + "_" + mo.group(2)
        fico = self.config.get("graphics", "icons") + '/'
        generated = fico + "generated/"
        try:
            os.mkdir(generated)
        except Exception:
            pass
        tp = dev["type"][6:].lower()
        Logger.debug("TP = " + tp)
        col = self.config.get("graphics", "color")
        fom = ""
        try:
            if tp == "rm" or tp == "allone" or tp == "ct10" or\
                    tp == "upnpirta2" or tp == "upnpirrc" or tp == "samsungctl":
                if shnm[0] == "@":
                    shnm = shnm[1:]
                mo = re.search("^([^0-9]+)[0-9]+([\\-\\+])$", shnm)
                if mo:
                    iconm = mo.group(1) + mo.group(2)
                else:
                    iconm = shnm
                iconm = iconm.lower()
                Logger.debug("Searching " + dev["name"] + ":" + shnm)
                fom1 = fico + iconm + "_ac.png"
                fom2 = fico + iconm + ".png"
                fom3 = generated + iconm + "_" + col + ".png"
                fim = fico + tp + ".png"
                if not os.path.isfile(fom1) and not os.path.isfile(fom2):
                    Logger.debug("Not found " + dev["name"] + ":" + iconm)
                    mo = re.search("^([0-9]+)_", iconm)

                    if mo:
                        nums = mo.group(1)
                        fom = generated + nums + "_" + col + ".png"
                        Logger.debug("Creating " + fom)
                        self.createImageText(nums, MyApp.COLOR_MAP[col], fom)
                    elif os.path.isfile(fim):
                        fom = generated + tp + "_" + col + ".png"
                        Logger.debug("Creating " + fom)
                        self.changeImageColor(fim, MyApp.COLOR_MAP[col], fom)
                elif os.path.isfile(fom1):
                    fom = fom1
                elif os.path.isfile(fom3):
                    fom = fom3
                else:
                    fom = fom3
                    Logger.debug("Creating " + fom)
                    self.changeImageColor(fom2, MyApp.COLOR_MAP[col], fom)
            elif tp == "s20" or tp == "tasmotaswitch" or (tp == "primelan" and (dev["subtype"] == 2 or dev["subtype"] == 0)):
                col = "Green" if shnm == "ON" else "Red"
                fim = fico + tp + ".png"
                fom = generated + tp + "_" + col + ".png"
                Logger.debug("Creating " + fom)
                self.changeImageColor(fim, MyApp.COLOR_MAP[col], fom)
            elif tp == "virtual" or (tp == "primelan" and dev["subtype"] == 1):
                fom = generated + shnm + "_" + col + ".png"
                Logger.debug("Creating " + fom)
                self.createImageText(shnm, MyApp.COLOR_MAP[col], fom)
        except Exception:
            fom = ""
            traceback.print_exc()
        return dict(ico=fico + 'default.png' if not len(fom) or not os.path.isfile(fom) else fom,
                    dname=dev["name"], dname2=dev["name2"], name=shnm, msg=msg, sel=False,
                    dtype=dev["type"], host=self.config.get('network', 'host'),
                    udpport=int(self.config.get('network', 'udpport')))

    def createImageText(self, txt, col, fom):
        if not os.path.isfile(fom):
            if platform == "android":
                FileOutputStream = autoclass("java.io.FileOutputStream")
                Bitmap = autoclass("android.graphics.Bitmap")
                BitmapConfig = autoclass("android.graphics.Bitmap$Config")
                BitmapCompressFormat = autoclass("android.graphics.Bitmap$CompressFormat")
                Canvas = autoclass("android.graphics.Canvas")
                # PorterDuff = autoclass("android.graphics.PorterDuff")
                PorterDuffMode = autoclass("android.graphics.PorterDuff$Mode")
                Paint = autoclass("android.graphics.Paint")
                PaintAlign = autoclass("android.graphics.Paint$Align")
                Color = autoclass("android.graphics.Color")
                paint = Paint(Paint.ANTI_ALIAS_FLAG)
                paint.setTextSize(55)
                paint.setColor(col)
                paint.setTextAlign(PaintAlign.LEFT)
                baseline = -paint.ascent()  # ascent() is negative
                width = round(paint.measureText(txt))  # round
                height = round(baseline + paint.descent())
                image = Bitmap.createBitmap(width, height, BitmapConfig.ARGB_8888)
                canvas = Canvas(image)
                canvas.drawColor(Color.TRANSPARENT, PorterDuffMode.CLEAR)
                canvas.drawText(txt, 0, baseline, paint)
                image.compress(BitmapCompressFormat.PNG, 100, FileOutputStream(fom))
            else:
                from PIL import Image, ImageDraw, ImageFont
                img = Image.new('RGBA', (128, 128), (255, 0, 0, 0))

                d = ImageDraw.Draw(img)
                fnt = ImageFont.truetype("arial", 50)
                d.text((18, 18), txt, fill=col, font=fnt)

                img.save(fom)

    def changeImageColor(self, fim, col, fom):
        if not os.path.isfile(fom):
            if platform == "android":
                FileOutputStream = autoclass("java.io.FileOutputStream")
                BitmapFactory = autoclass("android.graphics.BitmapFactory")
                BitmapFactoryOptions = autoclass("android.graphics.BitmapFactory$Options")
                # BitmapConfig = autoclass("android.graphics.Bitmap$Config")
                BitmapCompressFormat = autoclass("android.graphics.Bitmap$CompressFormat")
                Canvas = autoclass("android.graphics.Canvas")
                PorterDuffMode = autoclass("android.graphics.PorterDuff$Mode")
                Paint = autoclass("android.graphics.Paint")
                PorterDuffColorFilter = autoclass("android.graphics.PorterDuffColorFilter")
                options = BitmapFactoryOptions()
                options.inMutable = True
                # declaredField = options.getClass().getDeclaredField("inPreferredConfig")
                # declaredField.set(cast('java.lang.Object',options), cast('java.lang.Object', BitmapConfig.ARGB_8888))
                # options.inPreferredConfig = BitmapConfig.ARGB_8888;
                bm = BitmapFactory.decodeFile(fim, options)
                paint = Paint()
                filterv = PorterDuffColorFilter(col, PorterDuffMode.SRC_IN)
                paint.setColorFilter(filterv)
                canvas = Canvas(bm)
                canvas.drawBitmap(bm, 0, 0, paint)
                bm.compress(BitmapCompressFormat.PNG, 100, FileOutputStream(fom))
            else:
                from PIL import Image
                import numpy as np
                im = Image.open(fim)
                im = im.convert('RGBA')
                np.array(im)
                data = np.array(im)   # "data" is a height x width x 4 numpy array
                red, green, blue, alpha = data.T  # Temporarily unpack the bands for readability

                # Replace white with red... (leaves alpha values alone...)
                white_areas = (red == 255) & (blue == 255) & (green == 255)
                data[..., :-1][white_areas.T] = col  # Transpose back needed

                im2 = Image.fromarray(data)
                im2.save(fom)

    def _get_user_data_dir(self):
        # Determine and return the user_data_dir.
        if platform == 'android':
            from jnius import autoclass, cast
            Environment = autoclass('android.os.Environment')
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            ctx = PythonActivity.mActivity
            strg = ctx.getExternalFilesDirs(None)
            if strg:
                dest = strg[0]
                for f in strg:
                    if Environment.isExternalStorageRemovable(f):
                        dest = f
                        break
                data_dir = dest.getAbsolutePath()
            else:
                file_p = cast('java.io.File', ctx.getFilesDir())
                data_dir = file_p.getAbsolutePath()
            if not exists(data_dir):
                os.mkdir(data_dir)
            return data_dir
        else:
            super(MyApp, self)._get_user_data_dir()

    def dl_devices(self, *args):

        # Connect the socket to the port where the server is listening
        stringall = b''
        obj = None
        for _ in range(3):
            lastex = None
            sock = None
            stringall = b''
            obj = None
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                # sock.settimeout(self.timeout)
                sock.connect((self.config.get('network', 'host'),
                              int(self.config.get('network', 'tcpport'))))
                sock.setblocking(0)
                sock.settimeout(5000)
                sock.send(b"@7 devicedl\n")
                now = time.time()
                idx = -1
                while time.time() - now < 10:
                    ready = select.select([sock], [sock], [], 0.5)
                    if ready[0]:
                        data = sock.recv(4096)
                        if not data:
                            raise Exception('Conection closed')
                        else:
                            Logger.debug("RCV: " + str(data))
                            idx = data.find(10)
                            if idx < 0:
                                stringall += data
                            else:
                                stringall += data[0:idx]
                                break
                if idx < 0:
                    raise Exception('Timeout in receiving data')
                sock.close()
                obj = json.loads(stringall)
                obj = self.alter_server_obj(obj)
                break
            except Exception:
                lastex = traceback.format_exc()
                if sock:
                    try:
                        sock.close()
                    except Exception:
                        pass
                traceback.print_exc()
        if lastex:
            send_message(
                '/dl_finish',
                (json.dumps(dict(error=str(lastex))),),
                '127.0.0.1',
                self.port_osc,
                encoding='utf8'
            )
        else:
            try:
                outobj = list()
                foundfilters = []
                title = ''
                devfilter = self.config.get("device", "device")
                filters = devfilter.split('/')
                for dev in obj:
                    dn = dev["name"]
                    dev['name2'] = ''
                    dt = dev["type"]
                    Logger.debug("DEV " + dn + ":" + dt + "/" + str(dev))
                    k = 1
                    filt = False
                    if 'sh' in dev:
                        Logger.debug("Filter detected: " + dn + "/sh")
                        foundfilters.append(dn + '/sh')
                        filt = True
                    if "dir" in dev:
                        filt2 = dict()
                        for remk in dev["dir"]:
                            parts = remk.split(':')
                            remn = parts[0]
                            if remn not in filt2:
                                filt2[remn] = 1
                                Logger.debug("Filter detected: " + dn + "/" + remn)
                                foundfilters.append(dn + '/' + remn)
                        filt = True
                    if not filt:
                        Logger.debug("Filter detected: " + dn)
                        foundfilters.append(dn)
                    if len(filters) and dn == filters[0]:
                        title = dn
                        if dt == "DeviceRM" or dt == "DeviceAllOne" or dt == "DeviceCT10" or\
                                dt == "DeviceUpnpIRTA2" or dt == "DeviceUpnpIRRC" or dt == "DeviceSamsungCtl":
                            remmap = dict()
                            if "sh" in dev and len(filters) > 1 and filters[1] == "sh":
                                title += '/sh'
                                for remk in dev["sh"]:
                                    parts = remk.split(':')
                                    shnm = parts[0]
                                    if shnm not in remmap:
                                        remmap[shnm] = 1
                                        outobj.append(self.define_sh(
                                            dev, shnm, "@" + str(k) + " emitir " + dn + " " + shnm))
                                        k += 1
                            elif "dir" in dev and len(filters) > 1:
                                title += "/" + filters[1]
                                for remk in dev["dir"]:
                                    parts = remk.split(':')
                                    remn = parts[0]
                                    shnm = parts[1]
                                    if remn == filters[1] and shnm not in remmap:
                                        remmap[shnm] = 1
                                        dev['name2'] = remn
                                        outobj.append(self.define_sh(
                                            dev, shnm, "@" + str(k) + " emitir " + dn + " " + remn + ":" + shnm))
                                        k += 1
                        elif dt == "DeviceVirtual":
                            for stvalue, shnm in dev['nicks'].items():
                                outobj.append(self.define_sh(dev, shnm, "@" + str(k) +
                                                             " statechange " + dn + " " + stvalue))
                                k += 1
                        elif dt == "DevicePrimelan" and int(dev["subtype"]) == 1:
                            Logger.debug("Here 1")
                            for stvalue in range(100):
                                outobj.append(self.define_sh(dev, str(stvalue), "@" +
                                                             str(k) + " statechange " + dn + " " + str(stvalue)))
                                k += 1
                        elif dt == "DeviceS20" or dt == "DeviceTasmotaswitch" or (dt == "DevicePrimelan" and (int(dev["subtype"]) == 2 or int(dev["subtype"]) == 0)):
                            Logger.debug("Here 2")
                            outobj.append(self.define_sh(dev, "ON", "@" +
                                                         str(k) + " statechange " + dn + " 1"))
                            k += 1
                            outobj.append(self.define_sh(dev, "OFF", "@" +
                                                         str(k) + " statechange " + dn + " 0"))
                send_message(
                    '/dl_finish',
                    (json.dumps(dict(obj=outobj, title=title, filters=foundfilters)),),
                    '127.0.0.1',
                    self.port_osc,
                    encoding='utf8'
                )
            except Exception:
                lastex = traceback.format_exc()
                traceback.print_exc()
            if lastex:
                send_message(
                    '/dl_finish',
                    (json.dumps(dict(error=str(lastex))),),
                    '127.0.0.1',
                    self.port_osc,
                    encoding='utf8'
                )

    def tst(self):
        self.root.ids.okbtn.disabled = True
        # threading.Thread(target=self.dl_devices).start()

    def go(self):
        self.root.ids.okbtn.disabled = True
        threading.Thread(target=self.dl_devices).start()


class MySettingsWithTabbedPanel(SettingsWithTabbedPanel):
    """
    It is not usually necessary to create subclass of a settings panel. There
    are many built-in types that you can use out of the box
    (SettingsWithSidebar, SettingsWithSpinner etc.).
    You would only want to create a Settings subclass like this if you want to
    change the behavior or appearance of an existing Settings class.
    """

    def on_close(self):
        Logger.info("main.py: MySettingsWithTabbedPanel.on_close")
        App.get_running_app().stop()

    def on_config_change(self, config, section, key, value):
        Logger.info(
            "main.py: MySettingsWithTabbedPanel.on_config_change: "
            "{0}, {1}, {2}, {3}".format(config, section, key, value))


MyApp.init_map()

os.environ['KIVY_EVENTLOOP'] = 'async'
loop = asyncio.get_event_loop()
loop.run_until_complete(MyApp().async_run())
loop.close()
# MyApp().run()
