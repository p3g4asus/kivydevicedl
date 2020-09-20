REM py -3 -m venv %~dp0venv
REM call %~dp0venv\Scripts\activate.bat
REM pip3 install cython
REM python -m pip install --upgrade pip wheel setuptools
REM python -m pip install docutils pygments pypiwin32 kivy_deps.sdl2==0.1.* kivy_deps.glew==0.1.*
REM python -m pip install kivy_deps.gstreamer==0.1.*
REM set PATH=C:\Program Files\Java\jdk-13.0.2\bin;C:\Program Files\Java\jdk-13.0.2\bin\server;%PATH%
REM set JAVA_HOME=C:\Program Files\Java\jdk-13.0.2
REM pip install pyjnius
REM set USE_SDL2=1
REM set USE_GSTREAMER=1
REM pip3 install git+https://github.com/kivy/kivy.git@20c14b2a2bac73288a4c2808843910364565f66a
REM pip3 install oscpy
REM pip3 install Pillow
REM pause
call %~dp0venv\Scripts\activate.bat
set JAVA_HOME=C:\Program Files\Java\jdk-13.0.2
set PATH=C:\Program Files\Java\jdk-13.0.2\bin\server;%PATH%
set KCFG_KIVY_LOG_LEVEL=debug
set KCFG_KIVY_LOG_ENABLE=1
set KCFG_KIVY_LOG_DIR=%~dp0logs
python src\main.py -d
pause
