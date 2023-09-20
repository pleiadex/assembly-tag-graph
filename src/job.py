from collections import deque

class Job:
  def __init__(self, current_label_name, pc, stack=deque()):
    self.current_label_name = current_label_name
    self.pc = pc
    self.stack = stack