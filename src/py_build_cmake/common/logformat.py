import logging


class GitHubActionsFormatter(logging.Formatter):
    """Formats warnings etc. for GitHub Actions: https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#setting-a-notice-message"""

    def __init__(self):
        super().__init__(fmt="%(name)s:%(message)s")

    def format(self, record: logging.LogRecord):
        s = super().format(record)
        prefix = {
            logging.INFO:
            "::notice file=%(pathname)s,line=%(lineno)d::" % record.__dict__,
            logging.WARNING:
            "::warning file=%(pathname)s,line=%(lineno)d::" % record.__dict__,
            logging.ERROR:
            "::error file=%(pathname)s,line=%(lineno)d::" % record.__dict__
        }.get(record.levelno, record.levelname + ":")
        return prefix + s
