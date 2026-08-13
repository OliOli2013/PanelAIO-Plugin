# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

import logging
import os
import traceback

try:
    from logging.handlers import RotatingFileHandler
except Exception:
    RotatingFileHandler = None

LOG_ROOT = '/tmp/PanelAIO/logs'
LOG_FILE = os.path.join(LOG_ROOT, 'panelaio.log')
_LOGGER_NAME = 'aio_panel'
_CONFIGURED = False


def _ensure_dir(path):
    try:
        if not os.path.isdir(path):
            os.makedirs(path)
    except Exception:
        pass


def setup_logging(level=logging.INFO):
    global _CONFIGURED
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(level)
    if _CONFIGURED:
        return logger
    _ensure_dir(LOG_ROOT)
    try:
        if RotatingFileHandler is not None:
            handler = RotatingFileHandler(LOG_FILE, maxBytes=256 * 1024, backupCount=3)
        else:
            handler = logging.FileHandler(LOG_FILE)
        handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s'))
        logger.addHandler(handler)
    except Exception:
        pass
    _CONFIGURED = True
    return logger


def get_logger():
    return setup_logging()


def log_exception(context, exc=None):
    logger = setup_logging()
    try:
        if exc is None:
            logger.error('%s\n%s', context, traceback.format_exc())
        else:
            logger.error('%s: %s\n%s', context, exc, traceback.format_exc())
    except Exception:
        pass
