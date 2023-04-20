import sqlite3
import random
from datetime import datetime, timedelta
from scoregenerator import Golfer, Hole, create_score, get_golfers_from_db
from sqlalchemy.sql._elements_constructors import false


conn = sqlite3.connect('golf2.db')
c = conn.cursor()

c.execute("""
    SELECT Players.name, Players.Rating, 
           AVG(CASE WHEN PGA_stats.STAT_ID = 142 THEN PGA_stats.AVERAGE END) AS par3avg,
           AVG(CASE WHEN PGA_stats.STAT_ID = 143 THEN PGA_stats.AVERAGE END) AS par4avg,
           AVG(CASE WHEN PGA_stats.STAT_ID = 144 THEN PGA_stats.AVERAGE END) AS par5avg
    FROM Players 
    JOIN PGA_stats ON Players.name = PGA_stats.player
    WHERE PGA_stats.STAT_ID IN (142, 143, 144)
    GROUP BY Players.name, Players.Rating;
""")
PGA_stats = c.fetchall()

c.execute('SELECT players_id, name, tour, human, rating FROM Players')
all_players = c.fetchall()

all_players_dict = {player[0]: {'name': player[1], 'tour': player[2], 'human': player[3], 'rating': player[4]} for player in all_players}


for row in PGA_stats:
    name = row[0]
    rating = row[1]
    par3avg = row[2]
    par4avg = row[3]
    par5avg = row[4]
    #print(f"{name}, {rating}, {par3avg}, {par4avg}, {par5avg}")

active_season = 2023
active_week = 1
human = False


gen_scores_calls = 0
update_pos_calls = 0
golfers = get_golfers_from_db()
golfer_instances = {golfer.player_id: golfer for golfer in golfers}

cut_score = 0

# Retrieve active_tid from the schedule table based on active_week and active_season
c.execute('SELECT schedule_id FROM schedule WHERE week=? AND season=?', (active_week, active_season))
active_tid = c.fetchone()[0]


def get_player_id(name, tid):
    c.execute('SELECT player_id FROM scores WHERE name = ? AND tid = ?', (name, tid))
    result = c.fetchone()
    if result:
        return result[0]
    else:
        return None


def get_field(field_size=156):
    c.execute('SELECT players_id, name, tour, human, rating FROM Players')
    all_players = c.fetchall()
    human_players = [player for player in all_players if player[3]]

    include_human = False
    chosen_human = None
    while True:
        human_playing = input("Will a human be playing? (yes/no): ").lower()
        if human_playing == "yes":
            if human_players:
                include_human = True
                print("Select a human player:")
                for idx, player in enumerate(human_players, start=1):
                    print(f"{idx}. {player[1]}")
                while True:
                    try:
                        choice = int(input("Enter the number of the chosen player: "))
                        if 1 <= choice <= len(human_players):
                            chosen_human = human_players[choice - 1]
                            break
                        else:
                            print("Invalid choice. Please choose a valid number.")
                    except ValueError:
                        print("Invalid input. Please enter a number.")
            else:
                print("No human players found.")
                include_human = False
            break
        elif human_playing == "no":
            include_human = False
            break
        else:
            print("Invalid input. Please enter 'yes' or 'no'.")

    if not include_human:
        all_players = [player for player in all_players if not player[3]]

    selected_players = []
    ids = []

    if include_human:
        selected_players.append({'player_id': chosen_human[0], 'name': chosen_human[1], 'rating': chosen_human[4]})
        ids.append(chosen_human[0])
        #yesfield_size -= 1

    while len(selected_players) < field_size and all_players:
        player = random.choice(all_players)
        if player[0] not in ids and random.randint(1, 100) in range(20, 81):
            selected_players.append({'player_id': player[0], 'name': player[1], 'rating': player[4]})
            ids.append(player[0])
        all_players.remove(player)

        if not all_players:
            c.execute(f"SELECT players_id, name, tour, human, rating FROM Players WHERE players_id NOT IN ({', '.join('?' for _ in ids)})", ids)
            all_players = c.fetchall()
            if not include_human:
                all_players = [player for player in all_players if not player[3]]

    return selected_players, include_human



def set_tee_times(field, round_num, playerData):
    player_tee_times = {}
    r2_tee_times = {}

    if round_num == 1:
        random.shuffle(field)    
    if round_num in [3, 4]:
