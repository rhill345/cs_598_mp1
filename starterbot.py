import os
import time
from slackclient import SlackClient
from fuzzywuzzy import fuzz

# starterbot's ID as an environment variable
BOT_ID = os.environ.get("BOT_ID")

# constants
AT_BOT = "<@" + BOT_ID + ">"
AUTO_RESPONSE = "[AUTO RESPONSE] "

# Time constants
T_START = 5
T_MAX = 15
T_END = 30

# Similarity constants
S1 = 0.3
S2 = 0.95

# Value constants
VD_MAX = 1
VD_INF = 0.9
VS_MAX = 1

# Author constants
ALPHA = 3
BETA = 1.5
GAMMA = 0.3

user_dictionary = {}
post_list = []

# instantiate Slack & Twilio clients
slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))


def create_user():
    return {"I": [1], "V": [1], "S": [1], "N": 0, "last_post_ts": 0}


def calculate_msg_delay(user, ts):
    last_post_ts = user_dictionary[user]["last_post_ts"]
    latency = ts - last_post_ts
    if latency < T_START:
        return latency
    elif latency < T_MAX:
        return 1.2
    else:
        return 1


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

    user_dictionary[user]["I"].insert(0, I)
    return I


def update_msg_similarity(user, msg):
    S = 1.2
    similarity = 0
    for post in post_list:
        similarity = max(compare_similarity(msg, post), similarity)

    if similarity < 10:
        S = 1
    elif similarity > 95:
        S = 0.2

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

    # Create a user if it does not exists.
    if user not in user_dictionary:
        user_dictionary[user] = create_user()

    ts_long = long(float(ts));
    # Calculate the value for the user.
    V = calculate_user_value(user, msg, ts_long)

    # Store the current post.
    post_list.append(msg)

    # Update the latest post time foruser.
    user_dictionary[user]["last_post_ts"] = ts_long;

    # Send response with calculated user value.
    response = AUTO_RESPONSE + "Your value is '" + str(V) + "'"

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
            if output and 'text' in output and AUTO_RESPONSE not in output['text']:
                # return text after the @ mention, whitespace removed
                return output['text'], \
                       output['channel'], output['user'], output['ts']
    return None, None, None, None


def compare_similarity(sentence1, sentence2):
    return fuzz.ratio(sentence1, sentence2)


if __name__ == "__main__":
    READ_WEBSOCKET_DELAY = 1  # 1 second delay between reading from firehose
    if slack_client.rtm_connect():
        print("CS598 Bot connected and running!")
        while True:
            msg, channel, user, ts = parse_slack_output(slack_client.rtm_read())
            if msg and channel and user and ts:
                handle_post_for_user(msg, channel, user, ts)
            time.sleep(READ_WEBSOCKET_DELAY)
    else:
        print("Connection failed. Invalid Slack token or bot ID?")
