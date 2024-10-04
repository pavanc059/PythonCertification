import random

board = [[1,2,3],[4,'X',6],[7,8,9]]

int_value_dict = {
    1: [0,0],
    2: [0,1],
    3: [0,2],
    4: [1,0],
    5: [1,1],
    6: [1,2],
    7: [2,0],
    8: [2,1],
    9: [2,2]}

def display_board(board):
    # The function accepts one parameter containing the board's current status
    # and prints it out to the console.
    one = f'  {board[0][0]}  '
    two = f'  {board[0][1]}  '
    three = f'   {board[0][2]}   '
    fou = f'  {board[1][0]}  '
    fiv = f'  {board[1][1]}  '
    six = f'  {board[1][2]}  '
    sev = f'  {board[2][0]}  '
    eit = f'  {board[2][1]}  '
    nin = f'  {board[2][2]}  '
    
    print(f'''
    +-------+-------+-------+
    |       |       |       |
    | {one} | {two} |{three}|
    |       |       |       |
    +-------+-------+-------+
    |       |       |       |
    | {fou} | {fiv} | {six} |
    |       |       |       |
    +-------+-------+-------+
    |       |       |       |
    | {sev} | {eit} | {nin} |
    |       |       |       |
    +-------+-------+-------+
    ''')


def enter_move(board):
    # The function accepts the board's current status, asks the user about their move, 
    # checks the input, and updates the board according to the user's decision.
    free_fields = make_list_of_free_fields(board)
    if len(free_fields) == 0:
        print('Draw')
        display_board(board)
        return False
    display_board(board)
    move = int(input('Enter your move: '))
    if move > 9 or move < 1:
        print('Invalid move')
        enter_move(board)
    if move == 1 and (board[0][0] != 'O' or board[0][0] != 'X') :
        board[0][0] = 'O'
        display_board(board)
    elif move == 2 and (board[0][1] != 'O' or board[0][1] != 'X'):
        board[0][1] = 'O'
        display_board(board)
    elif move == 3 and (board[0][2] != 'O' or board[0][2] != 'X'):
        board[0][2] = 'O'
        display_board(board)
    elif move == 4 and (board[1][0] != 'O' or board[1][0] != 'X'):
        board[1][0] = 'O'
        display_board(board)
    elif move == 5 and (board[1][1] != 'O' or board[1][1] != 'X'):
        board[1][1] = 'O'
        display_board(board)
    elif move == 6 and (board[1][2] != 'O' or board[1][2] != 'X'):
        board[1][2] = 'O'
        display_board(board)
    elif move == 7 and (board[2][0] != 'O' or board[2][0] != 'X'):
        board[2][0] = 'O'
        display_board(board)
    elif move == 8 and (board[2][1] != 'O' or board[2][1] != 'X'):
        board[2][1] = 'O'
        display_board(board)
    elif move == 9 and (board[2][2] != 'O' or board[2][2] != 'X'):
        board[2][2] = 'O'
        display_board(board)
    else:
        print('Invalid move')
        enter_move(board)
    
    if victory_for(board, 'O'):
        print('You won')
        display_board(board)       
        return
  
    draw_move(board)
    enter_move(board)


def make_list_of_free_fields(board):
    # The function browses the board and builds a list of all the free squares; 
    # the list consists of tuples, while each tuple is a pair of row and column numbers.
    free_fields_list = []
    for index_x, x in enumerate(board):
        for index_y, y in enumerate(x):
            if y != 'O' and y != 'X':
                free_fields_list.append((index_x,index_y))
    return free_fields_list
                


def victory_for(board, sign):
    # The function analyzes the board's status in order to check if 
    # the player using 'O's or 'X's has won the game
    possible_wins = [
        [(0, 0), (0, 1), (0, 2)],
        [(1, 0), (1, 1), (1, 2)],
        [(2, 0), (2, 1), (2, 2)],
        [(0, 0), (1, 0), (2, 0)],
        [(0, 1), (1, 1), (2, 1)],
        [(0, 2), (1, 2), (2, 2)],
        [(0, 0), (1, 1), (2, 2)],
        [(0, 2), (1, 1), (2, 0)]
    ]   

    for win in possible_wins:
        win_counter = 0
        for x in win:
            if board[x[0]][x[1]] == sign:
                print(f'Values on board {board[x[0]][x[1]]}')
                win_counter += 1
                continue
            else:
                break
        if win_counter == 3:
            return True
        

            
            

           
        


def draw_move(board):
    # The function draws the computer's move and updates the board.
    value = random.randint(1, 9)
    print(value)
    print(f'random value {value} and current value in position {board[int_value_dict[value][0]][int_value_dict[value][1]]}')
    if board[int_value_dict[value][0]][int_value_dict[value][1]] != 'X' and  board[int_value_dict[value][0]][int_value_dict[value][1]] != 'O':
        board[int_value_dict[value][0]][int_value_dict[value][1]] = 'X'       
    else:
        draw_move(board)

    if victory_for(board, 'X'):
        print('You lose')
        display_board(board)
        return

#display_board(board)

#print(make_list_of_free_fields(board))
enter_move(board)