#        field.reverse()
        sorted_field = sorted(field, key=lambda x: x['total'], reverse=True)

    hole_order1 = list(range(1, 19))
    hole_order10 = [10, 11, 12, 13, 14, 15, 16, 17, 18, 1, 2, 3, 4, 5, 6, 7, 8, 9]

    if round_num == 1:
        gap_divisor = 6
    elif round_num == 2:
        gap_divisor = 6
    else:  # round_num == 3 or round_num == 4
        gap_divisor = None

    num_players = len(field)

    for run in range(2 if round_num == 1 else 1):
        if run == 1 and round_num == 1:
            groups = list(reversed(groups))
            start_time = datetime(2023, 3, 29, 7)
        elif round_num in [3, 4]:
            if num_players % 2 == 1:
                solo_golfer = [sorted_field[0]]
                groups = [sorted_field[i:i + 2] for i in range(1, num_players, 2)]
                groups.insert(0, solo_golfer)
            else:
                groups = [sorted_field[i:i + 2] for i in range(0, num_players, 2)]
            start_time = datetime(2023, 3, 31, 8, 0)
        else:
            groups = [field[i:i + 3] for i in range(0, num_players, 3)]
            start_time = datetime(2023, 3, 29, 7)
            
        gap = num_players // gap_divisor if gap_divisor is not None else None
        
        tee_times_dict = player_tee_times if run == 0 else r2_tee_times
    
        for i, group in enumerate(groups):
            tee_time = start_time.strftime("%I:%M %p")
            if round_num in [3, 4]:
                current_hole = 1
                hole_order = list(range(1, 19))
            elif i % 2 == 0:
                current_hole = 10
                hole_order = [10, 11, 12, 13, 14, 15, 16, 17, 18, 1, 2, 3, 4, 5, 6, 7, 8, 9]
            else:
                current_hole = 1
                hole_order = list(range(1, 19))
    
            for j, golfer in enumerate(group):
                player_id = golfer['player_id']
                tee_times_dict[player_id] = {
                    'player_id': player_id,
                    'name': golfer['name'],
                    'tee_time': tee_time,
                    'current_hole': current_hole,
                    'hole_order': hole_order,
                    'group_num': i
                }
        
            if round_num in [3, 4]:
                start_time += timedelta(minutes=11)
            else:
                if gap and i == gap + 1:
                    start_time += ((gap / 2) + 3) * timedelta(minutes=11)
                if i % 2 == 1:
                    start_time += timedelta(minutes=11)

        if run == 0:
            r1_tee_times = tee_times_dict
        else:
            r2_tee_times = tee_times_dict

    return tee_times_dict, r1_tee_times, r2_tee_times


def print_tee_times(player_tee_times, round_num):
    sorted_tee_times = sort_tee_times(player_tee_times)
    
    if round_num not in (1,2):
        max_rows = len(sorted_tee_times)
    else:
        max_rows = len(sorted_tee_times) // 2

    first_tee_times = []
    tenth_tee_times = []

    for _, player_data in sorted_tee_times.items():
        if round_num in [3, 4] or player_data['current_hole'] == 1:
            first_tee_times.append(player_data)
        else:
            tenth_tee_times.append(player_data)

    print("Time       1st Hole                  10th Hole")
    print("-" * 50)

    prev_tee_time = None
    
    for i in range(max_rows):
        first_tee_time = first_tee_times[i]['tee_time'] if i < len(first_tee_times) else ""
        first_golfer_name = first_tee_times[i]['name'] if i < len(first_tee_times) else ""
    
        tenth_tee_time = tenth_tee_times[i]['tee_time'] if i < len(tenth_tee_times) else ""
        tenth_golfer_name = tenth_tee_times[i]['name'] if i < len(tenth_tee_times) else ""
    
        if prev_tee_time and prev_tee_time != first_tee_time:
            print()
        if i == 0 or prev_tee_time != first_tee_time:
            print(f"{first_tee_time:<12}{first_golfer_name:<25}{tenth_golfer_name:<30}")
        else:
            print(f"{'':<12}{first_golfer_name:<25}{tenth_golfer_name:<30}")
    
        prev_tee_time = first_tee_time.strip() or prev_tee_time


def initialize_tournament(tee_times, hole_pars):
    # Initialize a dictionary to keep track of each group's position on the course

    playerData = {}
    leaderboard = {}
    for pid, tee_time in tee_times.items():
        hole_order = tee_time['hole_order']
        start_hole = tee_time['current_hole']
        playerData[pid] = {
            "player_id": pid,
            "name": tee_time['name'],
            "start_time": datetime.strptime(tee_time['tee_time'], "%I:%M %p"),
            "start_hole": start_hole,
            "current_hole": start_hole if start_hole == 1 else 10,
            "r1scores": [],
            "r2scores": [],
            "r3scores": [],
            "r4scores": [],
            "total_holes": 0,
            "hole_order": hole_order,
            "started": False,
            "finished": False,
            "hole_pars": hole_pars,
            "make_cut": 0,
            "human": all_players_dict[pid]["human"],
            "total_strokes": 0
        }
        leaderboard[pid] = {
            'rank': 0,
            'start_rank': 0,
            'movement': 0,
            'player_id': pid,
            'player': "",
            'total': 0,
            'thru': 0,
            'round': 0,
            'r1': 0,
            'r2': 0,
            'r3': 0,
            'r4': 0,
            'strokes': 0,
            'make_cut': 0
        }
    return playerData, leaderboard


