import functools
import inspect
import logging
import os
import time
from typing import Any, Callable, Iterable, Optional, Sequence

_LOGGING_CONFIGURED = False


def configure_logging(level_name: Optional[str] = None) -> int:
    """
    Ensure root logging is configured once. Level can be overridden via
    ESS_GUI_LOG_LEVEL environment variable or the supplied level_name.
    """
    global _LOGGING_CONFIGURED
    if level_name is None:
        level_name = os.getenv("ESS_GUI_LOG_LEVEL", "DEBUG")
    level = getattr(logging, str(level_name).upper(), logging.DEBUG)
    if not _LOGGING_CONFIGURED:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        )
        _LOGGING_CONFIGURED = True
    root_logger = logging.getLogger()
    if root_logger.level == logging.NOTSET or root_logger.level > level:
        root_logger.setLevel(level)
    return level


def get_logger(name: str) -> logging.Logger:
    """Return a logger after ensuring logging is configured."""
    configure_logging()
    return logging.getLogger(name)


def ensure_logger(obj: Any, name: Optional[str] = None) -> logging.Logger:
    """
    Attach a logger to obj if it does not already have one.
    The logger name defaults to the class-qualified name of the object.
    """
    logger = getattr(obj, "logger", None)
    if logger is None:
        if name is None:
            cls = obj.__class__
            name = f"{cls.__module__}.{cls.__name__}"
        logger = get_logger(name)
        setattr(obj, "logger", logger)
    return logger


def safe_repr(value: Any, maxlen: int = 120) -> str:
    """Return a repr truncated to maxlen characters."""
    try:
        text = repr(value)
    except Exception as exc:  # pragma: no cover - repr rarely fails
        text = f"<repr error: {exc}>"
    if len(text) > maxlen:
        text = text[: maxlen - 3] + "..."
    return text


def summarize_bytes(data: Any, limit: int = 64) -> str:
    """Produce a compact summary for bytes/bytearray payloads."""
    if data is None:
        return "None"
    if not isinstance(data, (bytes, bytearray)):
        return safe_repr(data)
    display = bytes(data[:limit])
    hex_sample = " ".join(f"{byte:02X}" for byte in display)
    ascii_sample = "".join(chr(byte) if 32 <= byte <= 126 else "." for byte in display)
    remainder = len(data) - len(display)
    suffix = "" if remainder <= 0 else f" ... (+{remainder} bytes)"
    return f"{len(data)} bytes | hex: {hex_sample} | ascii: {ascii_sample}{suffix}"


class SerialDebugWrapper:
    """
    Thin wrapper around a pySerial Serial instance that logs reads/writes.
    """

    def __init__(self, serial_obj: Any, logger: Optional[logging.Logger] = None, name: str = "serial"):
        object.__setattr__(self, "_ser", serial_obj)
        object.__setattr__(self, "_logger", logger or get_logger(__name__))
        object.__setattr__(self, "_name", name)

    def _serial_id(self) -> str:
        port = getattr(self._ser, "port", "unknown")
        baud = getattr(self._ser, "baudrate", "unknown")
        return f"{self._name}@{port} (baud {baud})"

    # --- pySerial API passthroughs with logging ---------------------------------
    def write(self, data: bytes) -> int:
        self._logger.debug("%s.write request: %s", self._serial_id(), summarize_bytes(data))
        try:
            written = self._ser.write(data)
        except Exception:  # pragma: no cover - debugging utility
            self._logger.exception("%s.write failed", self._serial_id())
            raise
        self._logger.debug("%s.write completed: %s bytes written", self._serial_id(), written)
        return written

    def read(self, size: int = 1) -> bytes:
        in_waiting = None
        try:
            in_waiting = getattr(self._ser, "in_waiting", None)
        except Exception:  # pragma: no cover
            pass
        self._logger.debug("%s.read request: size=%s, in_waiting=%s", self._serial_id(), size, in_waiting)
        start_time = time.time()
        try:
            data = self._ser.read(size)
        except Exception:  # pragma: no cover
            self._logger.exception("%s.read failed", self._serial_id())
            raise
        duration = time.time() - start_time
        self._logger.debug("%s.read response (%0.3fs): %s", self._serial_id(), duration, summarize_bytes(data))
        return data

    def readline(self, *args, **kwargs) -> bytes:
        self._logger.debug("%s.readline request", self._serial_id())
        start_time = time.time()
        try:
            data = self._ser.readline(*args, **kwargs)
        except Exception:  # pragma: no cover
            self._logger.exception("%s.readline failed", self._serial_id())
            raise
        duration = time.time() - start_time
        self._logger.debug("%s.readline response (%0.3fs): %s", self._serial_id(), duration, summarize_bytes(data))
        return data

    def read_until(self, *args, **kwargs) -> bytes:
        self._logger.debug("%s.read_until request", self._serial_id())
        start_time = time.time()
        try:
            data = self._ser.read_until(*args, **kwargs)
        except Exception:  # pragma: no cover
            self._logger.exception("%s.read_until failed", self._serial_id())
            raise
        duration = time.time() - start_time
        self._logger.debug("%s.read_until response (%0.3fs): %s", self._serial_id(), duration, summarize_bytes(data))
        return data

    # --- buffer helpers ---------------------------------------------------------
    def reset_input_buffer(self) -> Any:
        self._logger.debug("%s.reset_input_buffer()", self._serial_id())
        return self._ser.reset_input_buffer()

    def reset_output_buffer(self) -> Any:
        self._logger.debug("%s.reset_output_buffer()", self._serial_id())
        return self._ser.reset_output_buffer()

    def flush(self) -> Any:
        self._logger.debug("%s.flush()", self._serial_id())
        return self._ser.flush()

    def close(self) -> Any:
        self._logger.debug("%s.close()", self._serial_id())
        return self._ser.close()

    # --- default attribute passthroughs -----------------------------------------
    def __getattr__(self, item: str) -> Any:
        return getattr(self._ser, item)

    def __setattr__(self, key: str, value: Any) -> None:
        if key in {"_ser", "_logger", "_name"}:
            object.__setattr__(self, key, value)
        else:
            setattr(self._ser, key, value)

    def __delattr__(self, item: str) -> None:
        if item in {"_ser", "_logger", "_name"}:
            object.__delattr__(self, item)
        else:
            delattr(self._ser, item)

    def __dir__(self) -> Sequence[str]:
        return sorted(set(dir(self.__class__)) | set(self.__dict__.keys()) | set(dir(self._ser)))

    def __repr__(self) -> str:
        return f"<SerialDebugWrapper for {self._serial_id()}>"


