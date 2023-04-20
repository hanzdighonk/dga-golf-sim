import random
from collections import Counter
import numpy as np
import sqlite3


best_improvement = 0
worst_improvement = 0
best_golfer = None
worst_golfer = None


def calculate_multiplier(difficulty):
    slope = -1 / 9
    intercept = 14 / 9
    multiplier = (slope * difficulty) + intercept
    return multiplier

def roll_score(par, par3_bird_better, par4_bird_better, par5_bird_better, bogey_avoid, course_difficulty, condition_difficulty):
    roll = random.randint(1, 10000)
    birdie_better_pct = 0
    bogey_pct = bogey_avoid

    course_multiplier = calculate_multiplier(course_difficulty)
    condition_multiplier = calculate_multiplier(condition_difficulty)
    print("Course Multi: ",course_multiplier)
    print("Condition Multi: ",course_multiplier)
    
    if par == 3:
        birdie_better_pct = par3_bird_better * course_multiplier * condition_multiplier
        hole_in_one = birdie_better_pct * 0.01
        birdie = birdie_better_pct * 0.98
        par_pct = 100 - birdie_better_pct - bogey_pct
    elif par == 4:
        birdie_better_pct = par4_bird_better * course_multiplier * condition_multiplier
        hole_in_one = birdie_better_pct * 0.0005
        eagle = birdie_better_pct * 0.025
        birdie = birdie_better_pct * 0.97
        par_pct = 100 - birdie_better_pct - bogey_pct
    elif par == 5:
        birdie_better_pct = par5_bird_better * course_multiplier * condition_multiplier
        double_eagle = birdie_better_pct * 0.0001
        eagle = birdie_better_pct * 0.15
        birdie = birdie_better_pct * 0.85
        par_pct = 100 - birdie_better_pct - bogey_pct
    
    print("Birdie better: ", birdie_better_pct)
    print("par: ", par_pct)
    
    
    cum_prob = 0
    if par == 3:
        cum_prob += hole_in_one
        if roll <= cum_prob * 100:
            return 1  # Hole-in-one
        cum_prob += birdie
        if roll <= cum_prob * 100:
            return 2  # Birdie
    elif par == 4:
        cum_prob += hole_in_one
        if roll <= cum_prob * 100:
            return 1  # Hole-in-one
        cum_prob += eagle
        if roll <= cum_prob * 100:
            return 2  # Eagle
        cum_prob += birdie
        if roll <= cum_prob * 100:
            return 3  # Birdie
    elif par == 5:
        cum_prob += double_eagle
        if roll <= cum_prob * 100:
            return 2  # Double-eagle
        cum_prob += eagle
        if roll <= cum_prob * 100:
            return 3  # Eagle
        cum_prob += birdie
        if roll <= cum_prob * 100:
            return 4  # Birdie

    cum_prob += par_pct
    if roll <= cum_prob * 100:
        return par  # Par

    cum_prob += bogey_pct * 0.95
    if roll <= cum_prob * 100:
        return par + 1  # Bogey

    cum_prob += bogey_pct * 0.04
    if roll <= cum_prob * 100:
        return par + 2  # Double Bogey
    
        cum_prob += bogey_pct * 0.009
    if roll <= cum_prob * 100:
        return par + 3  # Triple Bogey

    # Rare scores
    return par + random.randint(3, 5)


def create_score(golfer, par, par3, par4, par5, bogeyAvoid, course, condition):
    # Get the initial score
    score = roll_score(par, par3, par4, par5, bogeyAvoid, course, condition)

    # Call reroll_if_needed if the score is par+1 or worse
    if score >= par + 1:
        score = reroll_if_needed(score, par, golfer, par3, par4, par5, bogeyAvoid, course, condition)

    return score


def get_golfers_from_db():
    conn = sqlite3.connect("golf2.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Players")
    rows = cursor.fetchall()

    golfers = []
    for row in rows:
        golfer = Golfer(
            player_id=row[0],
            name=row[1],
            rating=row[9],
            par3=row[10],
            par4=row[11],
            par5=row[12],
            bogeyAvoid=row[13]
        )
        golfers.append(golfer)

    conn.close()

    return golfers