## loops endlessly likely due to finished = false for players that aren't in activePlayers
def simulate_round(tee_times, course_name, course_id, hole_pars, hole_handicaps, rd, playerData, tournament, purse, hasCut, cutline, made_cut, missed_cut, golfer_instances, course_difficulty, course_condition, leaderboard):
    

    # Set the current time to the time of the first tee time
    if rd in [1, 2]:
        current_time = datetime.strptime("07:00 AM", "%I:%M %p")
    else:
        current_time = datetime.strptime("08:00 AM", "%I:%M %p")
        
    total_par = sum(hole_pars)
    # Initialize a variable to keep track of the current step
    step = 0
    # Simulate the round until all groups have finished
        
    for player_id, tee_time_data in tee_times.items():
        tee_time =  datetime.strptime(tee_time_data['tee_time'], "%I:%M %p")
        current_hole = tee_time_data['current_hole']
        hole_order = tee_time_data['hole_order']
        start_hole = tee_time_data['current_hole']
        
        
        playerData[player_id].update({
            'start_time': tee_time,
            'current_hole': current_hole,
            'start_hole': current_hole,
            'hole_order': hole_order
        })   
        
        
    while not all_finished(playerData):
        if rd in [1, 2]:
            activePlayers = list(playerData.keys())
        else:
            activePlayers = [player['player_id'] for player in made_cut]
            for id in playerData:
                if id not in activePlayers:
                    playerData[id]["finished"] = 1

        # Check if any golfers have started playing
        for id in activePlayers:
            # Check if the current time equals the golfer's start time
            if current_time == playerData[id]["start_time"]:
                # Set started to True
                playerData[id]["started"] = True
                if rd > 1:
                    leaderboard[id]['start_rank'] = leaderboard[id]['rank']
                    leaderboard[id]['movement'] = 0
        for id in activePlayers:
            if playerData[id]["started"] and not playerData[id]["finished"]:
                if playerData[id]['human']:
                    hole_number = playerData[id]['current_hole']
                    human_input_scores(id, hole_number, playerData, rd)
                else:
                    # Generate scores for the current golfer
                    generate_scores(playerData, hole_pars, hole_handicaps, current_time, rd, activePlayers, golfer_instances, course_difficulty, course_condition, id)


        # Update the playerData of each id on the course
        update_positions(playerData, current_time, activePlayers)
        
        # Calculate leaderboard
        leaderboard, r3r4Field, sorted_players = calculate_leaderboard(playerData, rd, activePlayers, missed_cut, leaderboard)
        # print("Leaderboard: ",leaderboard)
        
        # Print leaderboard
        if rd in [1,2]:
            print_leaderboard(leaderboard, active_season, active_week, tournament, purse, course_name, total_par, rd, hasCut, cutline, activePlayers, playerData, sorted_players)
        else:
            print_top_half(made_cut, leaderboard, playerData, rd)
            print_missed_cut(missed_cut, leaderboard, playerData, rd)
        html_leaderboard = update_leaderboard_html(leaderboard, playerData, rd)

        # Increment the current time by 11 minutes
        current_time += timedelta(minutes=11)
        # Increment the step counter
        step += 1
      
    for id in playerData:
        playerData[id]["started"] = False
        playerData[id]["finished"] = False
        playerData[id]["total_holes"] = 0
    return playerData, activePlayers, leaderboard, html_leaderboard

def human_input_scores(player_id, hole_number, playerData, rd):
    # Get user input for the hole score
    hole_score = int(input(f"{playerData[player_id]['name']}: H{hole_number} score: "))

    # Update the player's round and total scores
    playerData[player_id][f"r{rd}scores"].append((int(hole_number), hole_score))
    playerData[player_id]["total_strokes"] += hole_score

    # Increment the total_holes counter for the player
    playerData[player_id]["total_holes"] += 1

    
    

def projected_cutline(leaderboard, cut_line=65):
    sorted_leaderboard = sorted(leaderboard, key=lambda x: x['total'])

    cut_index = cut_line - 1

    # Adjust cut_line if there are less than cut_line players in the field
    if len(sorted_leaderboard) < cut_line:
        cut_index = len(sorted_leaderboard) - 1

    cut_score = sorted_leaderboard[cut_index]['total']

    projected_cutline = {'rank': 'Cut', 'player': 'Projected Cut Line', 'total': cut_score}

    # Create a copy of the leaderboard with the projected cut line added
    leaderboard_with_cut = sorted_leaderboard[:cut_index + 1] + [projected_cutline] + sorted_leaderboard[cut_index + 1:]

    return leaderboard_with_cut


def all_finished(playerData):
    # Check if all groups have finished the course
    for group in playerData:
        # Loop over each golfer in the group
        if not playerData[group]["finished"]:
            return False
    return True


def update_positions(playerData, current_time, activePlayers):
    for id in activePlayers:
        if playerData[id]["started"] and not playerData[id]["finished"]:
            # Check if the golfer has finished a hole
            if playerData[id]["total_holes"] != 0 and playerData[id]["total_holes"] % 1 == 0:
                # Update the current hole using hole_order
                hole_index = playerData[id]["total_holes"] % 18
                playerData[id]["current_hole"] = playerData[id]["hole_order"][hole_index]

                # Check if the golfer has finished all 18 holes
                if playerData[id]["total_holes"] == 18:
                    playerData[id]["finished"] = True


                  
def generate_scores(playerData, hole_pars, hole_handicaps, current_time, rd, activePlayers, golfer_instances, course_difficulty, course_condition, player_id):
    # Check if the specified player has started and not yet finished
    if playerData[player_id]["started"] and not playerData[player_id]["finished"]:
        # Get the player instance
        golfer_instance = golfer_instances[player_id]

        # Get the current hole for the player
        current_hole = playerData[player_id]["current_hole"]

        # Get the hole par
        hole_par = hole_pars[current_hole - 1]

        # Calculate the score for the current hole
        hole_score = create_score(golfer_instance, hole_par, golfer_instance.par3, golfer_instance.par4, golfer_instance.par5, golfer_instance.bogeyAvoid, course_difficulty, course_condition)

        # Update the player's round and total scores
        playerData[player_id][f"r{rd}scores"].append((current_hole, hole_score))
        playerData[player_id]["total_strokes"] += hole_score

        # Increment the total_holes counter for the player
        playerData[player_id]["total_holes"] += 1


                    
                           
def get_final_scores(playerData):
    # Return the final scores for each group
    pass


