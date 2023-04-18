import sqlite3
import random
from datetime import datetime, timedelta
from scoregenerator import Golfer, Hole, create_score, get_golfers_from_db


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

for row in PGA_stats:
    name = row[0]
    rating = row[1]
    par3avg = row[2]
    par4avg = row[3]
    par5avg = row[4]
    print(f"{name}, {rating}, {par3avg}, {par4avg}, {par5avg}")

active_season = 2023
active_week = 1

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
    c.execute('SELECT players_id, name FROM Players')
    all_players = c.fetchall()
    selected_players = []
    ids = []
    
    while len(selected_players) < field_size and all_players:
        player = random.choice(all_players)
        if player[0] not in ids and random.randint(1, 100) in range(20, 81):
            selected_players.append({'player_id': player[0], 'name': player[1]})
            ids.append(player[0])
        all_players.remove(player)
    
        if not all_players:
            c.execute(f"SELECT players_id, name FROM Players WHERE players_id NOT IN ({', '.join('?' for _ in ids)})", ids)
            all_players = c.fetchall()

    return selected_players


def set_tee_times(field, round_num, playerData):
    player_tee_times = {}
    r2_tee_times = {}
    
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
            
    # max_rows = max(len([group for group in player_tee_times.values() if group['current_hole'] == 1]),
    #               len([group for group in player_tee_times.values() if group['current_hole'] == 10]))
    # total_rows = (len([group for group in player_tee_times.values() if group['current_hole'] == 1]) +
    #               len([group for group in player_tee_times.values() if group['current_hole'] == 10]))
    #
    # if round_num in [3, 4]:
    #     print(f"{'Round ' + str(round_num)}")
    #     print(f"{'Tee Times':<12}{'1st Hole':<25}")
    # else:
    #     print(f"{'Round ' + str(round_num)}")
    #     print(f"{'Tee Times':<12}{'1st Hole':<25}{'10th Hole':<30}")

    
    #prev_tee_time = ""

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
    for pid, tee_time in tee_times.items():
        hole_order = tee_time['hole_order']
        start_hole = tee_time['current_hole']
        playerData[pid] = {
            "player_id": pid,
            "name": tee_time['name'],
            "start_time": datetime.strptime(tee_time['tee_time'], "%I:%M %p"),
            "start_hole": start_hole,
            "current_hole": start_hole if start_hole == 1 else 10,
            "R1scores": [],
            "R2scores": [],
            "R3scores": [],
            "R4scores": [],
            "total_holes": 0,
            "hole_order": hole_order,
            "started": False,
            "finished": False,
            "hole_pars": hole_pars,
            "makeCut": 0
        }
    return playerData


## loops endlessly likely due to finished = false for players that aren't in activePlayers
def simulate_round(tee_times, course_name, course_id, hole_pars, hole_handicaps, rd, playerData, tournament, purse, hasCut, cutline, made_cut, missed_cut, golfer_instances, course_difficulty, course_condition):
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
        
        # Generate scores for any ids that have finished a hole
        generate_scores(playerData, hole_pars, hole_handicaps, current_time, rd, activePlayers, golfer_instances, course_difficulty, course_condition)
        print ("GenScoresCounter: ", gen_scores_calls)
        
        # Update the playerData of each id on the course
        update_positions(playerData, current_time, activePlayers)

        # Calculate leaderboard
        leaderboard, r3r4Field = calculate_leaderboard(playerData, rd, activePlayers, missed_cut)
        # print("Leaderboard: ",leaderboard)
        
        # Print leaderboard
        if rd in [1,2]:
            print_leaderboard(leaderboard, active_season, active_week, tournament, purse, course_name, total_par, rd, hasCut, cutline, activePlayers, playerData)
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


