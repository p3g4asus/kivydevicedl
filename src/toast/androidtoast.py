from jnius import autoclass, cast
from android.runnable import run_on_ui_thread

Toast = autoclass('android.widget.Toast')
context = autoclass('org.kivy.android.PythonActivity').mActivity    

@run_on_ui_thread
def toast(text, length_long=False):
    duration = Toast.LENGTH_LONG if length_long else Toast.LENGTH_SHORT
    String = autoclass('java.lang.String')
    c = cast('java.lang.CharSequence', String(text))
    t = Toast.makeText(context, c, duration)
    t.show()
