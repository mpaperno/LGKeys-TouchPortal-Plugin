
import json

class Logger:
  def __init__(self, logger):
    self.logger = logger
    self.dbg = logger.debug
    self.info = logger.info
    self.warn = logger.warning
    self.err = logger.error
    self.crit = logger.critical

  def format_json(self, data):
    return json.dumps(data, indent=2)
