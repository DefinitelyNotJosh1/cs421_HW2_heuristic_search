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
# utility
#
# Description: Calculates the utility of a given game state on a scale of 0 to 1
# Reminder: Do not use the board variable
#
# Parameters:
#   gameState - a game state
#
# Return: The utility of the state
#
##
def utility(gameState):
        # Some ideas: from Josh:
        # Food difference - this should absolutely play a decently large role.                          DONE
        # enemy ants - if the enemy has lots of ants and we don't, that's bad.                          DONE

        # Constants
        me = gameState.whoseTurn
        myInv = getCurrPlayerInventory(gameState)
        enemyInv = getEnemyInv(me, gameState)
        utility = 0.0
        # If I win in this game state, return 1
        if gameState.phase == PLAY_PHASE:
            if getWinner(gameState) == me:
                return 1.0                                                        # base

        # food stuff - 60% of total utility
        foodScore = foodUtility(gameState, myInv, enemyInv, me)
        # print(f"Food Score: {foodScore}")
        if foodScore:
            utility += foodScore * 0.6

        # defense stuff - 40% of total utility
        defenseScore = defenseUtility(gameState, me)
        if defenseScore:
            utility += defenseScore * 0.40

        # attack stuff - 20% of total utility
        attackScore = attackUtility(gameState, me) * 0.2
        if attackScore:
            utility += attackScore

        # print(f"Utility: {utility}")

        utility = min(utility, 0.99999999999999999)
        return utility


## foodUtility
# Description: Calculates the utility of the food situation in a game state
# Includes worker utility
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
    utility = 0.0
    # Food Weights - 90% of total utility
    if myInv.foodCount is not None and enemyInv.foodCount is not None:
        foodScore = 0.5
        foodScore += (myInv.foodCount / 11) * 0.5 # This is on a scale of 0 - 1 - good, now multiply by multiplier
        foodScore -= (enemyInv.foodCount / 11) * 0.5
        # print(f"Food Score: {foodScore}")
        utility += foodScore * 0.97


        # Some help from ChatGPT
        workerScore = 0.0
        # Get my workers
        myWorkers = getAntList(gameState, me, (WORKER,))
        tunnels = myInv.getTunnels()
        anthill = myInv.getAnthill()
        foodList = getConstrList(gameState, None, (FOOD,))
        numWorkers = len(myWorkers)
        # print(f"Workers: {myWorkers}")
        # print(f"Num Workers: {numWorkers}")

        # If we have no workers, score is 0
        if numWorkers == 0:
            return 0.0

        # If we have too many workers, aka not good
        if numWorkers > 2:
            utility -= 0.1

        # Avoid division by zero; if no workers, score remains 0
        if numWorkers > 0:
            # Precompute drop sites
            dropSites = []
            if anthill:
                dropSites.append(anthill.coords)
            if tunnels:
                dropSites.extend([t.coords for t in tunnels])

            # Normalization constants keep per-worker contribution in [0,1]
            maxFoodDist = 8.0
            maxDropDist = 8.0

            for i, w in enumerate(myWorkers):
                contrib = 0.0

                if w.carrying:
                    # If at drop site: full contribution
                    if dropSites and any(w.coords == d for d in dropSites):
                        contrib = 1.0
                    else:
                        # Positive baseline for carrying so picking up is attractive
                        if dropSites:
                            closestDrop = min(approxDist(w.coords, d) for d in dropSites)
                            progressToDrop = max(0.0, min(1.0, 1.0 - (closestDrop / maxDropDist)))
                        else:
                            progressToDrop = 0.0
                        # Baseline 0.5 plus progress up to 1.0 max
                        contrib = 0.5 + 0.5 * progressToDrop
                else:
                    # Not carrying: incentivize getting closer to nearest food, but cap at 0.5
                    if foodList:
                        closestFood = min(approxDist(w.coords, f.coords) for f in foodList)
                        towardFood = max(0.0, min(1.0, 1.0 - (closestFood / maxFoodDist)))
                        contrib = 0.5 * towardFood
                    else:
                        contrib = 0.0

                # Clamp and average across workers
                contrib = max(0.0, min(1.0, contrib))
                workerScore += contrib / numWorkers
                # print(f"Worker {i} contrib: {contrib}")

        # print(f"Worker Score: {workerScore}")
        # Ensure workerScore in [0,1]
        workerScore = max(0.0, min(1.0, workerScore))
        utility += (workerScore * 0.03)
        utility = min(utility, 1.0)
        return utility


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