def projected_cutline(leaderboard, cut_line=65):
    sorted_leaderboard = sorted(leaderboard, key=lambda x: x['Total'])

    cut_index = cut_line - 1

    # Adjust cut_line if there are less than cut_line players in the field
    if len(sorted_leaderboard) < cut_line:
        cut_index = len(sorted_leaderboard) - 1

    cut_score = sorted_leaderboard[cut_index]['Total']

    projected_cutline = {'Rank': 'Cut', 'Player': 'Projected Cut Line', 'Total': cut_score}

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
    
    global update_pos_calls
    update_pos_calls += 1
    
    # Update the playerData of each id on the course based on the current step and current time
    for id in activePlayers:
        # Check if the golfer has started playing
        if playerData[id]["start_time"] <= current_time and playerData[id]["started"] and not playerData[id]["finished"]:
            # Get the current hole for the golfer
            current_hole = playerData[id]["current_hole"]
            # Get the index of the current hole in the hole_order list
            hole_index = playerData[id]["hole_order"].index(current_hole)
            # Determine the next hole for the golfer
            next_hole_index = (hole_index + 1) % 18
            next_hole = playerData[id]["hole_order"][next_hole_index]
            playerData[id]["current_hole"] = next_hole
            # Increment the total number of holes completed by 1 if the hole has changed
            if next_hole != current_hole:
                playerData[id]["total_holes"] += 1
                # Check if the golfer has completed all 18 holes
                if playerData[id]["total_holes"] == 18:
                    # Set finished to True to indicate that the golfer has finished playing
                    playerData[id]["finished"] = True

                  
def generate_scores(playerData, hole_pars, hole_handicaps, current_time, rd, activePlayers, golfer_instances, course_difficulty, course_condition):
    
    global gen_scores_calls
    gen_scores_calls += 1
    
    for id in playerData:
        if id in activePlayers:
            golfer = golfer_instances[id]
            hole = playerData[id]["current_hole"]
            if playerData[id]["start_time"] <= current_time and playerData[id]["started"] and not playerData[id]["finished"]:
                # Convert the hole to an index for the hole_pars and hole_handicaps lists
                hole_index = int(hole) - 1
                # Get the par and handicap for the current hole
                par = hole_pars[hole_index]
                handicap = hole_handicaps[hole_index]
                par3 = golfer.par3
                par4 = golfer.par4
                par5 = golfer.par5
                bogeyAvoid = golfer.bogeyAvoid
                # Calculate the range of scores based on the par for the current hole
                # min_score = max(par - 2, 1)
                # max_score = min(par + 2, 10)
                # Generate a random score within the range
                generated_score = create_score(golfer, par, par3, par4, par5, bogeyAvoid, course_difficulty, course_condition)
                score = generated_score
                # Store the score in the appropriate scores list for the golfer based on the round
                if rd == 1:
                    playerData[id]["R1scores"].append((int(hole), score))
                elif rd == 2:
                    playerData[id]["R2scores"].append((int(hole), score))
                elif rd == 3:
                    playerData[id]["R3scores"].append((int(hole), score))
                elif rd == 4:
                    playerData[id]["R4scores"].append((int(hole), score))

                    
                           
def get_final_scores(playerData):
    # Return the final scores for each group
    pass


def process_cut(playerData, cutline, rd, leaderboard):
    global cut_score

    # Calculate the cut score
    scores = sorted([player['Total'] for player in leaderboard.values() if player['Total'] != '-'])
    cut_index = min(cutline, len(scores))

    cut_score = scores[cut_index - 1]
    for i in range(cut_index, len(scores)):
        if scores[i] == cut_score:
            cut_index += 1
        else:
            break

    # Update the MakeCut value for each player
    for player_id, player in leaderboard.items():
        player_rank = int(player['Rank'])  # Convert the player's rank to an integer
        if cut_index > player_rank:
            playerData[player_id]['makeCut'] = 1
            leaderboard[player_id]['MakeCut'] = 1
        else:
            playerData[player_id]['makeCut'] = 0
            leaderboard[player_id]['MakeCut'] = 0
            
    # Create the made_cut and missed_cut dictionaries
    made_cut, missed_cut = get_cut_lists(playerData, leaderboard)
    
    return made_cut, missed_cut, leaderboard


def get_cut_lists(playerData, leaderboard):
    made_cut = [{'player_id': player_id, 'name': player_data['name'], 'total': player_data['total_score']} for player_id, player_data in playerData.items() if player_id in leaderboard and player_data.get('makeCut') == 1]
    missed_cut = [{'player_id': player_id, 'name': player_data['name'], 'total': player_data['total_score']} for player_id, player_data in playerData.items() if player_id in leaderboard and player_data.get('makeCut') == 0]
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
    print("schedule_info: ", schedule_info)

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


