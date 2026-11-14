"""Single persistent host; do not preload an application that starts worker threads."""

bind = "127.0.0.1:8787"
workers = 1
worker_class = "gthread"
threads = 4
preload_app = False
timeout = 120
graceful_timeout = 30
accesslog = "-"
errorlog = "-"

# Keep state private and avoid a control socket outside the service state directory.
umask = 0o077
control_socket_disable = True
