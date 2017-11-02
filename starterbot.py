import os
import time
import re, math
from collections import Counter
from slackclient import SlackClient
# from fuzzywuzzy import fuzz
import operator

# starterbot's ID as an environment variable
BOT_ID = os.environ.get("BOT_ID")

# constants
AT_BOT = "<@" + BOT_ID + ">"

SCORE_COMMAND = "printscore"

AUTO_RESPONSE = "[AUTO RESPONSE] "

# Time constants
T_START = 5
T_MAX = 15
T_END = 30

# Similarity constants
S1 = 0.3
S2 = 0.80

# Value constants
VD_MAX = 1
VD_INF = 0.9
VS_MAX = 1

# Author constants
ALPHA = 3
BETA = 1.5
GAMMA = 0.3

VMAX = 5
TIE = 0.2
TDS = 0.9

user_dictionary = {}
post_list = []

# instantiate Slack & Twilio clients
slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))

# participation cycle time
COMMUNITY_REWARD = 1.2
COMMUNITY_THRESHOLD = 10
COMMUNITY_REWARD_TIME = 36

participation_cycle_start_ts = 0
participation_cycle_post_count = 0

WORD = re.compile(r'\w+')


def get_cosine(vec1, vec2):
    intersection = set(vec1.keys()) & set(vec2.keys())
    numerator = sum([vec1[x] * vec2[x] for x in intersection])

    sum1 = sum([vec1[x] ** 2 for x in vec1.keys()])
    sum2 = sum([vec2[x] ** 2 for x in vec2.keys()])
    denominator = math.sqrt(sum1) * math.sqrt(sum2)

    if not denominator:
        return 0.0
    else:
        return float(numerator) / denominator


def text_to_vector(text):
    words = WORD.findall(text)
    return Counter(words)


def create_user():
    return {"I": 1, "V": [1], "S": [float(1)], "N": 0, "last_post_ts": 0}


def calculate_msg_delay(user, ts):
    last_post_ts = user_dictionary[user]["last_post_ts"]
    latency = ts - last_post_ts
    return f_delay(latency)

def f_delay(d):
    if d <= T_START:
        lam = 1.0 * VD_INF / (math.exp(T_START) - 1)
        return lam * (math.exp(d) - 1)
    elif d <= T_MAX:
        b = 1.0 * (T_MAX / T_START * VD_INF - VS_MAX) / (T_MAX**2 - T_MAX * T_START)
        a = 1.0 * (VD_INF + b * (T_START**2)) / T_START
        return a*d - b*(d**2)
    else:
        lam = 1.0 * (VS_MAX - VD_INF) * math.exp(T_MAX)
        return lam * math(-d) + VD_INF


def calculate_similarity_value(sim):
    Vmax = 5
    if sim < TIE:
        return
    if sim >= TIE and sim <= TDS:
        return VS_MAX
    else:
        return


def update_user_importance(user):
    # incriment number of posts
    user_dictionary[user]["N"] = user_dictionary[user]["N"] + 1

    # TODO: Calculate user importance
    I = 0
    N = user_dictionary[user]["N"]

    Vs = user_dictionary[user]["V"]
    Vsum = 0
    for i in Vs:
        Vsum += i
    Vmean = Vsum / N

    Ss = user_dictionary[user]["S"]
    Ssum = 0
    for i in Ss:
        Ssum += i
    Smean = Ssum / i

    c = 0
    if Smean > S1 and Smean < S2:
        c = ALPHA
    elif Smean <= S1:
        c = BETA
    else:
        c = GAMMA

    I = N * Vmean * c

    user_dictionary[user]["I"] = I
    return I


def update_msg_similarity(user, msg):
    similarity = 0
    C = 0
    for post in post_list:
        current_sim = calculate_similarity_value(compare_similarity(msg, post[1]))
    if len(post_list) == 0:
        S = 1
    else:
        S = similarity / len(post_list)

    user_dictionary[user]["S"].insert(0, S)
    return S


def calculate_user_value(user, msg, ts):
    # Calculate the value.
    # V = I (ds)
    D = calculate_msg_delay(user, ts)
    I = update_user_importance(user)
    S = update_msg_similarity(user, msg)
    V = I * S * D

    # Add value to the dictionary.
    user_dictionary[user]["V"].insert(0, V)

    # Return the calculated value.
    return V


