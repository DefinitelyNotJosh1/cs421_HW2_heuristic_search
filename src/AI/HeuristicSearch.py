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
        enemy = 1 if me == 0 else 0
        utility = 0.500                         # base
        myInv = getCurrPlayerInventory(gameState)
        tunnels = myInv.getTunnels()
        anthill = myInv.getAnthill()
        foodList = getConstrList(gameState, None, (FOOD,))

        # Food Weights
        utility += (gameState.inventories[me].foodCount / 11) * 0.3                          # more food = more win; 0.3weight
        # utility -= (gameState.inventories[enemy].foodCount / 11) * 0.3                       # enemy more food /= more win; 0.3weight

        # Soldier Weights
        utility += (len(getAntList(gameState, me, (SOLDIER,R_SOLDIER))) / 10) * 0.2          # more soldiers = more win; 0.2weight
        # utility -= (len(getAntList(gameState, enemy, (DRONE,SOLDIER,R_SOLDIER))) / 10) * 0.2 # enemy more soldiers = more lose; 0.2weight

        # Worker Health Weights
        workers = getAntList(gameState, me, (WORKER,))
        if workers:  # Only if workers exist
            utility += (len(workers) / 2) * 0.2

            worker_health = sum(w.health for w in workers)
            utility += (worker_health / 3.0) / len(workers) * 0.3
            utility -= (len(workers) / 2) * 0.2

        # # Queen Weights
        my_queens = getAntList(gameState, me, (QUEEN,))
        enemy_queens = getAntList(gameState, enemy, (QUEEN,))
        if my_queens and enemy_queens:  # Both queens exist
            utility += ((my_queens[0].health - enemy_queens[0].health) / 10) * 0.2     # Protect the President/Queen; 0.2weight
            # utility += (my_queens[0].health / 10) * 0.2

        # Anthill Weights
        if gameState.inventories[enemy].getAnthill() or getCurrPlayerInventory(gameState).getAnthill():
            utility -= (gameState.inventories[enemy].getAnthill().captureHealth / 3) * 0.3       # Enemy anthill full health = bad; 0.3weight
            utility += (anthill.captureHealth / 3) * 0.3  # Anthill alive = good; 0.3weight

        # ChatGPT
        # Worker Weights
        workerScore = 0
        # Get my workers
        workers = getAntList(gameState, me, (WORKER,))

        for w in workers:
            # if blocking
            if my_queens and w.coords == my_queens[0].coords:
                utility -= 0.3
            # If carrying food, prioritize returning to tunnel or anthill
            if w.carrying:
                closestDrop = min(stepsToReach(gameState, w.coords, tunnels[0].coords),
                                  stepsToReach(gameState, w.coords, anthill.coords))
                if closestDrop == 0:
                    workerScore += 20
                else:
                    workerScore += max(0, 10 - closestDrop)   # closer to drop site is better
            else:
                # If not carrying, prioritize the closest food
                closestFood = min([stepsToReach(gameState, w.coords, f.coords) for f in foodList])
                if closestFood == 0:
                    workerScore += 10
                else:
                    workerScore += max(0, 5 - closestFood)   # closer to food is better

        print(f"Base utility: {utility}")
        print(f"Worker score: {workerScore}")
        print(f"Final utility before clamp: {utility + workerScore * 0.01}")
        utility += workerScore * 0.1
        # Clamp result to [0,1]
        utility = max(0.0, min(1.0, utility))

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
        bestNodes = []

        # Iterate through nodes to find the one with the highest utility
        for node in nodes:
            if node.evaluation is None:
                node.evaluation = self.utility(node.gameState) + node.depth + random.uniform(-0.01, 0.01)   # noise
            if ((node.evaluation - node.depth >= nodes[0].evaluation) -
                    (bestNodes[len(bestNodes) - 1].depth if len(bestNodes) != 0 else nodes[0].evaluation)):
                bestNodes.append(node)

        return random.choice(bestNodes) if len(bestNodes) != 0 else nodes[0]


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
    #   enemyLocation - The Locations of the Enemies that can be attacked (Location[])
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