def process_cut(playerData, cutline, rd, leaderboard):
    global cut_score

    # Calculate the cut score
    scores = sorted([player['total'] for player in leaderboard.values() if player['total'] != '-'])
    cut_index = min(cutline, len(scores))

    cut_score = scores[cut_index - 1]
    for i in range(cut_index, len(scores)):
        if scores[i] == cut_score:
            cut_index += 1
        else:
            break

    # Update the makecut value for each player
    for player_id, player in leaderboard.items():
        player_rank = int(player['rank'])  # Convert the player's rank to an integer
        if cut_index > player_rank:
            playerData[player_id]['make_cut'] = 1
            leaderboard[player_id]['make_cut'] = 1
        else:
            playerData[player_id]['make_cut'] = 0
            leaderboard[player_id]['make_cut'] = 0
            
    # Create the made_cut and missed_cut dictionaries
    made_cut, missed_cut = get_cut_lists(playerData, leaderboard)
    
    return made_cut, missed_cut, leaderboard


def get_cut_lists(playerData, leaderboard):
    made_cut = [{'player_id': player_id, 'name': player_data['name'], 'total': player_data['total_score']} for player_id, player_data in playerData.items() if player_id in leaderboard and player_data.get('make_cut') == 1]
    missed_cut = [{'player_id': player_id, 'name': player_data['name'], 'total': player_data['total_score']} for player_id, player_data in playerData.items() if player_id in leaderboard and player_data.get('make_cut') == 0]
    return made_cut, missed_cut



def add_scores(tid, name, round_num, scores):
    c.execute('INSERT INTO Scores (tid, name, round, scores) VALUES (?, ?, ?, ?)',
              (tid, name, round_num, ','.join(str(score) for score in scores)))
    conn.commit()


def clear_scores(tid):
    c.execute("DELETE FROM Scores WHERE tid=?", (tid,))
    conn.commit()
    conn.close()


def get_course_info():
    # """Gets the course information for the active event."""
    c.execute("SELECT Course FROM Schedule WHERE Season=? AND Week=?", (active_season, active_week))
    courses_name = c.fetchone()[0]
    print(courses_name)

    c.execute("SELECT courses_id, course_name, pars, handicaps FROM Courses WHERE course_name=?", (courses_name,))
    course_info = c.fetchone()

    course_id = course_info[0]
    course_name = course_info[1]
    hole_pars = list(map(int, course_info[2].split(",")))
    hole_handicaps = list(map(int, course_info[3].split(",")))

    total_par = sum(hole_pars)

    return course_id, course_name, hole_pars, hole_handicaps, total_par


def get_schedule_info(active_season, active_event_id):
    # """Gets the schedule information for the active event."""
    c.execute("SELECT schedule_id, season, week, tournament, purse, fieldsize, hasCut, cutline FROM Schedule WHERE Season=? AND Week=?", (active_season, active_week))
    schedule_info = c.fetchone()
    #print("schedule_info: ", schedule_info)

    tid = schedule_info[0]
    season = schedule_info[1]
    week = schedule_info[2]
    tournament = schedule_info[3]
    purse = schedule_info[4]
    fieldSize = schedule_info[5]
    hasCut = schedule_info[6]
    cutline = schedule_info[7]
    return tid, season, week, tournament, purse, fieldSize, hasCut, cutline


# def get_scores(active_event_id):
#     """Gets the scores for all players for the current round and active event."""
#     c.execute("""SELECT Scores.name, Scores.scores
#                   FROM Scores JOIN Schedule ON Scores.tid=Schedule.schedule_id
#                   WHERE Schedule.season=? AND Schedule.week=? AND Schedule.schedule_id=?""",
#               (active_season, active_week, active_event_id))
#     rows = c.fetchall()
#
#     scores_dict = {}
#     for row in rows:
#         name = row[0]
#         scores = [int(s) for s in row[1].split(",")]
#
#         if name not in scores_dict:
#             scores_dict[name] = []
#
#         scores_dict[name].append(scores)
#     return scores_dict


