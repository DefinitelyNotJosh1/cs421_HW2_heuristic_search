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
    #   utility - the utility of the state
    ##
    def __init__(self, parent, move, gameState, depth, evaluation):
        self.parent = parent
        self.move = move
        self.gameState = gameState
        self.depth = depth
        self.evaluation = evaluation



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
        super(AIPlayer,self).__init__(inputPlayerId, "Search")
        self.playerId = inputPlayerId


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
    def utility(self, gameState):
        # Some ideas: from Josh:
        # Food difference - this should absolutely play a decently large role.                          DONE
        # enemy ants - if the enemy has lots of ants and we don't, that's bad.                          DONE
        # worker ant distance from food - if worker isn't carrying food and close to food, that's good.
        # If worker ant is carrying food and close to a hill/tunnel, that's good.
        # If queen is within the attack range of an enemy ant, that's bad.
        #
        # Constants

       

        me = self.playerId
        myInv = getCurrPlayerInventory(gameState)
        enemyInv = getEnemyInv(me, gameState)
        enemy = 1 if me == 0 else 0
        utility = 0.0           
        # If I win in this game state, return 1
        if getWinner(gameState) == 1 - enemy:
            return 1.0                                                        # base

        # Food Weights - 90% of total utility
        if myInv.foodCount and enemyInv.foodCount:
            foodScore = myInv.foodCount / 11 # This is on a scale of 0 - 1 - good, now multiply by multiplier
            # foodScore -= (gameState.inventories[enemy].foodCount / 11) # ignore enemy food for now - 
            # in the future do this: start food score at 0.5, divide my food score by 2 and enemy food score by 2,
            # Add my food score and subtract enemy food score. This keeps everything on a scale of 0 - 1.
            print(f"Food Score: {foodScore}")
            utility += foodScore * 0.9
        # utility += (gameState.inventories[me].foodCount / 11) * 0.3                          # more food = more win; 0.3weight
        # utility -= (gameState.inventories[enemy].foodCount / 11) * 0.3                       # enemy more food /= more win; 0.3weight


        # If we're under attack (aka there are enemy ants on our side of the board, aka less than 4 in y coord)
        # Max 10% of total utility, not that important
        # attackScore = 0
        # enemyAnts = getAntList(gameState, enemy, (QUEEN, WORKER, DRONE, SOLDIER, R_SOLDIER))
        # attackingAnts = 0
        # if enemyAnts:
        #      for ant in enemyAnts:
        #         if ant.coords[1] < 4:
        #             attackingAnts += 1
        
        # print(f"attackScore: {attackScore}")
        # attackScore = ((len(enemyAnts)) - attackingAnts / len(enemyAnts)) # If there isn't a significant number of enemy attacking ants, good
        # utility += min(attackScore * 0.1, 0.1) 

        # Worker Weights
        # utility += (len(getAntList(gameState, me, (WORKER,))) / 3) * 0.2                     # more soldiers = more win; 0.2weight
        # utility -= (len(getAntList(gameState, enemy, (WORKER,))) / 3) * 0.2                  # enemy more soldiers = more win; 0.2weight
 

        # # Queen Weights
        # my_queens = getAntList(gameState, me, (QUEEN,))
        # enemy_queens = getAntList(gameState, enemy, (QUEEN,))

        # if my_queens and enemy_queens:  # Both queens exist
        #     utility += (max(0, my_queens[0].health - enemy_queens[0].health) / 10) * 0.2     # Protect the President/Queen; 0.2weight

        # # Anthill Weights
        # if gameState.inventories[enemy].getAnthill() or getCurrPlayerInventory(gameState).getAnthill():
        #     utility -= (gameState.inventories[enemy].getAnthill().captureHealth / 3) * 0.3       # Enemy anthill full health = bad; 0.3weight
        #     utility += (getCurrPlayerInventory(gameState).getAnthill().captureHealth / 3) * 0.3  # Anthill alive = good; 0.3weight

        # Worker Weights - 10% of total utility currently
        # Some help from ChatGPT
        workerScore = 0.0
        # Get my workers
        myWorkers = getAntList(gameState, 1 - enemy, (WORKER,))
        tunnels = myInv.getTunnels()
        anthill = myInv.getAnthill()
        foodList = getConstrList(gameState, None, (FOOD,))
        numWorkers = len(myWorkers)
        print(f"Workers: {myWorkers}")
        print(f"Num Workers: {numWorkers}")

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
                print(f"Worker {i} contrib: {contrib}")

        print(f"Worker Score: {workerScore}")
        # Ensure workerScore in [0,1]
        workerScore = max(0.0, min(1.0, workerScore))
        utility += (workerScore * 0.1) # 10% for now
        # Clamp result to [0,1]
        utility = min(utility, 1.0)
        print(f"Utility: {utility}")

        return utility


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
    def bestMove(self, nodes):
        # Initialize the best node with the first node's utility
        bestNodes = [nodes[0]]

        # Iterate through nodes to find the one with the highest utility
        for node in nodes:
            if node.evaluation is None:
                node.evaluation = self.utility(node.gameState) + node.depth
            if (node.evaluation - node.depth > bestNodes[0].evaluation - bestNodes[0].depth):
                bestNodes = [node]
            elif (node.evaluation - node.depth == bestNodes[0].evaluation - bestNodes[0].depth):
                bestNodes.append(node)

        return random.choice(bestNodes)


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
            numToPlace = 2
            moves = []
            for i in range(0, numToPlace):
                move = None
                while move == None:
                    #Choose any x location
                    x = random.randint(0, 9)
                    #Choose any y location on enemy side of the board
                    y = random.randint(6, 9)
                    #Set the move if this space is empty
                    if currentState.board[x][y].constr == None and (x, y) not in moves:
                        move = (x, y)
                        #Just need to make the space non-empty. So I threw whatever I felt like in there.
                        currentState.board[x][y].constr == True
                moves.append(move)
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
        bestNode = self.bestMove(nodes)

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
        return enemyLocations[random.randint(0, len(enemyLocations) - 1)]

    ##
    #registerWin
    #
    # This agent doens't learn
    #
    def registerWin(self, hasWon):
        #method templaste, not implemented
        pass


# UNIT TESTS
if __name__ == "__main__":
    gameState = GameState.getBlankState()
    AI = AIPlayer(0)

    util_range = AI.utility(gameState)
    if not 0.0 <= util_range <= 1.0:
        print(f"ERROR: utility() returned {util_range}")

    placements = AI.getPlacement(gameState)
    if not isinstance(placements, list) or len(placements) == 0:
        print("ERROR: getPlacement() did not return a valid list of coordinates")

    # move = AI.getMove(gameState)
    # if not isinstance(move, Move):
    #     print(f"ERROR: getMove() did not return a Move. Got: {move}")

    print("Beginning bestMove test")
    nodes = []
    for i in range(10):
        node = Node(None, None, GameState.getBlankState(), 1, None)
        nodes.append(node)
        node.evaluation = i / 10 + node.depth
    bestNode = AIPlayer(0).bestMove(nodes)

    if bestNode.evaluation == 1.9:
        print(f"BestMove test passed. Value was {bestNode.evaluation}, expected 1.9")
    else:
        print(f"BestMove test failed. Value was {bestNode.evaluation}, expected 1.9")


    print("Beginning utility test")
    gameState = GameState.getBlankState()
    util = AIPlayer(0).utility(gameState)
    if not 0.0 <= util <= 1.0:
        print(f"ERROR: utility() returned {util}")
    else:
        print(f"Utility test passed. Value was {util}, expected 0.0")


