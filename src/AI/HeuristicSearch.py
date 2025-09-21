# Heuristic Search AI, HW 2 CS-421
# Authors:
# - Christopher Yee
# - Joshua Krasnogorov

import random
import sys
sys.path.append("..")  #so other modules can be found in parent dir
from Player import *
from Constants import *
from Construction import CONSTR_STATS
from Ant import UNIT_STATS
from Move import Move
from GameState import *
from AIPlayerUtils import *


##
# NODE
# Description: A node in the search tree; contains a game state, a move, the parent state,
# and the utility of the state.
##
class Node:
    # Use slots for memory optimization and fast attribute access -
    # HOWEVER  - we can't add new attributes dynamically now. This shouldn't be a problem tho
    __slots__ = ['parent', 'move', 'gameState', 'depth', 'evaluation']

    ## __init__
    #
    # Description: Creates a new node
    #
    # Parameters:
    #   parent - the parent node
    #   move - the move that led to this state
    #   gameState - the game state
    #   depth - how many steps to reach from the agent's actual state
    #   evalution - state depth + utility
    ##
    def __init__(self, parent, move, gameState, depth, evaluation):
        self.parent = parent
        self.move = move
        self.gameState = gameState
        self.depth = depth
        self.evaluation = evaluation

##
# expandNode
#
# Description: Expands a node to include all valid moves from the GameState in the given node
#
# Parameters:
#   node - a node
#
# Return: A list of all the new nodes that were created.
##
def expandNode(node):
    moves = listAllLegalMoves(node.gameState)
    nodes = []
    for move in moves:
        newNode = Node(node, move, getNextState(node.gameState, move), node.depth + 1, None)
        nodes.append(newNode)
    return nodes



##
# utility
#
# Description: Heuristic estimate of number of turns until a win (lower is better)
# Reminder: Do not use the board variable
#
# Parameters:
#   gameState - a game state
#
# Return: Estimated remaining turns to win (int, non-negative; large if far)
#
##
def utility(gameState):
        me = gameState.whoseTurn
        myInv = getCurrPlayerInventory(gameState)
        enemyInv = getEnemyInv(me, gameState)
        # Already winning -> zero remaining turns
        if gameState.phase == PLAY_PHASE and getWinner(gameState) == me:
            return 0

        estTurnsToFoodWin = foodUtility(gameState, myInv, enemyInv, me)
        print(f"Estimated turns to food win: {estTurnsToFoodWin}")
        try:
            return int(estTurnsToFoodWin)
        except Exception:
            return 10000


## foodUtility
# Description: Admissibly estimates how many turns it will take to gather
# 11 food (ie we win)
#
# Parameters:
#   gameState - a game state
#   myInv - the inventory of the current player
#   enemyInv - the inventory of the enemy
#   me - the id of the current player
#
# Return: The utility of the food situation
##
def foodUtility(gameState, myInv, enemyInv, me):
    # Return an estimate of the number of turns (player moves) needed
    # to reach 11 food by shuttling food with workers.
    # Uses Manhattan distance and worker movement points as an admissible, fast heuristic.
    LARGE_TURNS = 10000

    currentFood = myInv.foodCount if myInv and myInv.foodCount is not None else 0
    foodNeeded = max(0, 11 - currentFood)
    if foodNeeded == 0:
        return 0


    # Gather resources
    workers = getAntList(gameState, me, (WORKER,))
    if workers is None or len(workers) == 0 or len(workers) > 1:
        return LARGE_TURNS

    foods = getConstrList(gameState, None, (FOOD,))
    if foods is None or len(foods) == 0:
        return LARGE_TURNS

    dropSites = []
    anthill = myInv.getAnthill() if myInv else None
    tunnels = myInv.getTunnels() if myInv else []
    if anthill is not None:
        dropSites.append(anthill.coords)
    if tunnels:
        dropSites.extend([t.coords for t in tunnels])
    if len(dropSites) == 0:
        return LARGE_TURNS

    movementPerTurn = UNIT_STATS[WORKER][MOVEMENT]
    if movementPerTurn <= 0:
        return LARGE_TURNS


    def turns_for_distance(d):
        return (d + movementPerTurn - 1) // movementPerTurn

    # Compute a conservative cycle time starting from a drop site (drop -> food -> drop)
    minDropToFood = min(
        approxDist(d, f.coords)
        for d in dropSites
        for f in foods
    )
    cycleTurns = turns_for_distance(minDropToFood + minDropToFood)

    # For each worker, estimate time to first delivery (if carrying, just to nearest drop)
    firstDeliveryTimes = []
    for w in workers:
        if w.carrying:
            toDrop = min(approxDist(w.coords, d) for d in dropSites)
            firstDeliveryTimes.append(turns_for_distance(toDrop))
        else:
            # nearest food, then from that food to nearest drop
            nearestFood = min(foods, key=lambda f: approxDist(w.coords, f.coords))
            toFood = approxDist(w.coords, nearestFood.coords)
            toDropFromFood = min(approxDist(nearestFood.coords, d) for d in dropSites)
            firstDeliveryTimes.append(turns_for_distance(toFood) + turns_for_distance(toDropFromFood))

    # Schedule deliveries greedily across workers to fulfill foodNeeded
    nextAvailable = list(firstDeliveryTimes)
    # If cycleTurns is zero (edge case), subsequent deliveries are immediate
    lastDeliveryTime = 0
    for _ in range(foodNeeded):
        i = min(range(len(nextAvailable)), key=lambda idx: nextAvailable[idx])
        lastDeliveryTime = nextAvailable[i]
        nextAvailable[i] = nextAvailable[i] + cycleTurns

    return int(lastDeliveryTime)