def calculate_leaderboard(playerData, rd, activePlayers, missed_cut, leaderboard):
    rank = 1 
    #leaderboard = []
    #movement = 0
    
    if rd > 2:
        r3r4Field = [{'player_id': player_id, 'name': player_data['name'], 'total': player_data['total_score']} for player_id, player_data in playerData.items() if player_data['make_cut'] == 1]

    else:
        r3r4Field = []
        
    for player_id, player_data in playerData.items():
        total_strokes = 0
        round_strokes = 0
        round_scores = [0, 0, 0, 0]
        total_par = 0
        total_par_sum = 0
        round_par = 0
        round_score = 0
                
        total_strokes = sum(score for hole, score in player_data['r1scores'] + player_data['r2scores'] + player_data['r3scores'] + player_data['r4scores'] if hole <= len(player_data['hole_pars']))
        total_par_sum = sum(player_data['hole_pars'][hole - 1] for hole, _ in player_data['r1scores'] + player_data['r2scores'] + player_data['r3scores'] + player_data['r4scores'])
                        
        for round_num in range(1, min(rd + 1, 5)):
            round_name = f'r{round_num}scores'
            round_strokes = sum(score for hole, score in player_data[round_name])
            round_par = sum(player_data['hole_pars'][hole - 1] for hole, score in player_data[round_name])
        
            if round_num < 2 or (round_num == 2 and len(player_data[round_name]) < 18):
                round_score = round_strokes - round_par
            elif 'make_cut' in player_data and player_data['make_cut'] == 0 and round_num >= 3:
                round_score = 0
            else:
                round_score = round_strokes - round_par

            if len(player_data[round_name]) == 18:
                round_scores[round_num - 1] = round_strokes
            total_score = total_strokes - total_par_sum
            
            data_to_update = {'round_scores': round_scores, 'round_strokes': round_strokes, 'round_score': round_score}
            playerData[player_id].update(data_to_update)
        total_score = total_strokes - total_par_sum
        data_to_update = {'total_score': total_score, 'total_strokes': total_strokes}
        playerData[player_id].update(data_to_update)

    for player_id, player_data in sorted(playerData.items(), key=lambda x: (x[1]['make_cut'], x[1]['total_score']), reverse=False):
        # Determine the last completed hole and current round score
        hole_order = playerData[player_id]['hole_order']
        current_hole = playerData[player_id]['current_hole']
        last_hole_index = hole_order.index(current_hole)
        makecut = 0
        if rd > 1:
            movement = leaderboard[player_id]['start_rank'] - leaderboard[player_id]['rank']
        else:
            movement = 0
    
        if playerData[player_id]['finished']:
            last_hole = "F"
        elif not playerData[player_id]['started']:
            start_time_str = playerData[player_id]['start_time']
            dt_str = start_time_str.strftime('%I:%M%p')
            last_hole = dt_str
    
        elif playerData[player_id]['start_hole'] == 10:
            # Add a '*' to the end of last_hole if start_hole is equal to 10
            lh = hole_order[last_hole_index - 1]
            last_hole = f"{lh}*"
        else:
            last_hole = last_hole_index
                
        if player_data['make_cut'] == 1:
            makecut = 1
        
        # Calculate the total score, and add it to the leaderboard
        total_score = player_data['total_score']
        leaderboard[player_id].update({
            'rank': rank,
            'movement': movement,
            'player_id': player_id,
            'player': player_data['name'],
            'total': total_score,
            'thru': last_hole,
            'round': player_data['round_score'],
            'r1': player_data['round_scores'][0] if player_data['round_scores'][0] > 1 else '-',
            'r2': player_data['round_scores'][1] if player_data['round_scores'][1] > 1 else '-',
            'r3': player_data['round_scores'][2] if player_data['round_scores'][2] > 1 else '-',
            'r4': player_data['round_scores'][3] if player_data['round_scores'][3] > 1 else '-',
            'strokes': player_data['total_strokes'],
            'make_cut': player_data['make_cut']
        })
        
    # Create a list of players sorted by total score in ascending order
    sorted_players = sorted(leaderboard.items(), key=lambda x: x[1]['total'])



    # Assign rank to each player based on their position in the sorted list
    rank = 1
    ties = 0
    prev_score = None
    
    # First iteration: Rank players who made the cut
    for player_id, player_data in sorted_players:
        if rd in [3, 4] and not player_data['make_cut']:
            continue  # Skip players who didn't make the cut in round 3 and round 4

        if player_data['total'] != prev_score:
            rank += ties
            ties = 1
        else:
            ties += 1

        leaderboard[player_id]['rank'] = rank
        prev_score = player_data['total']

    # Second iteration: Rank players who missed the cut
    if rd in [3, 4]:
        ties = 1
        for player_id, player_data in sorted_players:
            if player_data['make_cut']:
                continue  # Skip players who made the cut

            if player_data['total'] != prev_score:
                rank += ties
                ties = 1
            else:
                ties += 1

            leaderboard[player_id]['rank'] = rank
            prev_score = player_data['total']


    return leaderboard, r3r4Field, sorted_players


def update_ranks(leaderboard):
    ranked_players = []
    for i, player_id in enumerate(leaderboard):
        rank = i + 1
        if i > 0 and leaderboard[player_id]['total'] == leaderboard[list(leaderboard)[i - 1]]['total']:
            rank = leaderboard[list(leaderboard)[i - 1]]['rank']
        leaderboard[player_id]['rank'] = rank
        ranked_players.append(leaderboard[player_id])
    return ranked_players

def print_header(header):
    # Format the header and print it
    print('{:<5}{:<5}{:<27}{:<6}{:<10}{:<6}{:<4}{:<4}{:<4}{:<4}{:<7}'.format(*header))
    # Print a line of dashes to separate the header from the rest of the leaderboard
    print('-' * 82)
    
def print_separator(length):
    """
    Takes a length and prints a line of dashes of that length.

    Parameters:
    length (int): The length of the line of dashes to print.

    Returns:
    None
    """
    print('-' * length)

def print_player(player_id, leaderboard, playerData, rd):
    player = leaderboard[player_id]
    rank = player['rank']
    movement = player['movement']
    total = player['total']
    thru = player['thru']
    r1 = player['r1']
    r2 = player['r2']
    r3 = player['r3']
    r4 = player['r4']
    strokes = player['strokes']
    makecut = playerData[player_id]['make_cut']

    # If the total is 0, change it to "E" for even
    if total == 0:
        total = 'E'
    # If the total is positive, add a plus sign to it and convert to a string
    elif total > 0:
        total = f'+{total}'

    if playerData[player_id]['started'] or playerData[player_id]['finished']:
        round_score = player['round']
        if round_score == 0:
            round_scr = 'E'
        elif round_score > 0:
            round_scr = f'+{round_score}'
        else:
            round_scr = round_score
        
    if not playerData[player_id]['started']:
        round_scr = "-"
    
    # Check if there are tied ranks and add "T" to the rank if there are
    rank_counts = {}
    for p_id, p_data in leaderboard.items():
        if p_data['rank'] in rank_counts:
            rank_counts[p_data['rank']] += 1
        else:
            rank_counts[p_data['rank']] = 1
    
    # Check if the player's makecut value is 0 and it's the 3rd or 4th round
    if makecut == 0 and rd in (3, 4):
        rank = "CUT"
    elif rank_counts[rank] > 1:
        rank = f"T{rank}"

    # Check an# Format the movement value with arrows or a dash
    if rd == 1 or rd in (3, 4) and playerData[player_id]['make_cut'] == 0:
        movement_str = ""
    else:
        if player['movement'] > 0:
            movement_str = f"↑{player['movement']}"
        elif player['movement'] < 0:
            movement_str = f"↓{-player['movement']}"
        else:
            movement_str = '-'
    
    
    print(f"{rank:<5}{movement_str:<5}{player['player']:<27}{total:<6}{thru:<10}{round_scr:<6}{r1:<4}{r2:<4}{r3:<4}{r4:<4}{strokes:<7}")
    
    
