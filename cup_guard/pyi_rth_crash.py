"""Install crash logging before the rest of the app starts."""
from cup_guard.crash_report import install_handlers

install_handlers()