## defenseUtility
# Description: Calculates the utility of the defense situation in a game state
#
# Parameters:
#   gameState - a game state
#   myInv - the inventory of the current player
#   enemyInv - the inventory of the enemy
#   me - the id of the current player
#
# Return: The utility of the attack situation
##
def defenseUtility(gameState, me):
    enemy = 1 - me
    def on_my_side(coords):
        y = coords[1]
        return (y <= 4)

    # Enemy ants on my side are threats
    threats = [a for a in getAntList(gameState, enemy, (QUEEN, WORKER, DRONE, SOLDIER, R_SOLDIER)) if on_my_side(a.coords)]
    # My attack-capable ants
    defenders = getAntList(gameState, me, (DRONE, SOLDIER, R_SOLDIER))

    # If no threats on my side, defense is perfect
    if not threats:
        return 1.0
    # If there are threats but no defenders, defense is bad
    if not defenders:
        return 0.0

    # Encourage defenders to be close to threats
    # 0 distance -> 1.0 score; distance >= maxDist -> 0.1 score
    maxDist = 10.0
    total = 0.0
    for t in threats:
        minDist = min(approxDist(d.coords, t.coords) for d in defenders)
        score = 1.0 - min(minDist / maxDist, 10.0)
        total += score

    proximityScore = total / len(threats)
    return max(0.0, min(1.0, proximityScore))


 ##
# bestMove
#
# Description: Searches a given list of game nodes to find the highest utility move
#
# Parameters:
#   gameState - a game state
#   moves - a list of moves
#
# Return: The state with the highest utility
#
def bestMove(nodes):
    # A*-style: choose node with minimal f = g(depth) + h(estimated turns)
    bestNodes = []
    bestF = None
    for node in nodes:
        if node.evaluation is None:
            node.evaluation = utility(node.gameState) + node.depth
        f = node.evaluation
        if bestF is None or f < bestF:
            bestF = f
            bestNodes = [node]
        elif f == bestF:
            bestNodes.append(node)
    return random.choice(bestNodes)