def calculate_leaderboard(playerData, rd, activePlayers, missed_cut):
    rank = 1 
    leaderboard = []
    
    if rd > 2:
        r3r4Field = [{'player_id': player_id, 'name': player_data['name'], 'total': player_data['total_score']} for player_id, player_data in playerData.items() if player_data['makeCut'] == 1]

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
                
        total_strokes = sum(score for hole, score in player_data['R1scores'] + player_data['R2scores'] + player_data['R3scores'] + player_data['R4scores'] if hole <= len(player_data['hole_pars']))
        total_par_sum = sum(player_data['hole_pars'][hole - 1] for hole, _ in player_data['R1scores'] + player_data['R2scores'] + player_data['R3scores'] + player_data['R4scores'])
                        
        for round_num in range(1, min(rd + 1, 5)):
            round_name = f'R{round_num}scores'
            round_strokes = sum(score for hole, score in player_data[round_name])
            round_par = sum(player_data['hole_pars'][hole - 1] for hole, score in player_data[round_name])
        
            if round_num < 2 or (round_num == 2 and len(player_data[round_name]) < 18):
                round_score = round_strokes - round_par
            elif 'makeCut' in player_data and player_data['makeCut'] == 0 and round_num >= 3:
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

    leaderboard = {}
    for player_id, player_data in sorted(playerData.items(), key=lambda x: (x[1]['makeCut'], x[1]['total_score']), reverse=False):
        # Determine the last completed hole and current round score
        hole_order = playerData[player_id]['hole_order']
        current_hole = playerData[player_id]['current_hole']
        last_hole_index = hole_order.index(current_hole)
        makeCut = 0
    
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
                
        if player_data['makeCut'] == 1:
            makeCut = 1
        
        # Calculate the total score, and add it to the leaderboard
        total_score = player_data['total_score']
        leaderboard[player_id] = {
            'Rank': rank,
            'Player_id': player_id,
            'Player': player_data['name'],
            'Total': total_score,
            'Thru': last_hole,
            'Round': player_data['round_score'],
            'R1': player_data['round_scores'][0] if player_data['round_scores'][0] > 1 else '-',
            'R2': player_data['round_scores'][1] if player_data['round_scores'][1] > 1 else '-',
            'R3': player_data['round_scores'][2] if player_data['round_scores'][2] > 1 else '-',
            'R4': player_data['round_scores'][3] if player_data['round_scores'][3] > 1 else '-',
            'Strokes': player_data['total_strokes'],
            'MakeCut': player_data['makeCut']
        }
        
    # Create a list of players sorted by total score in ascending order
    sorted_players = sorted(leaderboard.items(), key=lambda x: x[1]['Total'])

    # Assign rank to each player based on their position in the sorted list
    rank = 1
    ties = 0
    prev_score = None
    
    # First iteration: Rank players who made the cut
    for player_id, player_data in sorted_players:
        if rd in [3, 4] and not player_data['MakeCut']:
            continue  # Skip players who didn't make the cut in round 3 and round 4

        if player_data['Total'] != prev_score:
            rank += ties
            ties = 1
        else:
            ties += 1

        leaderboard[player_id]['Rank'] = rank
        prev_score = player_data['Total']

    # Second iteration: Rank players who missed the cut
    if rd in [3, 4]:
        ties = 1
        for player_id, player_data in sorted_players:
            if player_data['MakeCut']:
                continue  # Skip players who made the cut

            if player_data['Total'] != prev_score:
                rank += ties
                ties = 1
            else:
                ties += 1

            leaderboard[player_id]['Rank'] = rank
            prev_score = player_data['Total']


    return leaderboard, r3r4Field


def update_ranks(leaderboard):
    ranked_players = []
    for i, player_id in enumerate(leaderboard):
        rank = i + 1
        if i > 0 and leaderboard[player_id]['Total'] == leaderboard[list(leaderboard)[i - 1]]['Total']:
            rank = leaderboard[list(leaderboard)[i - 1]]['Rank']
        leaderboard[player_id]['Rank'] = rank
        ranked_players.append(leaderboard[player_id])
    return ranked_players

