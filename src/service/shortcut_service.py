import asyncio
import json
import os
import threading
import traceback
from os.path import dirname, join
from time import time

from android.broadcast import BroadcastReceiver
from jnius import PythonJavaClass, autoclass, cast, java_method
from kivy.logger import Logger
from oscpy.client import send_message
from oscpy.server import OSCThreadServer

ACTION_RESULT_SH = 'kyvidevdl.result.sh'
ACTION_NEXT_SH = 'kyvidevdl.next.sh'
ACTION_STOP_SH = 'kyvidevdl.stop.sh'
ACTION_REPEAT_SH = 'kyvidevdl.repeat.sh'


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
            traceback.print_exc()


class ShortcutService(object):
    def init_java_classes(self):
        self.PendingIntent = autoclass('android.app.PendingIntent')
        self.ShortcutInfoBuilder = autoclass('android.content.pm.ShortcutInfo$Builder')
        self.Intent = autoclass('android.content.Intent')
        self.Icon = autoclass('android.graphics.drawable.Icon')
        self.Uri = autoclass('android.net.Uri')
        self.BitmapFactory = autoclass("android.graphics.BitmapFactory")
        self.AndroidString = autoclass('java.lang.String')
        self.LauncherApps = autoclass('android.content.pm.LauncherApps')
        BitmapFactoryOptions = autoclass("android.graphics.BitmapFactory$Options")
        self.bitmap_factory_options = BitmapFactoryOptions()

    def init_notification(self):
        self.init_java_classes()
        Context = autoclass('android.content.Context')
        NotificationBuilder = autoclass('android.app.Notification$Builder')
        NotificationActionBuilder = autoclass('android.app.Notification$Action$Builder')
        Notification = autoclass('android.app.Notification')
        Color = autoclass("android.graphics.Color")
        NotificationChannel = autoclass('android.app.NotificationChannel')
        NotificationManager = autoclass('android.app.NotificationManager')
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        self.service = autoclass('org.kivy.android.PythonService').mService
        self.FOREGROUND_NOTIFICATION_ID = 4572
        Intent = self.Intent
        channelName = self.AndroidString('DeviceManagerService'.encode('utf-8'))
        NOTIFICATION_CHANNEL_ID = self.AndroidString(self.service.getPackageName().encode('utf-8'))
        chan = NotificationChannel(NOTIFICATION_CHANNEL_ID, channelName, NotificationManager.IMPORTANCE_DEFAULT)
        chan.setLightColor(Color.BLUE)
        chan.setLockscreenVisibility(Notification.VISIBILITY_PRIVATE)
        self.shortcut_service = self.service.getSystemService(Context.SHORTCUT_SERVICE)
        self.notification_service = self.service.getSystemService(Context.NOTIFICATION_SERVICE)
        app_context = self.service.getApplication().getApplicationContext()
        self.notification_service.createNotificationChannel(chan)
        notification_image = join(dirname(__file__), '..', 'images', 'shortcut_service.png')
        bm = self.BitmapFactory.decodeFile(notification_image, self.bitmap_factory_options)
        notification_icon = self.Icon.createWithBitmap(bm)
        notification_intent = Intent(app_context, PythonActivity)
        notification_intent.setFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP |
                                     Intent.FLAG_ACTIVITY_SINGLE_TOP |
                                     Intent.FLAG_ACTIVITY_NEW_TASK)
        notification_intent.setAction(Intent.ACTION_MAIN)
        notification_intent.addCategory(Intent.CATEGORY_LAUNCHER)
        notification_intent = self.PendingIntent.getActivity(self.service, 0, notification_intent, 0)
        self.notification_builder_no_action = NotificationBuilder(app_context, NOTIFICATION_CHANNEL_ID)\
            .setContentIntent(notification_intent)\
            .setSmallIcon(notification_icon)

        notification_image = join(dirname(__file__), '..', 'images', 'stop.png')
        bm = self.BitmapFactory.decodeFile(notification_image, self.bitmap_factory_options)
        icon = self.Icon.createWithBitmap(bm)
        broadcastIntent = Intent(ACTION_STOP_SH)
        actionIntent = self.PendingIntent.getBroadcast(self.service,
                                                       0,
                                                       broadcastIntent,
                                                       self.PendingIntent.FLAG_UPDATE_CURRENT)
        stop_action = NotificationActionBuilder(
            icon,
            self.AndroidString('STOP'.encode('utf-8')),
            actionIntent).build()

        notification_image = join(dirname(__file__), '..', 'images', 'repeat.png')
        bm = self.BitmapFactory.decodeFile(notification_image, self.bitmap_factory_options)
        icon = self.Icon.createWithBitmap(bm)
        broadcastIntent = Intent(ACTION_REPEAT_SH)
        actionIntent = self.PendingIntent.getBroadcast(self.service,
                                                       0,
                                                       broadcastIntent,
                                                       self.PendingIntent.FLAG_UPDATE_CURRENT)
        repeat_action = NotificationActionBuilder(
            icon,
            self.AndroidString('REPEAT'.encode('utf-8')),
            actionIntent).build()

        notification_image = join(dirname(__file__), '..', 'images', 'next.png')
        bm = self.BitmapFactory.decodeFile(notification_image, self.bitmap_factory_options)
        icon = self.Icon.createWithBitmap(bm)
        broadcastIntent = Intent(ACTION_NEXT_SH)
        actionIntent = self.PendingIntent.getBroadcast(self.service,
                                                       0,
                                                       broadcastIntent,
                                                       self.PendingIntent.FLAG_UPDATE_CURRENT)
        next_action = NotificationActionBuilder(
            icon,
            self.AndroidString('NEXT'.encode('utf-8')),
            actionIntent).build()
        self.notification_builder = NotificationBuilder(app_context, NOTIFICATION_CHANNEL_ID)\
            .setContentIntent(notification_intent)\
            .setSmallIcon(notification_icon)\
            .addAction(stop_action)\
            .addAction(repeat_action)\
            .addAction(next_action)
        self.service.setAutoRestartService(False)
        self.service.startForeground(self.FOREGROUND_NOTIFICATION_ID, self.build_service_notification())

    def __init__(self, port_to_bind=None, port_to_send=None):
        self.port_to_bind = port_to_bind
        self.port_to_send = port_to_send
        self.osc = OSCThreadServer(encoding='utf8')
        self.osc.listen(address='127.0.0.1', port=self.port_to_bind, default=True)
        self.osc.bind('/quit', self.on_quit)
        self.osc.bind('/request', self.on_request)
        self.br = BroadcastReceiver(self.on_broadcast, actions=[
            ACTION_STOP_SH,
            ACTION_REPEAT_SH,
            ACTION_NEXT_SH,
            ACTION_RESULT_SH])
        self.loop = None
        self.requests = []
        self.current_request = None
        self.current_sh = None
        self.lock = threading.Lock()
        self.last_request = 0
        try:
            self.init_notification()
        except:  # noqa E722
            Logger.error(f"Error detected {traceback.print_exc()}")
        Logger.debug("Init ended")

    def build_service_notification(self, title=None, message=None):
        nb = self.notification_builder_no_action
        if not title:
            title = "ShortcutService"
        if not message:
            message = "Installing shortcuts"
        else:
            message = f"Installing shortcut {message}"
            nb = self.notification_builder

        title = self.AndroidString((title if title else 'N/A').encode('utf-8'))
        message = self.AndroidString(message.encode('utf-8'))
        nb.setContentTitle(title)\
            .setContentText(message)\
            .setOnlyAlertOnce(True)
        return nb.getNotification()

    def set_service_notification(self, idnot, notif):
        self.notification_service.notify(idnot, notif)

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
        Logger.info(f"Request received {msg}")
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
        try:
            if context:
                action = intent.getAction()
                if action == ACTION_RESULT_SH and self.current_sh:
                    # sh_info = cast('android.content.pm.LauncherApps$PinItemRequest',
                    #                intent.getParcelableExtra(self.LauncherApps.EXTRA_PIN_ITEM_REQUEST)).getShortcutInfo()
                    # idcurrent = self.current_request['sh_device'] + self.current_sh['name']
                    # Logger.info(f'ID1 = {sh_info.getId()} ID2={idcurrent}')
                    # if sh_info.getId() == idcurrent:
                    #     processed = self.current_sh
                    #     self.process_request()
                    # else:
                    #     return
                    # The check of the id should be done to be sure the intent returned relates to the request. But I am commenting it
                    # out because it seems that the intent returned by the launcher is someway wrong (the id returned does not match the
                    # one that was in pinnedShortcutCallbackIntent): This happends in pixel launcher (02/10/2020)
                    processed = self.current_sh
                    self.process_request()
                elif action == ACTION_NEXT_SH:
                    self.process_request()
                    return
                elif action == ACTION_REPEAT_SH:
                    self.process_request(True)
                    return
                elif action == ACTION_STOP_SH:
                    self.stop_processing()
                    return
            else:
                processed = None
            asyncio.ensure_future(self.send_response(processed), loop=self.loop)
        except Exception:
            Logger.error(f"Error detected {traceback.format_exc()}")

    def stop_processing(self):
        self.current_request = None
        self.lock.acquire()
        del self.requests[:]
        self.lock.release()

    def process_request(self, repeat=False):
        self.last_request = time()
        if not repeat:
            if not self.current_request and not len(self.requests):
                return
            elif not self.current_request or not self.current_request['shs']:
                self.lock.acquire()
                while self.requests:
                    self.current_request = self.requests.pop(0)
                    if self.current_request['shs']:
                        break
                self.lock.release()
        elif not self.current_request or not self.current_sh:
            return
        sh = None
        if not repeat:
            if self.current_request['shs']:
                sh = self.current_sh = self.current_request['shs'].pop(0)
        else:
            sh = self.current_sh
        if sh:
            ctx = self.br.context
            if self.shortcut_service.isRequestPinShortcutSupported():
                sh_id = self.current_request['sh_device'] + sh['name']
                self.set_service_notification(self.FOREGROUND_NOTIFICATION_ID, self.build_service_notification(message=sh_id))
                builds = self.ShortcutInfoBuilder(ctx, sh_id)
                builds.setShortLabel(self.current_request['sh_temp'].replace('$sh$', sh['name']))
                builds.setIcon(self.Icon.createWithBitmap(self.BitmapFactory.decodeFile(sh['img'], self.bitmap_factory_options)))
                builds.setIntent(self.Intent(self.Intent.ACTION_SENDTO, self.Uri.parse(sh['link'])))
                pinShortcutInfo = builds.build()
                pinnedShortcutCallbackIntent = self.shortcut_service.createShortcutResultIntent(pinShortcutInfo)
                Logger.info(f'Sending request for id {sh_id} (intent={cast("android.content.pm.LauncherApps$PinItemRequest", pinnedShortcutCallbackIntent.getParcelableExtra(self.LauncherApps.EXTRA_PIN_ITEM_REQUEST)).getShortcutInfo().getId()})')
                pinnedShortcutCallbackIntent.setAction(ACTION_RESULT_SH)
                successCallback = self.PendingIntent.getBroadcast(ctx,  0, pinnedShortcutCallbackIntent, 0)
                self.shortcut_service.requestPinShortcut(pinShortcutInfo, successCallback.getIntentSender())
            else:
                self.stop_processing()
                self.on_broadcast(None, None)
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