def update_leaderboard_html(leaderboard, playerData, rd):
    html_leaderboard = {}
    
    for player_id in leaderboard.keys():
        player = leaderboard[player_id].copy()
        
        # Add the updated player to the html_leaderboard
        html_leaderboard[player_id] = player
        
        # Perform the updates as in the print_player function
        total = player['total']
        if total == 0:
            total = 'E'
        elif total > 0:
            total = f'+{total}'
        
        player['total'] = total

        if playerData[player_id]['started'] or playerData[player_id]['finished']:
            round_score = player['round']
            if round_score == 0:
                round_scr = 'E'
            elif round_score > 0:
                round_scr = f'+{round_score}'
            else:
                round_scr = round_score
        else:
            round_scr = "-"
        
        player['round'] = round_scr

        makecut = playerData[player_id]['make_cut']
        rank = player['rank']

        rank_counts = {}
        for p_id, p_data in leaderboard.items():
            if p_data['rank'] in rank_counts:
                rank_counts[p_data['rank']] += 1
            else:
                rank_counts[p_data['rank']] = 1

        if makecut == 0 and rd in (3, 4):
            rank = "CUT"
        elif rank_counts[rank] > 1:
            rank = f"T{rank}"
        
        player['rank'] = rank

    return html_leaderboard


def print_projected_cutline(cut_index):
    print('-' * 72)
    print(f"Projected Cut Line: {cut_index}")
    print('-' * 72)


def print_top_half(made_cut, leaderboard, playerData, rd):
    # Create a dictionary to hold the data for the players who made the cut
    top_half = {}
    
    # Set the column header for the leaderboard
    header = ['Rank', '↑↓', 'Player', 'Total', 'Thru', 'Round', 'R1', 'R2', 'R3', 'R4', 'Strokes']

    # Print the header and separator
    print_header(header)
    
    for player_id, player_data in leaderboard.items():
        # If a player made the cut, add their data to the top_half dictionary
        if any(player['player_id'] == player_id for player in made_cut):
            top_half[player_id] = player_data

    # Sort the top_half dictionary based on player's total score
    sorted_top_half = sorted(top_half.values(), key=lambda x: x['total'])
    
    # Print the leaderboard for players who made the cut
    for player in sorted_top_half:
        current_player_id = player['player_id']
        print_player(current_player_id, leaderboard, playerData, rd)


def print_missed_cut(missed_cut, leaderboard, playerData, rd):
    sorted_mc = sorted(missed_cut, key=lambda x: x['total']) 
    print_separator(82)
    print("The following players missed the cut:")
    print_separator(82)
    
    # Print the leaderboard for players who missed the cut
    for player_data in sorted_mc:
        pid = player_data['player_id']
        print_player(pid, leaderboard, playerData, rd)
        

def calculate_cut(leaderboard, has_cut, cutline):
    if not has_cut:
        return None, list(leaderboard.keys())
    
    # Get the scores of players who are not disqualified and sort them
    scores = sorted([player['total'] for player in leaderboard.values() if player['total'] != '-'])

    # Determine the index of the cut line
    cut_index = min(cutline, len(scores))

    # Check if there are ties at the cut line and adjust the cut line if necessary
    while cut_index < len(scores) and scores[cut_index] == scores[cut_index - 1]:
        cut_index += 1

    # Set the cut score
    cut_score = scores[cut_index - 1] if cut_index > 0 else None

    # Get the IDs of the players who made the cut
    made_cut = [player_id for player_id, player in leaderboard.items() if player['total'] != '-' and player['total'] <= cut_score]

    return cut_score, made_cut


def print_leaderboard(leaderboard, active_season, active_week, tournament, purse, course_name, total_par, rd, hasCut, cutline, activePlayers, playerData, sorted_players):
    # Print the season and week of the tournament
    print(f"\nSeason: {active_season}\nWeek: {active_week}\n")
    # Print the tournament name, course name, and total par
    print(f"Tournament: {tournament}\nCourse: {course_name}\nPar: {total_par}\n\nPurse: {purse}\n")

    # Set the column header for the leaderboard
    header = ['Rank', '↑↓', 'Player', 'Total', 'Thru', 'Round', 'R1', 'R2', 'R3', 'R4', 'Strokes']

    # Print the header and separator
    print_header(header)

    # Calculate the cut score and get the players who made the cut
    cut_score, made_cut = calculate_cut(leaderboard, hasCut, cutline)

    # Print the leaderboard for all players
    counter = 0
    for player_id, player_data in sorted_players:
        counter += 1
        # If there is a cut and it is the second round, print the projected cut line
        if hasCut and rd == 2:
            # Count the number of players tied at the cutline
            num_ties = len([p for p in leaderboard.values() if p['total'] == cut_score])
    
            # Print player data and cutline if applicable
            if counter < cutline or (counter <= cutline + num_ties and num_ties > 0):
                print_player(player_id, leaderboard, playerData, rd)
                if counter == cutline:
                    print_projected_cutline(cut_score)
            elif counter > cutline and counter <= cutline + num_ties:
                print_player(player_id, leaderboard, playerData, rd)
            else:
                print_player(player_id, leaderboard, playerData, rd)
        else:
            print_player(player_id, leaderboard, playerData, rd)



        