def print_header(header):
    # Format the header and print it
    print('{:<5}{:<27}{:<6}{:<10}{:<6}{:<4}{:<4}{:<4}{:<4}{:<7}'.format(*header))
    # Print a line of dashes to separate the header from the rest of the leaderboard
    print('-' * 72)
    
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
    rank = player['Rank']
    total = player['Total']
    thru = player['Thru']
    r1 = player['R1']
    r2 = player['R2']
    r3 = player['R3']
    r4 = player['R4']
    strokes = player['Strokes']
    makeCut = playerData[player_id]['makeCut']

    # If the total is 0, change it to "E" for even
    if total == 0:
        total = 'E'
    # If the total is positive, add a plus sign to it and convert to a string
    elif total > 0:
        total = f'+{total}'

    if playerData[player_id]['started'] or playerData[player_id]['finished']:
        round_score = player['Round']
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
        if p_data['Rank'] in rank_counts:
            rank_counts[p_data['Rank']] += 1
        else:
            rank_counts[p_data['Rank']] = 1
    
    # Check if the player's makeCut value is 0 and it's the 3rd or 4th round
    if makeCut == 0 and rd in (3, 4):
        rank = "CUT"
    elif rank_counts[rank] > 1:
        rank = f"T{rank}"
        
    print(f"{rank:<5}{player['Player']:<27}{total:<6}{thru:<10}{round_scr:<6}{r1:<4}{r2:<4}{r3:<4}{r4:<4}{strokes:<7}")
    
def update_leaderboard_html(leaderboard, playerData, rd):
    html_leaderboard = {}
    
    for player_id in leaderboard.keys():
        player = leaderboard[player_id].copy()
        
        # Add the updated player to the html_leaderboard
        html_leaderboard[player_id] = player
        
        # Perform the updates as in the print_player function
        total = player['Total']
        if total == 0:
            total = 'E'
        elif total > 0:
            total = f'+{total}'
        
        player['Total'] = total

        if playerData[player_id]['started'] or playerData[player_id]['finished']:
            round_score = player['Round']
            if round_score == 0:
                round_scr = 'E'
            elif round_score > 0:
                round_scr = f'+{round_score}'
            else:
                round_scr = round_score
        else:
            round_scr = "-"
        
        player['Round'] = round_scr

        makeCut = playerData[player_id]['makeCut']
        rank = player['Rank']

        rank_counts = {}
        for p_id, p_data in leaderboard.items():
            if p_data['Rank'] in rank_counts:
                rank_counts[p_data['Rank']] += 1
            else:
                rank_counts[p_data['Rank']] = 1

        if makeCut == 0 and rd in (3, 4):
            rank = "CUT"
        elif rank_counts[rank] > 1:
            rank = f"T{rank}"
        
        player['Rank'] = rank

    return html_leaderboard


def print_projected_cutline(cut_index):
    print('-' * 72)
    print(f"Projected Cut Line: {cut_index}")
    print('-' * 72)


def print_top_half(made_cut, leaderboard, playerData, rd):
    # Create a dictionary to hold the data for the players who made the cut
    top_half = {}
    
    # Set the column header for the leaderboard
    header = ['Rank', 'Player', 'Total', 'Thru', 'Round', 'R1', 'R2', 'R3', 'R4', 'Strokes']

    # Print the header and separator
    print_header(header)
    
    for player_id, player_data in leaderboard.items():
        # If a player made the cut, add their data to the top_half dictionary
        if any(player['player_id'] == player_id for player in made_cut):
            top_half[player_id] = player_data

    # Print the leaderboard for players who made the cut
    for player in top_half.values():
        current_player_id = player['Player_id']
        print_player(current_player_id, leaderboard, playerData, rd)


def print_missed_cut(missed_cut, leaderboard, playerData, rd):
    sorted_mc = sorted(missed_cut, key=lambda x: x['total']) 
    print_separator(72)
    print("The following players missed the cut:")
    print_separator(72)
    
    # Print the leaderboard for players who missed the cut
    for player_data in sorted_mc:
        pid = player_data['player_id']
        print_player(pid, leaderboard, playerData, rd)
        