class Golfer:
    def __init__(self, player_id, name, rating, par3, par4, par5, bogeyAvoid):
        self.player_id = player_id
        self.name = name
        self.rating = rating
        self.par3 = par3
        self.par4 = par4
        self.par5 = par5
        self.bogeyAvoid = bogeyAvoid
        self.extra_rolls = self.get_extra_rolls()
        self.reroll_count = 0

    def get_extra_rolls(self):
        if self.rating >= 95:
            return 3
        elif self.rating >= 80:
            return 2
        elif self.rating >= 60:
            return 1
        else:
            return 0


class Hole:
    def __init__(self, hole_number, par, handicap):
        self.hole_number = hole_number
        self.par = par
        self.handicap = handicap

def generate_score(golfer, par):

    # Get the initial score
    score = roll_score(par)

    # Call reroll_if_needed if the score is par+1 or worse
    if score >= par + 1:
        score = reroll_if_needed(score, par, golfer)

    return score


def reroll_if_needed(score, par, golfer, par3, par4, par5, bogeyAvoid, course, condition):
    global best_improvement, worst_improvement, best_golfer, worst_golfer

    if golfer.extra_rolls > 0:
        # Calculate score difference from par
        score_diff = score - par

        # Determine if a reroll should be used based on the golfer's rating
        chance = (golfer.rating - 15) / 100

        # Check if golfer can reroll par+1 (rating of 95 or more) or par+2 (all other players)
        if (score_diff >= 2 and random.random() <= chance * 2):
            original_score = score
            score = roll_score(par, par3, par4, par5, bogeyAvoid, course, condition)
            golfer.extra_rolls -= 1
            golfer.reroll_count += 1
            print(f"Reroll used: {golfer.name} - Rerolls used: {golfer.reroll_count} - Rerolls left: {golfer.extra_rolls} - Old: {original_score}  New: {score}")

            # Calculate the improvement and update best and worst improvements
            improvement = original_score - score
            if improvement > best_improvement:
                best_improvement = improvement
                best_golfer = golfer.name
            elif improvement < worst_improvement:
                worst_improvement = improvement
                worst_golfer = golfer.name
        else:
            print(f"Reroll skipped: {golfer.name} - Rerolls used: {golfer.reroll_count} - Org: {score}")
    # print()
    # print(f"Best improvement: {best_golfer} with {best_improvement} strokes")
    # print(f"Worst improvement: {worst_golfer} with {worst_improvement} strokes")
    # print()
    return score


# # Test data
# golfers = get_golfers_from_db()
# hard = "hard"
# normal = "normal"
# easy = "easy"
#
# #par = 3
# par3_bird_better = 24.22
# par4_bird_better = 24.18
# par5_bird_better = 57.5
# bogey_avoid = 11.95
#
# # Generate 1000 scores for Par 3 holes
# scores3 = [roll_score(3, par3_bird_better, par4_bird_better, par5_bird_better, bogey_avoid, hard, hard) for _ in range(132)]
# scores4 = [roll_score(4, par3_bird_better, par4_bird_better, par5_bird_better, bogey_avoid, hard, hard) for _ in range(132)]
# scores5 = [roll_score(5, par3_bird_better, par4_bird_better, par5_bird_better, bogey_avoid, hard, hard) for _ in range(132)]
#
# # Count the occurrences of each score
# score_counts3 = Counter(scores3)
# score_counts4 = Counter(scores4)
# score_counts5 = Counter(scores5)
#
# # Calculate the average scores
# average_score3 = np.mean(scores3)
# average_score4 = np.mean(scores4)
# average_score5 = np.mean(scores5)
#
# # Print the results
# print("Generated scores for 1000 Par 3 holes:")
# for score, count in sorted(score_counts3.items()):
#     print(f"Score {score}: {count} times")
# print(f"Average Score for Par 3 holes: {average_score3:.2f}\n")
#
# print("Generated scores for 1000 Par 4 holes:")
# for score, count in sorted(score_counts4.items()):
#     print(f"Score {score}: {count} times")
# print(f"Average Score for Par 4 holes: {average_score4:.2f}\n")
#
# print("Generated scores for 1000 Par 5 holes:")
# for score, count in sorted(score_counts5.items()):
#     print(f"Score {score}: {count} times")
# print(f"Average Score for Par 5 holes: {average_score5:.2f}")