def get_stats(scores_dict, hole_pars):
    stats = {
        'par3': {'ace': 0, 'alb': 0, 'eagle': 0, 'bird': 0, 'par': 0, 'bogie': 0, 'dbogie': 0, 'tbogie': 0, 'other': 0},
        'par4': {'ace': 0, 'alb': 0, 'eagle': 0, 'bird': 0, 'par': 0, 'bogie': 0, 'dbogie': 0, 'tbogie': 0, 'other': 0},
        'par5': {'ace': 0, 'alb': 0, 'eagle': 0, 'bird': 0, 'par': 0, 'bogie': 0, 'dbogie': 0, 'tbogie': 0, 'other': 0}
    }
    for player in scores_dict:
        for rd in range(1, 5):  # Loop through rounds 1 to 4
            round_key = f"r{rd}scores"
            round_scores = scores_dict[player][round_key]
            for hole_data in round_scores:
                hole_number, score = hole_data
                hole_index = hole_number - 1
                par = hole_pars[hole_index]
                if par == 3:
                    if score == 1:
                        stats['par3']['ace'] += 1
                    elif score == 99:
                        stats['par3']['alb'] += 0
                    elif score == 99:
                        stats['par3']['eagle'] += 0                    
                    elif score == par - 1:
                        stats['par3']['bird'] += 1
                    elif score == par:
                        stats['par3']['par'] += 1
                    elif score == par + 1:
                        stats['par3']['bogie'] += 1
                    elif score == par + 2:
                        stats['par3']['dbogie'] += 1
                    elif score == par + 3:
                        stats['par3']['tbogie'] += 1
                    else:
                        stats['par3']['other'] += 1
                elif par == 4:
                    if score == par - 3:
                        stats['par4']['ace'] += 1
                    elif score == 99:
                        stats['par4']['alb'] += 0
                    elif score == par - 2:
                        stats['par4']['eagle'] += 1
                    elif score == par - 1:
                        stats['par4']['bird'] += 1
                    elif score == par:
                        stats['par4']['par'] += 1
                    elif score == par + 1:
                        stats['par4']['bogie'] += 1
                    elif score == par + 2:
                        stats['par4']['dbogie'] += 1
                    elif score == par + 3:
                        stats['par4']['tbogie'] += 1
                    else:
                        stats['par4']['other'] += 1
                else:  # Par5
                    if score == 99:
                        stats['par4']['ace'] += 0
                    elif score == par - 3:
                        stats['par5']['alb'] += 1
                    elif score == par - 2:
                        stats['par5']['eagle'] += 1
                    elif score == par - 1:
                        stats['par5']['bird'] += 1
                    elif score == par:
                        stats['par5']['par'] += 1
                    elif score == par + 1:
                        stats['par5']['bogie'] += 1
                    elif score == par + 2:
                        stats['par5']['dbogie'] += 1
                    elif score == par + 3:
                        stats['par5']['tbogie'] += 1
                    else:
                        stats['par5']['other'] += 1

    # print("Stats: ", stats)
    return stats


def print_stats(stats, headers):
    # Print table headers
    print("{:<15}".format(""), end="")
    for header in headers:
        print("{:<10}".format(header), end="")
    print()

    # Print table rows
    for par in stats.keys():
        print("{:<15}".format(par), end="")
        for header in headers:
            value = stats[par].get(header.lower(), "")
            print("{:<10}".format(value), end="")
        print()
        
        

def sort_tee_times(tee_times, reverse=False):
    sorted_tee_times = sorted(tee_times.items(), key=lambda x: datetime.strptime(x[1]['tee_time'], "%I:%M %p"), reverse=reverse)
    return dict(sorted_tee_times)



def reverse_field(tee_times):
    # Sort the tee_times by group_num (ascending order) for round 1
    sorted_rd1 = sorted(tee_times.items(), key=lambda x: x[1]['group_num'])

    # Reverse sort the tee_times by group_num
    reverse_sorted_groups = sorted(sorted_rd1, key=lambda x: x[1]['group_num'], reverse=True)

    # Reassign tee times based on the reversed group_num order
    for index, (pid, player_data) in enumerate(reverse_sorted_groups):
        player_data['tee_time'] = sorted_rd1[index][1]['tee_time']

    return dict(reverse_sorted_groups)

def playoff(leaderboard, hole_pars, golfer_instances, course, condition):
    # Check if there is a tie for first place
    first_place_score = next(player["total"] for player in leaderboard.values() if player["rank"] == 1)
    tied_players = [player for player in leaderboard.values() if player["total"] == first_place_score]


    if len(tied_players) > 1:
        print("\nPlayoff needed!\n")

        hole_number = 1
        while len(tied_players) > 1:
            for player in tied_players:
                golfer = golfer_instances[player["player_id"]]
                par = hole_pars[hole_number - 1]
                par3 = golfer.par3
                par4 = golfer.par4
                par5 = golfer.par5
                bogeyAvoid = golfer.bogeyAvoid
                player["playoff_score"] = create_score(golfer, par, par3, par4, par5, bogeyAvoid, course, condition)

            # Print the scores of all players in the playoff
            
            print(f"Playoff hole {hole_number} results:")
            for player in tied_players:
                print(f"{player['player']} - Score: {player['playoff_score']}")
            print()
            # Eliminate players who don't match the lowest score
            lowest_playoff_score = min(player["playoff_score"] for player in tied_players)
            tied_players = [player for player in tied_players if player["playoff_score"] == lowest_playoff_score]

            hole_number += 1

        if len(tied_players) == 1:
            winner = tied_players[0]
            winner['rank'] = f"{winner['rank']}*"
            print(f"Playoff winner: {winner['player']}")

    return leaderboard