def calculate_cut(leaderboard, has_cut, cutline):
    if not has_cut:
        return None, list(leaderboard.keys())
    
    # Get the scores of players who are not disqualified and sort them
    scores = sorted([player['Total'] for player in leaderboard.values() if player['Total'] != '-'])

    # Determine the index of the cut line
    cut_index = min(cutline, len(scores))

    # Check if there are ties at the cut line and adjust the cut line if necessary
    while cut_index < len(scores) and scores[cut_index] == scores[cut_index - 1]:
        cut_index += 1

    # Set the cut score
    cut_score = scores[cut_index - 1] if cut_index > 0 else None

    # Get the IDs of the players who made the cut
    made_cut = [player_id for player_id, player in leaderboard.items() if player['Total'] != '-' and player['Total'] <= cut_score]

    return cut_score, made_cut


def print_leaderboard(leaderboard, active_season, active_week, tournament, purse, course_name, total_par, rd, hasCut, cutline, activePlayers, playerData):
    # Print the season and week of the tournament
    print(f"\nSeason: {active_season}\nWeek: {active_week}\n")
    # Print the tournament name, course name, and total par
    print(f"Tournament: {tournament}\nCourse: {course_name}\nPar: {total_par}\n\nPurse: {purse}\n")

    # Set the column header for the leaderboard
    header = ['Rank', 'Player', 'Total', 'Thru', 'Round', 'R1', 'R2', 'R3', 'R4', 'Strokes']

    # Print the header and separator
    print_header(header)

    # Calculate the cut score and get the players who made the cut
    cut_score, made_cut = calculate_cut(leaderboard, hasCut, cutline)

    # Print the leaderboard for all players
    counter = 0
    for player_id, player_data in leaderboard.items():
        counter += 1
        # If there is a cut and it is the second round, print the projected cut line
        if hasCut and rd == 2:
            # Count the number of players tied at the cutline
            num_ties = len([p for p in leaderboard.values() if p['Total'] == cut_score])
            if counter <= cutline or (counter == cutline + num_ties and num_ties > 1):
                print_player(player_id, leaderboard, playerData, rd)
                if counter == cutline:
                    print_projected_cutline(cut_score)
            elif counter > cutline + num_ties:
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
        for round_score in scores_dict[player]:
            for i in range(len(round_score)):
                score = round_score[i]
                par = hole_pars[i]
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
    first_place_score = next(player["Total"] for player in leaderboard.values() if player["Rank"] == 1)
    tied_players = [player for player in leaderboard.values() if player["Total"] == first_place_score]


    if len(tied_players) > 1:
        print("\nPlayoff needed!\n")

        hole_number = 1
        while len(tied_players) > 1:
            for player in tied_players:
                golfer = golfer_instances[player["Player_id"]]
                par = hole_pars[hole_number - 1]
                par3 = golfer.par3
                par4 = golfer.par4
                par5 = golfer.par5
                bogeyAvoid = golfer.bogeyAvoid
                player["PlayoffScore"] = create_score(golfer, par, par3, par4, par5, bogeyAvoid, course, condition)

            # Print the scores of all players in the playoff
            
            print(f"Playoff hole {hole_number} results:")
            for player in tied_players:
                print(f"{player['Player']} - Score: {player['PlayoffScore']}")
            print()
            # Eliminate players who don't match the lowest score
            lowest_playoff_score = min(player["PlayoffScore"] for player in tied_players)
            tied_players = [player for player in tied_players if player["PlayoffScore"] == lowest_playoff_score]

            hole_number += 1

        if len(tied_players) == 1:
            winner = tied_players[0]
            winner['Rank'] = f"{winner['Rank']}*"
            print(f"Playoff winner: {winner['Player']}")

    return leaderboard





