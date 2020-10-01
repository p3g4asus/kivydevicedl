import asyncio
import json
import os
import threading
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

    def start(self):
        self.br.start()
        self.loop = asyncio.get_event_loop()
        self.loop.run_forever()

    def on_quit(self, msg):
        self.br.stop()
        self.loop.stop()

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
                Logger.info(f'Sending request for {sh_id}')
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