def log_call(
    func: Optional[Callable] = None,
    *,
    logger_attr: str = "logger",
    logger_name: Optional[str] = None,
    level: int = logging.DEBUG,
    log_args: bool = True,
    log_result: bool = False,
    log_exceptions: bool = True,
) -> Callable:
    """
    Decorator that logs a function or method call with arguments and results.
    """

    def decorator(inner_func: Callable) -> Callable:
        method_name = inner_func.__qualname__

        @functools.wraps(inner_func)
        def wrapper(*args, **kwargs):
            logger = None
            bound_instance = args[0] if args else None
            if bound_instance is not None:
                logger = getattr(bound_instance, logger_attr, None)
            if logger is None:
                resolved_name = logger_name or inner_func.__module__
                logger = get_logger(resolved_name)

            if log_args:
                arg_parts: Iterable[str] = []
                if args:
                    arg_parts = list(
                        safe_repr(arg, maxlen=80 if idx else 40) for idx, arg in enumerate(args)
                    )
                kw_parts = [f"{key}={safe_repr(val, maxlen=80)}" for key, val in kwargs.items()]
                signature = ", ".join(list(arg_parts) + kw_parts)
            else:
                signature = ""

            logger.log(level, "Entering %s(%s)", method_name, signature)
            try:
                result = inner_func(*args, **kwargs)
            except Exception as exc:
                if log_exceptions:
                    logger.exception("Error in %s: %s", method_name, exc)
                raise

            if log_result:
                logger.log(level, "Exiting %s -> %s", method_name, safe_repr(result, maxlen=120))
            else:
                logger.log(level, "Exiting %s", method_name)
            return result

        setattr(wrapper, "_debug_wrapped", True)
        return wrapper

    if func is None:
        return decorator
    return decorator(func)


def log_class_methods(
    cls: type,
    *,
    logger_attr: str = "logger",
    logger_name: Optional[str] = None,
    exclude: Optional[Iterable[str]] = None,
    include_private: bool = False,
    level: int = logging.DEBUG,
    log_args: bool = True,
    log_result: bool = False,
) -> type:
    """
    Wrap all callable attributes on cls with log_call to automatically emit debug logging.
    """
    exclusions = set(exclude or ())
    for attr_name, attr_value in list(cls.__dict__.items()):
        if attr_name in exclusions:
            continue
        if isinstance(attr_value, (staticmethod, classmethod, property)):
            continue
        if not callable(attr_value):
            continue
        if not include_private and attr_name.startswith("_"):
            continue
        if getattr(attr_value, "_debug_wrapped", False):
            continue
        wrapped = log_call(
            attr_value,
            logger_attr=logger_attr,
            logger_name=logger_name,
            level=level,
            log_args=log_args,
            log_result=log_result,
        )
        setattr(cls, attr_name, wrapped)
    return cls