# def run_tournament():
#     # Remove the line below, since you will be passing the connection as an argument
#     conn = sqlite3.connect('golf2.db')
#     c = conn.cursor()
#     made_cut = {}
#     missed_cut = {}
#     playerData = {}
#
#     # Clear all scores
#     # clear_scores(tid)
#
#     # Get active event id based on active_season and active_week
#     c.execute("SELECT schedule_id FROM Schedule WHERE Season=? AND Week=?", (active_season, active_week))
#     active_event_id = c.fetchone()[0]
#     # print(active_event_id)
#
#     # Get schedule information
#     tid, season, week, tournament, purse, fieldSize, hasCut, cutline = get_schedule_info(active_season, active_event_id)
#
#
#     # Get player field
#     field = get_field(fieldSize)
#     #print("Field: ", field)
#
#     # print("selected players: ",field)
#
#     # Assign R1 tee times
#     tee_times_dict, R1_tee_times, R2_tee_times = set_tee_times(field, 1, playerData)
#     print_tee_times(R1_tee_times, 1)
#
#
#     # Get course information
#     course_id, course_name, hole_pars, hole_handicaps, total_par = get_course_info()
#
#     # initialize tournament    
#     playerData = initialize_tournament(R1_tee_times, hole_pars)
#
#     # simulate R1
#     playerData, activePlayers, leaderboard, html_leaderboard = simulate_round(R1_tee_times, course_name, course_id, hole_pars, hole_handicaps, 1, playerData, tournament, purse, hasCut, cutline, made_cut, missed_cut, golfer_instances)
#
#
#     # print R2 tee times
#     print_tee_times(R2_tee_times, 1)
#     print_leaderboard(leaderboard, active_season, active_week, tournament, purse, course_name, total_par, 2, hasCut, cutline, activePlayers, playerData)
#     # simulate R2
#     playerData, activePlayers, leaderboard, html_leaderboard = simulate_round(R2_tee_times, course_name, tid, hole_pars, hole_handicaps, 2, playerData, tournament, purse, hasCut, cutline, made_cut, missed_cut, golfer_instances)
#
#     # process cut
#     if hasCut:
#          made_cut, missed_cut, leaderboard = process_cut(playerData, cutline, 3, leaderboard)      
#
#     # set tee times for R3
#     R3_tee_times, R1_tee_times, R2_tee_times = set_tee_times(made_cut, 3, playerData)
#     print_tee_times(R3_tee_times, 3)
#     print_top_half(made_cut, leaderboard, playerData, 3)
#     print_missed_cut(missed_cut, leaderboard, playerData, 3)
#
#     # simulate R3
#     playerData, activePlayers, leaderboard, html_leaderboard = simulate_round(R3_tee_times, course_name, tid, hole_pars, hole_handicaps, 3, playerData, tournament, purse, hasCut, cutline, made_cut, missed_cut, golfer_instances)
#
#
#     # set tee times for R4
#     made_cut, missed_cut = get_cut_lists(playerData, leaderboard)
#     R4_tee_times, R1_tee_times, R2_tee_times = set_tee_times(made_cut, 4, playerData)
#     print_tee_times(R4_tee_times, 4)
#     print_top_half(made_cut, leaderboard, playerData, 4)
#     print_missed_cut(missed_cut, leaderboard, playerData, 4)
#
#     # simulate R4
#     playerData, activePlayers, leaderboard, html_leaderboard = simulate_round(R4_tee_times, course_name, tid, hole_pars, hole_handicaps, 4, playerData, tournament, purse, hasCut, cutline, made_cut, missed_cut, golfer_instances)
#     print()
#
#     # Run the playoff if necessary
#     # Sort the made_cut list by total score in ascending order
#     rank_1_players = [player for player in leaderboard.values() if player["Rank"] == 1]
#
#     if len(rank_1_players) > 1:
#         # Call the playoff function with the sorted leaderboard
#         leaderboard = playoff(leaderboard, hole_pars, golfer_instances)
#
#     # Print the final leaderboard
#     print("\nFinal Leaderboard:")
#     #print(leaderboard)
# #    for player_id, player in leaderboard.items():
#         #print(f"{player['Rank']} - {player['Player']} - {player['Total']}")
#
#     # get stats
#     # stats = get_stats(playerData, hole_pars)
#     #
#     # # print stats
#     # headers = ['Ace', 'Alb', 'Eagle', 'Bird', 'Par', 'Bogie', 'DBogie', 'TBogie', 'Other']
#     # print_stats(stats, headers)
#
#     return leaderboard





