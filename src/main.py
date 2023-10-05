import os
from collections import deque
import networkx as nx
import matplotlib.pyplot as plt

from job import Job
from managers import CodeManager, OpcodeManager, StackManager
from constants import CODE_TYPE, OPCODE

def preprocess(file_name):
  # open the sample file used
  file = open(f'../resources/{file_name}')
    
  # read the content of the file opened
  code = file.readlines()

  data_index = code.index('.data\n')
  contract_code_manager = CodeManager(code[:data_index-1])
  transaction_code_manager = CodeManager(code[data_index+2:]) # +2 to skip the .data and 0:

  # close the file
  file.close()

  return contract_code_manager, transaction_code_manager

def plot(G, dir, file_name):
  plt.figure(figsize =(150, 150))
  options = {
      'node_color': 'green',
      'node_size': 1e4,
      'width': 5,
      'font_size': 15,
      'arrowsize': 10,
  }

  nx.draw_networkx(G, **options)
  plt.savefig(f"{dir}/{file_name}.png")

def execute(code_manager):

  # create job queue
  job_queue = deque()
  g = nx.DiGraph()

  # create a initial job and push to the job queue
  init_label_name = OpcodeManager.get_label_name(
    OpcodeManager.extract(code_manager.code[0])[1],
    OpcodeManager.extract(code_manager.code[0])[2]
  )

  g.add_node(init_label_name)
  job_queue.append(Job(init_label_name, 1))

  # initialize stack manager
  stack_manager = StackManager()

  # while job queue is not empty
  while job_queue:
    job = job_queue.popleft()

    while job.pc < len(code_manager.code):
      # get the code type, opcode, and operand
      type, opcode, operand = OpcodeManager.extract(code_manager.code[job.pc])
      job.pc += 1

      # stop, halt, return, revert, invalid, selfdestruct
      if opcode == 'STOP' or opcode == 'HALT' or opcode == 'RETURN' or opcode == 'REVERT' or opcode == 'INVALID' or opcode == 'SELFDESTRUCT':
        break

      # label
      elif type == CODE_TYPE.LABEL:
        label_name = OpcodeManager.get_label_name(opcode, operand)
        
        if g.has_edge(job.current_label_name, label_name):
          break # if the edge is already in the graph, do not add it again

        # add the edge from the previous node to the label
        g.add_edge(job.current_label_name, label_name)
        job.current_label_name = label_name

      # jump
      elif opcode == 'JUMP':
        # if jump, pop one value from the stack and change the pc to the new value
        dest = job.stack.pop()

        if 'tag' in dest: # ex. dest = '[tag] 1'
          tag_id = dest.split(' ')[1]
          job.pc = int(code_manager.label_hashmap[f"tag {tag_id}"])

        else:
          job.pc = int(dest)

      # jumpi
      elif opcode == 'JUMPI':
        # pop two values from the stack
        dest = job.stack.pop()
        job.stack.pop() # we don't use condition since we explore all paths

        if 'tag' in dest: # ex. dest = '[tag] 1'
          tag_id = dest.split(' ')[1]
          next_pc = int(code_manager.label_hashmap[f"tag {tag_id}"])

        else: # FIXME: jump dest address is being calculated out of stack values ex) tag 86
          next_pc = int(dest)

        # create a new job and push to the job queue
        job_queue.append(Job(job.current_label_name, next_pc, job.stack.copy()))


      # opcode
      elif type == CODE_TYPE.OPCODE:
        # use random value other than address of jumpdest
        [_, num_ins, num_outs, _] = stack_manager.opcodes[getattr(OPCODE, opcode)]
        
        # pop num_ins values from the stack
        for _ in range(num_ins):
          job.stack.pop()

        # push num_outs values to the stack
        for _ in range(num_outs):
          if 'PUSH' in opcode:
            job.stack.append(operand)

          elif 'DUP' in opcode:
            dup_index = int(opcode[3:])
            job.stack.append(job.stack[-dup_index])

          elif 'SWAP' in opcode:
            swap_index = int(opcode[4:])
            job.stack[-(swap_index+1)], job.stack[-1] = job.stack[-1], job.stack[-(swap_index+1)]

          else:
            job.stack.append('1') # random value

      else:
        pass

  return g

def main():
  for function in ['assembly_caInterest', 'assembly_UniswapV3Pool1']:
    dir_path = f'../outputs/{function}'
    os.makedirs(dir_path, exist_ok=True)

    # split the code into contract code and transaction code
    contract_code, transaction_code = preprocess(f'{function}.txt')

    # create a graph under /outputs
    contract_graph = execute(contract_code)
    transaction_graph = execute(transaction_code)

    # plot the graph (png)
    plot(contract_graph, dir_path, 'contract_graph')
    plot(transaction_graph, dir_path, 'transaction_graph')

if __name__ == "__main__":
  main()