## attackUtility
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
def attackUtility(gameState, me):
    enemy = 1 - me
    attackScore = 0.0
    myAttackAnts = getAntList(gameState, me, (DRONE, SOLDIER, R_SOLDIER, QUEEN))
    enemyAnts = getAntList(gameState, enemy, (WORKER, DRONE, SOLDIER, R_SOLDIER, QUEEN))

    for ant in myAttackAnts:
        for enemy in enemyAnts:
            distance = approxDist(ant.coords, enemy.coords)

            if distance == 1:
                # Prioritize Queen, then Soldier and RSoldier, and finally Worker
                if enemy.type == QUEEN:
                    attackScore += 0.4
                elif enemy.type == SOLDIER or enemy.type == R_SOLDIER:
                    attackScore += 0.3
                elif enemy.type == WORKER:
                    attackScore += 0.2
                else:
                    attackScore += 0.1
                # If they enemy has low HP
                if enemy.health <= 1:
                    attackScore += 0.2

    return max(0.0, min(1.0, attackScore))

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
    # Initialize the best node with the first node's utility
    bestNodes = [nodes[0]]

    # Iterate through nodes to find the one with the highest utility
    for node in nodes:
        if node.evaluation is None:
            node.evaluation = utility(node.gameState) + node.depth
        if (node.evaluation - node.depth > bestNodes[0].evaluation - bestNodes[0].depth):
            bestNodes = [node]
        elif (node.evaluation - node.depth == bestNodes[0].evaluation - bestNodes[0].depth):
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
        super(AIPlayer,self).__init__(inputPlayerId, "Search Bot1")
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
        moves = listAllLegalMoves(currentState)

        # list all gamestate objects that will result from making each legal move
        nodes = []
        for move in moves:
            newNode = Node(currentState, move, getNextState(currentState, move), 1, None)
            nodes.append(newNode)
            # print(f"Node {len(nodes)}: {newNode.evaluation}")

        # find the best move
        bestNode = bestMove(nodes)

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
        # return enemyLocations[0]
        # Gets all the ants on the board
        enemyID = 1 - self.playerId
        enemyWorkers = getAntList(currentState, enemyID, (WORKER,))
        enemyDrone = getAntList(currentState, enemyID, (DRONE,SOLDIER,R_SOLDIER,QUEEN))
        queen = getAntList(currentState, self.playerId, (QUEEN,))[0]

        # Gets the coords of all ants
        coordsList = [ant.coords for ant in enemyDrone]
        enemyWorker = enemyWorkers[0].coords if enemyWorkers else None
        enemyQueen = getAntList(currentState, enemyID, (QUEEN,))[0].coords

        # Finds nearest ant to the queen if there is one; #ManhattanDistance
        nearest = min(coordsList, key=lambda coord: approxDist(coord, queen.coords))

        if enemyQueen in enemyLocations:
            return enemyQueen
        elif enemyWorker in enemyLocations:
            return enemyWorker
        elif nearest in enemyLocations:
            return nearest
        else:
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


# UTILITY TEST
# print("| Beginning utility test")
gameState = GameState.getBlankState()
util = utility(gameState)
if not 0.0 <= util <= 1.0:
    print(f"| ERROR: utility() returned {util}, expected 0.4")
else:
    # print(f"| Utility test passed. Value was {util}, expected 0.4")
    passedTests += 1


# FOOD UTILITY TEST
# print("| Beginning food utility test")
gameState = GameState.getBasicState()
util = foodUtility(gameState, getCurrPlayerInventory(gameState), getEnemyInv(0, gameState), 0)
if not 0.0 <= util <= 1.0:
    print(f"| ERROR: foodUtility() returned {util}, expected 0.0")
else:
    # print(f"| Food utility test passed. Value was {util}, expected 0.0")
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
