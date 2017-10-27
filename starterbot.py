import os
import time
from slackclient import SlackClient

# starterbot's ID as an environment variable
BOT_ID = os.environ.get("BOT_ID")

# constants
AT_BOT = "<@" + BOT_ID + ">"

# Time constants
T_START = 5
T_MAX = 15
T_END = 30

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
    return {"I" : [1], "V" : [1], "S" : [1], "N" : 0, "last_post_ts" : 0}

def calculate_msg_delay(user, ts):
    # TODO: Calculate the delay using user_dictionary[user]["last_post_ts"]

    last_post_ts = user_dictionary[user]
    latency = ts - last_post_ts
    if latency < T_START:
        return 0.3
    elif latency < T_MAX:
        return 1.2
    else:
        return 1



def update_user_importance(user):
    # incriment number of posts
    user_dictionary[user]["N"] = user_dictionary[user]["N"] + 1

    # TODO: Calculate user importance
    I = 0

    user_dictionary[user]["I"].insert(0, I)
    #this method will return the calculated importance I
    return I

def update_msg_similarity(user, msg):
    # TODO: Calculate message similarity over 'post_list'
    S = 0

    user_dictionary[user]["S"].insert(0, S)

    


    #this method will return the calculated importance I
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
    if user not in user_dictionary
        user_dictionary[user] = create_user()

    # Calculate the value for the user.
    V = calculate_user_value(user, msg, ts)

    # Store the current post.
    post_list.append(msg)

    # Update the latest post time foruser.
    user_dictionary[user]["last_post_ts"] = ts

    # Send response with calculated user value.
    response = "The current value for ''" + user "''" + \
               "is '" + user_dictionary[user]["V"][0] + "'"

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
            if output and 'text' in output:
                # return text after the @ mention, whitespace removed
                return output['text'], \
                       output['channel'], output['user'], output['ts']
    return None, None, None, None


if __name__ == "__main__":
    READ_WEBSOCKET_DELAY = 1 # 1 second delay between reading from firehose
    if slack_client.rtm_connect():
        print("CS598 Bot connected and running!")
        while True:
            msg, channel, user, ts = parse_slack_output(slack_client.rtm_read())
            if msg and channel and user and ts:
                handle_command(msg, channel, user, ts)
            time.sleep(READ_WEBSOCKET_DELAY)
    else:
        print("Connection failed. Invalid Slack token or bot ID?")
