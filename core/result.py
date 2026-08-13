# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

from Plugins.SystemPlugins.PanelAIO.core.compatibility import ensure_unicode


class ActionResult(dict):
    """Dict-compatible result used by new code without breaking legacy callbacks."""
    def __init__(self, success=False, code='', title='', message='', details='', restart_gui=False, reboot=False, rollback=False, log='', **extra):
        dict.__init__(self)
        self.update({
            'success': bool(success),
            'code': ensure_unicode(code),
            'title': ensure_unicode(title),
            'message': ensure_unicode(message),
            'details': ensure_unicode(details),
            'restart_gui': bool(restart_gui),
            'reboot': bool(reboot),
            'rollback': bool(rollback),
            'log': ensure_unicode(log),
        })
        self.update(extra)


def normalize_result(value, title=''):
    if isinstance(value, ActionResult):
        return value
    if isinstance(value, dict):
        success = bool(value.get('success'))
        details = value.get('details') or value.get('error') or value.get('stderr') or value.get('stdout') or value.get('output') or ''
        code = value.get('code') or value.get('returncode') or ('OK' if success else 'ERROR')
        return ActionResult(
            success=success,
            code=code,
            title=title or value.get('title') or '',
            message=value.get('message') or '',
            details=details,
            restart_gui=value.get('restart_gui', False),
            reboot=value.get('reboot', False),
            rollback=value.get('rollback', False),
            log=value.get('log', ''),
            legacy=value,
        )
    return ActionResult(success=bool(value), code=('OK' if value else 'ERROR'), title=title)
