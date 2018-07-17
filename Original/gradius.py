import os
import subprocess
import sys
import math
import neat
import visualize
import signal
import matplotlib.pyplot as plt
from distutils import spawn


SEARCH_PATH = os.pathsep.join([os.environ['PATH'], '/usr/games', '/usr/local/games'])
FCEUX_PATH = spawn.find_executable('fceux', SEARCH_PATH)
if FCEUX_PATH is None:
    print("Não foi encontrado o emulador FCEUX na variável PATH. Verifique!")

SCORE = 0
GENERATION = 0
MAX_FITNESS = 0
BEST_GENOME = 0
TOTAL_FITNESS = 0

CONTROL = True

max_frame = 0
isInitialized = 0
rom_path = '/home/alan/Aula/TCC/rom/gradius.nes'
lua_path = '/home/alan/Aula/TCC/gradius.lua'
cmd_args = ['--xscale 2', '--yscale 2', '-f 0']
pipe_out = None
path_pipe_out = '/home/alan/Aula/TCC/pipeout'
path_pipe_in = '/home/alan/Aula/TCC/pipein'
subprocessx = None
commands     = {}
python_frame = 1
lua_frame    = 0
alive        = 0
vicx         = 0
vicy         = 0
enemies      = []

def resetVars():
    global commands, python_frame, enemies, python_frame, alive, lua_frame, vicx, vicy, isInitialized
    for c in range(len(commands)):
        commands[c] = 0
    enemies      = []
    python_frame = 1
    alive        = 0
    lua_frame    = 0
    vicx         = 0
    vicy         = 0

def setCommands(commandlist):
    commandstring = "#"
    for i in commandlist:
        if(i):
            commandstring = commandstring + "1,"
        else:
            commandstring = commandstring + "0,"
    return commandstring[:-1]
            
def create_pipes():
    if(not os.path.exists(path_pipe_out)):
        os.mkfifo(path_pipe_out)
    if(not os.path.exists(path_pipe_in)):
        os.mkfifo(path_pipe_in)

def write_pipe(value):
    global pipe_out
    #print("Python enviou: " + value)
    try:
        if pipe_out is None:
            pipe_out = open(path_pipe_out, 'w', 1)
        pipe_out.write(value + '\n')
    except IOError:
        pipe_out = None

def close_pipe():
    global pipe_out
    if pipe_out is not None:
        pipe_out = pipe_out
        pipe_out = None
        try:
            pipe_out.close()
        except BrokenPipeError:
            pass
    
def sendCommand(command):
    global isInitialized, subprocessx, pipe_out
    if(not isInitialized):
        if(not os.path.isfile(rom_path)):
            close_pipe()
            sys.exit("Rom não contrada em " + rom_path)

        create_pipes()

        args = [FCEUX_PATH]
        args.extend(cmd_args[:])
        args.extend(['--loadlua', lua_path])
        args.append(rom_path)
        args.extend(['&'])
        subprocessx = subprocess.Popen(' '.join(args), shell=True)
        subprocessx.communicate()
        if 0 == subprocessx.returncode:
            isInitialized = 1
            try:
                pipe_out = open(path_pipe_out, 'w', 1)
            except IOError:
                pipe_out = None
        else:
            close_pipe()
            sys.exit("Não foi possível inicializar o emulador")
        write_pipe(command)
    else:
        write_pipe(command)

def reciveFeedback(a = None, b = None):
    try:
        pipe_in = open(path_pipe_in, 'r')
    except IOError:
        pipe_in = None

    if pipe_in is not None:
        message = pipe_in.readline()
        processMessage(message)
        try:
            pipe_in.close()
        except BrokenPipeError:
            pass
    
def processMessage(message):
    global lua_frame, python_frame, vicx, vicy, alive, enemies
    parts        = message.split(sep="#")
    lua_frame    = int(parts[0])
    python_frame = lua_frame + 1
    positions    = parts[1].split(sep=",")
    vicx         = int(positions[0])
    vicy         = int(positions[1])
    alive        = int(parts[2])
    strenemies   = parts[3].split("!")
    enemies      = []
    for i, value in enumerate(strenemies[:-1]):
        parts = value.split(",")
        parts = [int(j) for j in parts]
        parts.append(int(math.hypot(parts[1] - vicx, parts[2] - vicy)))
        if(parts[1] != 0):
            enemies.append(parts)