def main():
    made_cut = {}
    missed_cut = {}
    playerData = {}

    # Clear all scores
    # clear_scores(tid)

    # Get active event id based on active_season and active_week
    c.execute("SELECT schedule_id FROM Schedule WHERE Season=? AND Week=?", (active_season, active_week))
    active_event_id = c.fetchone()[0]
    # print(active_event_id)

    # Get schedule information
    tid, season, week, tournament, purse, fieldSize, hasCut, cutline = get_schedule_info(active_season, active_event_id)


    # Get player field
    field = get_field(fieldSize)
    #print("Field: ", field)

    # print("selected players: ",field)

    # Assign R1 tee times
    tee_times_dict, R1_tee_times, R2_tee_times = set_tee_times(field, 1, playerData)
    print_tee_times(R1_tee_times, 1)


    # Get course information
    course_id, course_name, hole_pars, hole_handicaps, total_par = get_course_info()

    # initialize tournament    
    playerData = initialize_tournament(R1_tee_times, hole_pars)
    
    #course_difficulty & condition
    course_difficulty = "normal"
    course_condition = "normal"

    
    # simulate R1
    playerData, activePlayers, leaderboard, html_leaderboard = simulate_round(R1_tee_times, course_name, course_id, hole_pars, hole_handicaps, 1, playerData, tournament, purse, hasCut, cutline, made_cut, missed_cut, golfer_instances, course_difficulty, course_condition)

    # print R2 tee times
    print_tee_times(R2_tee_times, 1)
    print_leaderboard(leaderboard, active_season, active_week, tournament, purse, course_name, total_par, 2, hasCut, cutline, activePlayers, playerData)

    #course_difficulty & condition
    course_difficulty = "normal"
    course_condition = "hard"


    
    # simulate R2
    playerData, activePlayers, leaderboard, html_leaderboard = simulate_round(R2_tee_times, course_name, tid, hole_pars, hole_handicaps, 2, playerData, tournament, purse, hasCut, cutline, made_cut, missed_cut, golfer_instances, course_difficulty, course_condition)

    # process cut
    if hasCut:
         made_cut, missed_cut, leaderboard = process_cut(playerData, cutline, 3, leaderboard)      


    #course_difficulty & condition
    course_difficulty = "normal"
    course_condition = "easy"

    
    # set tee times for R3
    R3_tee_times, R1_tee_times, R2_tee_times = set_tee_times(made_cut, 3, playerData)
    print_tee_times(R3_tee_times, 3)
    print_top_half(made_cut, leaderboard, playerData, 3)
    print_missed_cut(missed_cut, leaderboard, playerData, 3)

    # simulate R3
    playerData, activePlayers, leaderboard, html_leaderboard = simulate_round(R3_tee_times, course_name, tid, hole_pars, hole_handicaps, 3, playerData, tournament, purse, hasCut, cutline, made_cut, missed_cut, golfer_instances, course_difficulty, course_condition)


    # set tee times for R4
    made_cut, missed_cut = get_cut_lists(playerData, leaderboard)
    R4_tee_times, R1_tee_times, R2_tee_times = set_tee_times(made_cut, 4, playerData)
    print_tee_times(R4_tee_times, 4)
    print_top_half(made_cut, leaderboard, playerData, 4)
    print_missed_cut(missed_cut, leaderboard, playerData, 4)

    #course_difficulty & condition
    course_difficulty = "hard"
    course_condition = "hard"

    # simulate R4
    playerData, activePlayers, leaderboard, html_leaderboard = simulate_round(R4_tee_times, course_name, tid, hole_pars, hole_handicaps, 4, playerData, tournament, purse, hasCut, cutline, made_cut, missed_cut, golfer_instances, course_difficulty, course_condition)
    print()

    # Run the playoff if necessary
    # Sort the made_cut list by total score in ascending order
    rank_1_players = [player for player in leaderboard.values() if player["Rank"] == 1]

    if len(rank_1_players) > 1:
        # Call the playoff function with the sorted leaderboard
        leaderboard = playoff(leaderboard, hole_pars, golfer_instances, course_difficulty, course_condition)

    # Print the final leaderboard
    print("\nFinal Leaderboard:")
    #print(leaderboard)
#    for player_id, player in leaderboard.items():
        #print(f"{player['Rank']} - {player['Player']} - {player['Total']}")

    # get stats
    # stats = get_stats(playerData, hole_pars)
    #
    # # print stats
    # headers = ['Ace', 'Alb', 'Eagle', 'Bird', 'Par', 'Bogie', 'DBogie', 'TBogie', 'Other']
    # print_stats(stats, headers)

#    conn.close()

main()
