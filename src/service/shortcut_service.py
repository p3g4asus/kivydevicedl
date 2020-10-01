import asyncio
import json
import os
import threading
from os.path import dirname, join
from time import time

from android.broadcast import BroadcastReceiver
from functools import partial
from jnius import PythonJavaClass, autoclass, java_method
from kivy.logger import Logger
from oscpy.client import send_message
from oscpy.server import OSCThreadServer

ACTION_RESULT_SH = 'kyvidevdl.result.sh'


class Runnable(PythonJavaClass):
    '''Wrapper around Java Runnable class. This class can be used to schedule a
    call of a Python function into the PythonActivity thread.
    '''

    __javainterfaces__ = ['java/lang/Runnable']

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    @java_method('()V')
    def run(self):
        try:
            self.func(*self.args, **self.kwargs)
        except:  # noqa E722
            import traceback
            traceback.print_exc()


class ShortcutService(object):
    def init_notification(self):
        self.service = autoclass('org.kivy.android.PythonService').mService
        self.FOREGROUND_NOTIFICATION_ID = 4572
        Intent = autoclass('android.content.Intent')
        self.Intent = Intent
        self.AndroidString = autoclass('java.lang.String')
        NotificationBuilder = autoclass('android.app.Notification$Builder')
        self.PythonActivity = autoclass('org.kivy.android.PythonActivity')
        PendingIntent = autoclass('android.app.PendingIntent')
        Notification = autoclass('android.app.Notification')
        Color = autoclass("android.graphics.Color")
        NotificationChannel = autoclass('android.app.NotificationChannel')
        NotificationManager = autoclass('android.app.NotificationManager')
        channelName = self.AndroidString('DeviceManagerService'.encode('utf-8'))
        NOTIFICATION_CHANNEL_ID = self.AndroidString(self.service.getPackageName().encode('utf-8'))
        chan = NotificationChannel(NOTIFICATION_CHANNEL_ID, channelName, NotificationManager.IMPORTANCE_DEFAULT)
        chan.setLightColor(Color.BLUE)
        chan.setLockscreenVisibility(Notification.VISIBILITY_PRIVATE)
        self.notification_service = self.service.getSystemService(self.br.context.NOTIFICATION_SERVICE)
        self.notification_service.createNotificationChannel(chan)
        BitmapFactory = autoclass("android.graphics.BitmapFactory")
        Icon = autoclass("android.graphics.drawable.Icon")
        BitmapFactoryOptions = autoclass("android.graphics.BitmapFactory$Options")
        # Drawable = jnius.autoclass("{}.R$drawable".format(service.getPackageName()))
        # icon = getattr(Drawable, 'icon')
        options = BitmapFactoryOptions()
        # options.inMutable = True
        # declaredField = options.getClass().getDeclaredField("inPreferredConfig")
        # declaredField.set(cast('java.lang.Object',options), cast('java.lang.Object', BitmapConfig.ARGB_8888))
        # options.inPreferredConfig = BitmapConfig.ARGB_8888;
        notification_image = join(dirname(__file__), '..', 'images', 'shortcut_service.png')
        bm = BitmapFactory.decodeFile(notification_image, options)
        notification_icon = Icon.createWithBitmap(bm)
        notification_intent = Intent(self.br.context, self.PythonActivity)
        notification_intent.setFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP |
                                     Intent.FLAG_ACTIVITY_SINGLE_TOP |
                                     Intent.FLAG_ACTIVITY_NEW_TASK)
        notification_intent.setAction(Intent.ACTION_MAIN)
        notification_intent.addCategory(Intent.CATEGORY_LAUNCHER)
        notification_intent = PendingIntent.getActivity(self.service, 0, notification_intent, 0)
        self.notification_builder_no_action = NotificationBuilder(self.br.context, NOTIFICATION_CHANNEL_ID)\
            .setContentIntent(notification_intent)\
            .setSmallIcon(notification_icon)
        self.service.setAutoRestartService(False)
        self.service.startForeground(self.FOREGROUND_NOTIFICATION_ID, self.build_service_notification())

    def __init__(self, port_to_bind=None, port_to_send=None):
        self.port_to_bind = port_to_bind
        self.port_to_send = port_to_send
        self.osc = OSCThreadServer(encoding='utf8')
        self.osc.listen(address='127.0.0.1', port=self.port_to_bind, default=True)
        self.osc.bind('/quit', self.on_quit)
        self.osc.bind('/request', self.on_request)
        self.br = BroadcastReceiver(self.on_broadcast, actions=[ACTION_RESULT_SH])
        self.loop = None
        self.requests = []
        self.current_request = None
        self.current_sh = None
        self.lock = threading.Lock()
        self.last_request = 0
        self.init_notification()

    def build_service_notification(self, title=None, message=None, lines=None, idnot=0):
        group = None
        nb = self.notification_builder_no_action
        if not title and not message:
            title = "ShortcutService"
            message = "Installing shortcuts"

        title = self.AndroidString((title if title else 'N/A').encode('utf-8'))
        message = self.AndroidString(message.encode('utf-8'))
        nb.setContentTitle(title)\
            .setGroup(group)\
            .setContentText(message)\
            .setOnlyAlertOnce(True)
        return nb.getNotification()

    def start(self):
        self.br.start()
        self.loop = asyncio.get_event_loop()
        self.loop.run_forever()

    def on_quit(self, msg):
        self.br.stop()
        self.loop.stop()
        self.service.stopForeground(True)
        self.service.stopSelf()

    def on_request(self, msg):
        m = json.loads(msg)
        self.lock.acquire()
        wasidle = len(self.requests) == 0 and not self.current_request
        if not wasidle and time() - self.last_request > 30:
            wasidle = True
            self.last_request = 0
        self.requests.append(m)
        self.lock.release()
        if wasidle:
            self.br.handler.post(Runnable(self.process_request))

    async def send_response(self, processed):
        send_message(
             '/sh_put',
             (json.dumps(processed),),
             '127.0.0.1',
             self.port_to_send,
             encoding='utf8'
        )

    def on_broadcast(self, context, intent):
        if context:
            processed = self.current_sh
            self.process_request()
        else:
            processed = None
        asyncio.ensure_future(partial(self.send_response, processed), loop=self.loop)

    def process_request(self):
        self.last_request = time()
        if not self.current_request and not len(self.requests):
            return
        elif not self.current_request or not self.current_request['shs']:
            self.lock.acquire()
            while self.requests:
                self.current_request = self.requests.pop()
                if self.current_request['shs']:
                    break
            self.lock.release()
        if self.current_request['shs']:
            sh = self.current_sh = self.current_request['shs'].pop()
            PendingIntent = autoclass('android.app.PendingIntent')
            ShortcutInfoBuilder = autoclass('android.content.pm.ShortcutInfo$Builder')
            Intent = autoclass('android.content.Intent')
            Icon = autoclass('android.graphics.drawable.Icon')
            Context = autoclass('android.content.Context')
            Uri = autoclass('android.net.Uri')
            BitmapFactory = autoclass("android.graphics.BitmapFactory")
            BitmapFactoryOptions = autoclass("android.graphics.BitmapFactory$Options")
            options = BitmapFactoryOptions()
            ctx = self.br.context
            shortcutManager = ctx.getSystemService(Context.SHORTCUT_SERVICE)
            if shortcutManager.isRequestPinShortcutSupported():
                sh_id = self.current_request['sh_device'] + sh['name']
                builds = ShortcutInfoBuilder(ctx, sh_id)
                builds.setShortLabel(self.current_request['sh_temp'].replace('$sh$', sh['name']))
                builds.setIcon(Icon.createWithBitmap(BitmapFactory.decodeFile(sh['img'], options)))
                builds.setIntent(Intent(Intent.ACTION_SENDTO, Uri.parse(sh['link'])))
                pinShortcutInfo = builds.build()
                pinnedShortcutCallbackIntent = shortcutManager.createShortcutResultIntent(pinShortcutInfo)
                Logger.info(f'Sending request for id {sh_id}')
                pinnedShortcutCallbackIntent.setAction(ACTION_RESULT_SH)
                successCallback = PendingIntent.getBroadcast(ctx,  0, pinnedShortcutCallbackIntent, 0)
                shortcutManager.requestPinShortcut(pinShortcutInfo, successCallback.getIntentSender())
            else:
                self.current_request = None
                self.lock.acquire()
                del self.requests[:]
                self.lock.release()
                self.on_broadcast(None)
        else:
            self.current_request = None


def main():
    p4a = os.environ.get('PYTHON_SERVICE_ARGUMENT', '')
    Logger.info(f"Server: p4a = {p4a}")
    args = json.loads(p4a)
    sh_service = ShortcutService(**args)
    sh_service.start()


if __name__ == '__main__':
    main()