def calcCommands():
    global enemies, vicx, vicy
    commands_ = []
    ahead = 50
    most_dang = [0,0,0, 255]
    commandstring = "#" + "np"
    if len(enemies) > 0:
        for e in enemies:
            if(e[-1] < most_dang[-1]):
                most_dang = e
                
        if (most_dang[1] - vicx) < ahead:
            distance = abs(most_dang[2] - vicy)
            if distance < 60:
                if(most_dang[2] < vicy):
                    commands_ = [0,1,1,0,0,0,0,0]
                else:
                    commands_ = [1,0,1,0,0,0,0,0]
            else:
                return ("#" + "np")
        elif (vicx < 60):
            commands_ = [0,0,0,1,0,0,0,0]
        else:
            commandstring = "#" + "np"
            return commandstring    
        commandstring = "#" + "cc" + setCommands(commands_)
    else:
        commandstring = "#" + "np"
        
    return commandstring

def eval_genomes(genomes, config):
	i = 0
	global SCORE
	global GENERATION, MAX_FITNESS, BEST_GENOME

	GENERATION += 1
	for genome_id, genome in genomes:
		
		genome.fitness = run(genome, config)
		print("Gen : %d Genome # : %d  Fitness : %f Max Fitness : %f"%(GENERATION,i,genome.fitness, MAX_FITNESS))
		if genome.fitness >= MAX_FITNESS:
			MAX_FITNESS = genome.fitness
			BEST_GENOME = genome
		SCORE = 0
		i+=1

def run(genome, config):

    net = neat.nn.FeedForwardNetwork.create(genome, config)
    global SCORE, CONTROL, vicx, vicy, max_frame
    last_printed = 0
    fitness = 0
    calcfit = 0
    while True:
        if python_frame > max_frame:
            max_frame = python_frame        
        #print("alive: " + str(alive) + ", frame:" + str(python_frame))
        commandstring = ""
        if (alive != 2):
            if((python_frame % 2) == 0):
                if(alive == 0):
                    CONTROL = True
                    commands = [0,0,0,0,0,0,1,0]
                    commandstring = "#" + "cc"
                    commandstring = commandstring + setCommands(commands)
                else:                    
                    input_ = [python_frame]
                    #input_ = [vicx + python_frame, vicy]
                    input_.extend([vicx, vicy])
                    j = len(enemies)
                    k = 0
                    while (k < j) and (k < 10):
                        enemy = enemies[k]
                        #enemy[0] = enemy[0] + python_frame 
                        input_.extend(enemy)
                        fitness = python_frame
                        if(enemy[0] == 2):
                            calcfit += 1
                        if(enemy[3] < 10):
                            if(enemy[0] > 100 and enemy[0] < 300):
                                calcfit -= 0.1
                            if(enemy[0] == 999):
                                calcfit -= 10
                        k += 1
                    while k < 10:
                        l = [-1, -1, -1, -1]
                        input_.extend(l)
                        k += 1
                    #fitness = SCORE + python_frame
                    output = net.activate(input_)
                    for i, o in enumerate(output):
                        if o < 0.5:
                            output[i] = 0
                        else:
                            output[i] = 1     
                    if(output[0] == 1 and output[1] == 1):
                        output[0] = 0
                        output[1] = 0
                    if(output[2] == 1 and output[3] == 1):
                        output[2] = 0
                        output[3] = 0
                    rest_output = [0,0,0]
                    output.extend(rest_output)                                   
                    #print(output)
                    #print(fitness)
                    commandstring = "#" + "cc"
                    commandstring = commandstring + setCommands(output)
            else:
                commandstring = "#" + "np"        
        else:
            resetVars()
            commandstring = "#" + "re"
            
        fullstring = str(python_frame) + commandstring
        if(commandstring == "#re" and CONTROL):
            CONTROL = False
            #print(fitness)
            return (fitness + calcfit)
        sendCommand(fullstring)
        reciveFeedback()
    



local_dir = os.path.dirname(__file__)
config_path = os.path.join(local_dir, 'config')
config = neat.Config(neat.DefaultGenome,
                     neat.DefaultReproduction,
                     neat.DefaultSpeciesSet,
                     neat.DefaultStagnation,
                     config_path)

range_ = 1
geracoes = 50
fitness = 0



best_fitness = 0

for i in range(range_):
    pop = neat.Checkpointer.restore_checkpoint('neat-checkpoint-15.gz')

    stats = neat.StatisticsReporter()
    pop.add_reporter(stats)
    pop.add_reporter(neat.StdOutReporter(True))
    pop.add_reporter(neat.Checkpointer(geracoes, 100))

    winner = pop.run(eval_genomes, geracoes)
    fitness += MAX_FITNESS
    if MAX_FITNESS > best_fitness:
        best_fitness = MAX_FITNESS
    MAX_FITNESS = 0
    GENERATION = 0
    BEST_GENOME = 0
print("Mean fitness: " + str(fitness/range_))
print("Best fitness: " + str(best_fitness))
print("Max frame: " + str(max_frame))