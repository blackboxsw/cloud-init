# Copyright (C) 2012 Canonical Ltd.
# Copyright (C) 2012 Hewlett-Packard Development Company, L.P.
# Copyright (C) 2012 Yahoo! Inc.
#
# Author: Scott Moser <scott.moser@canonical.com>
# Author: Juerg Haefliger <juerg.haefliger@hp.com>
# Author: Joshua Harlow <harlowja@yahoo-inc.com>
#
# This file is part of cloud-init. See LICENSE file for license information.

import collections.abc
import copy
import io
import logging
import logging.config
import logging.handlers
import os
import sys
import time
from collections import defaultdict
from contextlib import suppress
from typing import DefaultDict

DEFAULT_LOG_FORMAT = "%(asctime)s - %(filename)s[%(levelname)s]: %(message)s"
DEPRECATED = 35
TRACE = logging.DEBUG - 5


class CustomLoggerType(logging.Logger):
    """A hack to get mypy to stop complaining about custom logging methods.

    When using deprecated or trace logging, rather than:
        LOG = logging.getLogger(__name__)
    Instead do:
        LOG = cast(CustomLoggerType, logging.getLogger(__name__))
    """

    def trace(self, *args, **kwargs):
        pass

    def deprecated(self, *args, **kwargs):
        pass


def setup_basic_logging(level=logging.DEBUG, formatter=None):
    formatter = formatter or logging.Formatter(DEFAULT_LOG_FORMAT)
    root = logging.getLogger()
    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)
    console.setLevel(level)
    root.addHandler(console)
    root.setLevel(level)


def flush_loggers(root):
    if not root:
        return
    for h in root.handlers:
        if isinstance(h, (logging.StreamHandler)):
            with suppress(IOError):
                h.flush()
    flush_loggers(root.parent)


def define_extra_loggers() -> None:
    """Add DEPRECATED and TRACE log levels to the logging module."""

    def new_logger(level):
        def log_at_level(self, message, *args, **kwargs):
            if self.isEnabledFor(level):
                self._log(level, message, args, **kwargs)

        return log_at_level

    logging.addLevelName(DEPRECATED, "DEPRECATED")
    logging.addLevelName(TRACE, "TRACE")
    setattr(logging.Logger, "deprecated", new_logger(DEPRECATED))
    setattr(logging.Logger, "trace", new_logger(TRACE))


def setup_logging(cfg=None):
    # See if the config provides any logging conf...
    if not cfg:
        cfg = {}

    root_logger = logging.getLogger()
    exporter = LogExporter()
    exporter.setLevel(logging.WARN)

    log_cfgs = []
    log_cfg = cfg.get("logcfg")
    if log_cfg and isinstance(log_cfg, str):
        # If there is a 'logcfg' entry in the config,
        # respect it, it is the old keyname
        log_cfgs.append(str(log_cfg))
    elif "log_cfgs" in cfg:
        for a_cfg in cfg["log_cfgs"]:
            if isinstance(a_cfg, str):
                log_cfgs.append(a_cfg)
            elif isinstance(a_cfg, (collections.abc.Iterable)):
                cfg_str = [str(c) for c in a_cfg]
                log_cfgs.append("\n".join(cfg_str))
            else:
                log_cfgs.append(str(a_cfg))

    # See if any of them actually load...
    am_tried = 0

    # log_cfg may contain either a filepath to a file containing a logger
    # configuration, or a string containing a logger configuration
    # https://docs.python.org/3/library/logging.config.html#logging-config-fileformat
    for log_cfg in log_cfgs:
        # The default configuration includes an attempt at using /dev/log,
        # followed up by writing to a file. /dev/log will not exist in
        # very early boot, so an exception on that is expected.
        with suppress(FileNotFoundError):
            am_tried += 1

            # If the value is not a filename, assume that it is a config.
            if not (log_cfg.startswith("/") and os.path.isfile(log_cfg)):
                log_cfg = io.StringIO(log_cfg)

            # Attempt to load its config.
            logging.config.fileConfig(log_cfg)

            # Configure warning exporter after loading logging configuration
            root_logger.addHandler(exporter)

            # Use the first valid configuration.
            return

    # Configure warning exporter for basic logging
    root_logger.addHandler(exporter)

    # If it didn't work, at least setup a basic logger (if desired)
    basic_enabled = cfg.get("log_basic", True)

    sys.stderr.write(
        "WARN: no logging configured! (tried %s configs)\n" % (am_tried)
    )
    if basic_enabled:
        sys.stderr.write("Setting up basic logging...\n")
        setup_basic_logging()


class LogExporter(logging.StreamHandler):
    holder: DefaultDict[str, list] = defaultdict(list)

    def emit(self, record: logging.LogRecord):
        self.holder[record.levelname].append(record.getMessage())

    def export_logs(self):
        return copy.deepcopy(self.holder)

    def clean_logs(self):
        self.holder = defaultdict(list)

    def flush(self):
        pass


def reset_logging():
    """Remove all current handlers and unset log level."""
    log = logging.getLogger()
    handlers = list(log.handlers)
    for h in handlers:
        h.flush()
        h.close()
        log.removeHandler(h)
    log.setLevel(logging.NOTSET)


def setup_backup_logging():
    """In the event that internal logging exception occurs and logging is not
    possible for some reason, make a desperate final attempt to log to stderr
    which may ease debugging.
    """
    fallback_handler = logging.StreamHandler(sys.stderr)
    setattr(fallback_handler, "handleError", lambda record: None)
    fallback_handler.setFormatter(
        logging.Formatter(
            "FALLBACK: %(asctime)s - %(filename)s[%(levelname)s]: %(message)s"
        )
    )

    def handleError(self, record):
        """A closure that emits logs on stderr when other methods fail"""
        with suppress(IOError):
            fallback_handler.handle(record)
            fallback_handler.flush()

    setattr(logging.Handler, "handleError", handleError)


class CloudInitLogRecord(logging.LogRecord):
    """reporting the filename as __init__.py isn't very useful in logs

    if the filename is __init__.py, use the parent directory as the filename
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "__init__.py" == self.filename:
            self.filename = os.path.basename(os.path.dirname(self.pathname))


def configure_root_logger():
    """Customize the root logger for cloud-init"""

    # Always format logging timestamps as UTC time
    logging.Formatter.converter = time.gmtime
    define_extra_loggers()
    setup_backup_logging()
    reset_logging()

    # add handler only to the root logger
    handler = LogExporter()
    handler.setLevel(logging.WARN)
    logging.getLogger().addHandler(handler)

    # LogRecord allows us to report more useful information than __init__.py
    logging.setLogRecordFactory(CloudInitLogRecord)