def reset_movement(field, rd):
    for player_id, player_data in field.items():
        player_data['movement'] = 0
        player_data['start_rank'] = player_data['rank']
    return field

def main():
    made_cut = {}
    missed_cut = {}
    playerData = {}
    rd = 1

    # Clear all scores
    # clear_scores(tid)

    # Get active event id based on active_season and active_week
    c.execute("SELECT schedule_id FROM Schedule WHERE Season=? AND Week=?", (active_season, active_week))
    active_event_id = c.fetchone()[0]
    # print(active_event_id)

    # Get schedule information
    tid, season, week, tournament, purse, fieldSize, hasCut, cutline = get_schedule_info(active_season, active_event_id)


    # Get player field
    field,human = get_field(fieldSize)
    #print("Field: ", field)

    # print("selected players: ",field)

    # Assign r1 tee times
    tee_times_dict, r1_tee_times, r2_tee_times = set_tee_times(field, 1, playerData)
    print_tee_times(r1_tee_times, rd)
    input("Press any key to continue...")

    # Get course information
    course_id, course_name, hole_pars, hole_handicaps, total_par = get_course_info()

    # initialize tournament    
    playerData, leaderboard = initialize_tournament(r1_tee_times, hole_pars)
    
    #course_difficulty & condition
    course_difficulty = "normal"
    course_condition = "normal"

    
    # simulate r1
    playerData, activePlayers, leaderboard, html_leaderboard = simulate_round(r1_tee_times, course_name, course_id, hole_pars, hole_handicaps, 1, playerData, tournament, purse, hasCut, cutline, made_cut, missed_cut, golfer_instances, course_difficulty, course_condition, leaderboard)
    rd += 1
    # print r2 tee times
    print_tee_times(r2_tee_times, rd)
    reset_movement(leaderboard, rd)
    input("Press any key to continue...")
    #print_leaderboard(leaderboard, active_season, active_week, tournament, purse, course_name, total_par, 2, hasCut, cutline, activePlayers, playerData, sorted_players)

    #course_difficulty & condition
    course_difficulty = "normal"
    course_condition = "hard"


    
    # simulate r2
    playerData, activePlayers, leaderboard, html_leaderboard = simulate_round(r2_tee_times, course_name, tid, hole_pars, hole_handicaps, 2, playerData, tournament, purse, hasCut, cutline, made_cut, missed_cut, golfer_instances, course_difficulty, course_condition, leaderboard)
    rd += 1
    # process cut
    if hasCut:
         made_cut, missed_cut, leaderboard = process_cut(playerData, cutline, 3, leaderboard)      


    #course_difficulty & condition
    course_difficulty = "normal"
    course_condition = "easy"

    
    # set tee times for r3
    r3_tee_times, r1_tee_times, r2_tee_times = set_tee_times(made_cut, 3, playerData)
    print_tee_times(r3_tee_times, rd)
    reset_movement(leaderboard, rd)
    input("Press any key to continue...")
    print_top_half(made_cut, leaderboard, playerData, 3)
    print_missed_cut(missed_cut, leaderboard, playerData, 3)

    # simulate r3
    playerData, activePlayers, leaderboard, html_leaderboard = simulate_round(r3_tee_times, course_name, tid, hole_pars, hole_handicaps, 3, playerData, tournament, purse, hasCut, cutline, made_cut, missed_cut, golfer_instances, course_difficulty, course_condition, leaderboard)
    rd += 1

    # set tee times for r4
    made_cut, missed_cut = get_cut_lists(playerData, leaderboard)
    r4_tee_times, r1_tee_times, r2_tee_times = set_tee_times(made_cut, 4, playerData)
    print_tee_times(r4_tee_times, rd)
    reset_movement(leaderboard, rd)
    input("Press any key to continue...")
    print_top_half(made_cut, leaderboard, playerData, 4)
    print_missed_cut(missed_cut, leaderboard, playerData, 4)

    #course_difficulty & condition
    course_difficulty = "hard"
    course_condition = "hard"

    # simulate r4
    playerData, activePlayers, leaderboard, html_leaderboard = simulate_round(r4_tee_times, course_name, tid, hole_pars, hole_handicaps, 4, playerData, tournament, purse, hasCut, cutline, made_cut, missed_cut, golfer_instances, course_difficulty, course_condition, leaderboard)
    print()

    # Run the playoff if necessary
    # Sort the made_cut list by total score in ascending order
    rank_1_players = [player for player in leaderboard.values() if player["rank"] == 1]

    if len(rank_1_players) > 1:
        # Call the playoff function with the sorted leaderboard
        leaderboard = playoff(leaderboard, hole_pars, golfer_instances, course_difficulty, course_condition)

    # Print the final leaderboard
    print("\nFinal Leaderboard:")
    #print(leaderboard)
#    for player_id, player in leaderboard.items():
        #print(f"{player['rank']} - {player['player']} - {player['total']}")

    #get stats
    stats = get_stats(playerData, hole_pars)
    
    #print stats
    headers = ['Ace', 'Alb', 'Eagle', 'Bird', 'Par', 'Bogie', 'DBogie', 'TBogie', 'Other']
    print_stats(stats, headers)

#    conn.close()

main()