def handle_post_for_user(msg, channel, user, ts):
    """
        Receives commands directed at the bot and determines if they
        are valid commands. If so, then acts on the commands. If not,
        returns back what it needs for clarification.
    """
    participation_cycle_post_count
    # Create a user if it does not exists.
    if user not in user_dictionary:
        user_dictionary[user] = create_user()

    ts_long = long(float(ts));
    # Calculate the value for the user.
    V = calculate_user_value(user, msg, ts_long)

    # Store the current post.
    post_list.append((user, msg))

    # Update the latest post time foruser.
    user_dictionary[user]["last_post_ts"] = ts_long;

    # Send response with calculated user value.
    response = AUTO_RESPONSE + "V: '" + str(V) + "'  I: " + str(user_dictionary[user]["I"]) + "'" + "'  S: " + str(
        user_dictionary[user]["S"][0]) + "'"

    slack_client.api_call("chat.postMessage", channel=channel,
                          text=response, as_user=True)


# We can use this method to parse and slack input.  This is currently filtering
# by the bot name.
def parse_slack_output(slack_rtm_output):
    """
        The Slack Real Time Messaging API is an events firehose.
        this parsing function returns None unless a message is
        directed at the Bot, based on its ID.
    """
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output and 'text' in output and BOT_ID not in output['user']:
                # return text after the @ mention, whitespace removed
                return output['text'], \
                       output['channel'], output['user'], output['ts']
    return None, None, None, None


def compare_similarity(sentence1, sentence2):
    vector1 = text_to_vector(sentence1)
    vector2 = text_to_vector(sentence2)
    return get_cosine(vector1, vector2)


#    return fuzz.partial_token_set_ratio(sentence1, sentence2) / float(100)

def update_community_reward(ts):
    global participation_cycle_start_ts
    ts_long = long(float(ts));
    if participation_cycle_start_ts == 0:
        participation_cycle_start_ts = ts_long

    ts_hours = (((ts_long - participation_cycle_start_ts) / (1000 * 60 * 60)) % 24);
    if ts_hours >= COMMUNITY_REWARD_TIME:
        n_agents = len(user_dictionary)
        for key in user_dictionary:
            n_post += len(user_dictionary[key]["V"])

        if n_post > (COMMUNITY_THRESHOLD * n_agents):
            for key in user_dictionary:
                user_dictionary[key]["V"] = [i * COMMUNITY_REWARD for i in user_dictionary[key]["V"]]

        participation_cycle_start_ts = ts_long


def print_final_vals(channel):
    final_normalized_val = calculate_final_points(user_dictionary)
    sorted_point = sorted(final_normalized_val.items(), key=operator.itemgetter(1))
    response = ""
    for item in sorted_point:
        print "user " + item[0] + " final reward point is " + str(item[1])
        response += '<@' + item[0] + '>' + ' : ' + str(item[1]) + '\n'

    slack_client.api_call("chat.postMessage", channel=channel,
                          text=response, as_user=True)


def calculate_final_points(user_dictionary):
    final_values = {}
    max_val = float("-inf")
    for user in user_dictionary:
        sum = 0
        values = user_dictionary[user]["V"]
        for v in values:
            sum += v
        final_values[user] = sum
        if sum > max_val:
            max_val = sum

    final_normalized_values = {}
    for user in final_values:
        nor_val = final_values[user] / max_val * 5
        final_normalized_values[user] = nor_val

    return final_normalized_values

if __name__ == "__main__":
    READ_WEBSOCKET_DELAY = 1  # 1 second delay between reading from firehose
    if slack_client.rtm_connect():
        print("CS598 Bot connected and running!")
        while True:
            msg, channel, user, ts = parse_slack_output(slack_client.rtm_read())
            if msg and channel and user and ts:
                update_community_reward(ts)
                if msg.startswith(AT_BOT) and SCORE_COMMAND in msg:
                    print_final_vals(channel)
                else:
                    handle_post_for_user(msg, channel, user, ts)
            time.sleep(READ_WEBSOCKET_DELAY)
    else:
        print("Connection failed. Invalid Slack token or bot ID?")