##
#AIPlayer
#Description: The responsibility of this class is to interact with the game by
#deciding a valid move based on a given game state. This class has methods that
#will be implemented by students in Dr. Nuxoll's AI course.
#
#Variables:
#   playerId - The id of the player.
##
class AIPlayer(Player):

    #__init__
    #Description: Creates a new Player
    #
    #Parameters:
    #   inputPlayerId - The id to give the new player (int)
    #   cpy           - whether the player is a copy (when playing itself)
    ##
    def __init__(self, inputPlayerId):
        super(AIPlayer,self).__init__(inputPlayerId, "Search Bot")
        self.playerId = inputPlayerId


    ##
    #getPlacement
    #
    #Description: called during setup phase for each Construction that
    #   must be placed by the player.  These items are: 1 Anthill on
    #   the player's side; 1 tunnel on player's side; 9 grass on the
    #   player's side; and 2 food on the enemy's side.
    #
    #Parameters:
    #   construction - the Construction to be placed.
    #   currentState - the state of the game at this point in time.
    #
    #Return: The coordinates of where the construction is to be placed
    ##
    def getPlacement(self, currentState):
        numToPlace = 0
        #implemented by students to return their next move
        if currentState.phase == SETUP_PHASE_1:    #stuff on my side
            numToPlace = 11
            moves = []
            for i in range(0, numToPlace):
                move = None
                while move == None:
                    #Choose any x location
                    x = random.randint(0, 9)
                    #Choose any y location on your side of the board
                    y = random.randint(0, 3)
                    #Set the move if this space is empty
                    if currentState.board[x][y].constr == None and (x, y) not in moves:
                        move = (x, y)
                        #Just need to make the space non-empty. So I threw whatever I felt like in there.
                        currentState.board[x][y].constr == True
                moves.append(move)
            return moves
        elif currentState.phase == SETUP_PHASE_2:   #stuff on foe's side
            enemyTunnel = getConstrList(currentState, None, (TUNNEL,))[0]
            enemyHill = getConstrList(currentState, None, (ANTHILL,))[0]

            # find all spots on enemy side of board that are empty
            furthestCoords = []
            for i in range(0, 10):
                for j in range(6, 10):
                    if currentState.board[i][j].constr == None:
                        furthestCoords.append((i,j))

            # sort spots by distance from enemy tunnel
            furthestCoords.sort(key=lambda x:
                        abs(enemyTunnel.coords[0] - x[0]) + abs(enemyTunnel.coords[1] - x[1]) +
                        abs(enemyHill.coords[0] - x[0]) + abs(enemyHill.coords[1] - x[1]))
            moves = []
            # add the two furthest spots to the moves list
            moves.append(furthestCoords[-1])
            moves.append(furthestCoords[-2])
            return moves
        else:
            return [(0, 0)]

    ##
    #getMove
    #Description: Gets the next move from the Player.
    #
    #Parameters:
    #   currentState - The state of the current game waiting for the player's move (GameState)
    #
    #Return: The Move to be made
    ##

    def getMove(self, currentState):

        frontierNodes = []
        expandedNodes = []
        rootNode = Node(None, None, currentState, 0, None)
        frontierNodes.append(rootNode)

        for i in range(3): # 3 is the depth of the search
            bestNode = bestMove(frontierNodes)
            frontierNodes.remove(bestNode)
            expandedNodes.append(bestNode)
            newNodes = expandNode(bestNode)
            frontierNodes.extend(newNodes)

        bestNode = bestMove(frontierNodes)
        while bestNode.depth > 1:
            bestNode = bestNode.parent
        return bestNode.move


    ##
    #getAttack
    #Description: Gets the attack to be made from the Player
    #
    #Parameters:
    #   currentState - A clone of the current state (GameState)
    #   attackingAnt - The ant currently making the attack (Ant)
    #   enemyLocations - The Locations of the Enemies that can be attacked (Location[])
    ##
    def getAttack(self, currentState, attackingAnt, enemyLocations):
        #Attack a random enemy.
        return enemyLocations[0]

    ##
    #registerWin
    #
    # This agent doens't learn
    #
    def registerWin(self, hasWon):
        #method templaste, not implemented
        pass


# Remove print statements for final version
# print("-------------------------------- STARTING TESTS -------------------------------- ")
totalTests = 4
passedTests = 0
# BEST MOVE TEST
# print("| Beginning bestMove test")
nodes = []
for i in range(10):
    node = Node(None, None, GameState.getBlankState(), 1, None)
    nodes.append(node)
    node.evaluation = i / 10 + node.depth
bestNode = bestMove(nodes)

if bestNode.evaluation == 1.9:
    # print(f"| BestMove test passed. Value was {bestNode.evaluation}, expected 1.9")
    passedTests += 1
else:
    print(f"| BestMove test failed. Value was {bestNode.evaluation}, expected 1.9")


# UTILITY TEST (now returns an estimated non-negative integer turns)
# print("| Beginning utility test")
gameState = GameState.getBlankState()
util = utility(gameState)
if not (isinstance(util, int) and util >= 0):
    print(f"| ERROR: utility() returned {util}, expected non-negative int")
else:
    # print(f"| Utility test passed. Value was {util} (turns)")
    passedTests += 1


# FOOD UTILITY TEST (now returns turn estimate, non-negative integer or LARGE)
# print("| Beginning food utility test")
gameState = GameState.getBasicState()
util_turns = foodUtility(gameState, getCurrPlayerInventory(gameState), getEnemyInv(0, gameState), 0)
if not (isinstance(util_turns, int) and util_turns >= 0):
    print(f"| ERROR: foodUtility() returned {util_turns}, expected non-negative int")
else:
    # print(f"| Food utility test passed. Value was {util_turns} (turns)")
    passedTests += 1


# DEFENSE UTILITY TEST
# print("| Beginning defense utility test")
gameState = GameState.getBasicState()
util = defenseUtility(gameState, 0)
if not 0.0 <= util <= 1.0:
    print(f"| ERROR: defenseUtility() returned {util}, expected 1.0")
else:
    # print(f"| Defense utility test passed. Value was {util}, expected 1.0")
    passedTests += 1

# print(f"|----------------------- Passed {passedTests} out of {totalTests} tests --------------------------- ")
# print("-------------------------------- ENDING TESTS -------------------------------- ")
