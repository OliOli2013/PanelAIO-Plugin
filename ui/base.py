# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

import traceback
from threading import Thread

from Components.Label import Label
try:
    from Components.ScrollLabel import ScrollLabel
except Exception:
    ScrollLabel = None
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
try:
    from enigma import eTimer
except Exception:
    eTimer = None

from Plugins.SystemPlugins.PanelAIO.core.compatibility import ensure_str

class ManagedScreen(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self._timers = []
        self.onClose.append(self._cleanup_resources)

    def create_timer(self, callback):
        if eTimer is None:
            return None
        timer = eTimer()
        try:
            conn = timer.timeout.connect(callback)
            self._timers.append((timer, conn))
        except Exception:
            try:
                timer.callback.append(callback)
            except Exception:
                pass
            self._timers.append((timer, None))
        return timer

    def _cleanup_resources(self):
        for timer, conn in self._timers:
            try:
                timer.stop()
            except Exception:
                pass
        self._timers = []

    def show_info(self, message, timeout=10):
        self.session.open(MessageBox, ensure_str(message), MessageBox.TYPE_INFO, timeout=timeout)

    def show_error(self, message, timeout=12):
        self.session.open(MessageBox, ensure_str(message), MessageBox.TYPE_ERROR, timeout=timeout)

    def ask_yes_no(self, message, callback):
        self.session.openWithCallback(callback, MessageBox, ensure_str(message), type=MessageBox.TYPE_YESNO)

    def start_background_task(self, target, on_success, on_error=None, busy_text=None):
        state = {'done': False, 'result': None, 'error': None}
        wait_dialog = None
        if busy_text:
            try:
                wait_dialog = self.session.open(MessageBox, ensure_str(busy_text), MessageBox.TYPE_INFO, enable_input=False)
            except Exception:
                wait_dialog = None

        def runner():
            try:
                state['result'] = target()
            except Exception:
                state['error'] = traceback.format_exc()
            state['done'] = True

        def poll():
            if state['done']:
                try:
                    timer.stop()
                except Exception:
                    pass
                try:
                    if wait_dialog is not None:
                        wait_dialog.close()
                except Exception:
                    pass
                if state['error']:
                    if on_error is not None:
                        on_error(state['error'])
                    else:
                        self.show_error(state['error'])
                else:
                    if on_success is not None:
                        on_success(state['result'])
            else:
                try:
                    timer.start(250, True)
                except Exception:
                    pass

        Thread(target=runner, daemon=True).start()
        timer = self.create_timer(poll)
        if timer is not None:
            timer.start(250, True)
        return state

class ScrollTextMixin(object):
    def set_scroll_text(self, widget_name, value):
        try:
            self[widget_name].setText(ensure_str(value))
        except Exception:
            pass

    def page_up(self, widget_name='body'):
        try:
            self[widget_name].pageUp()
        except Exception:
            pass

    def page_down(self, widget_name='body'):
        try:
            self[widget_name].pageDown()
        except Exception:
            pass

def make_body_widget(initial=''):
    if ScrollLabel is not None:
        return ScrollLabel(ensure_str(initial))
    return Label(ensure_str(initial))
