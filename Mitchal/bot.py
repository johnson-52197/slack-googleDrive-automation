import logging
import slack
import os
import time
import config
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, request, Response, after_this_request
from slackeventsapi import SlackEventAdapter
import gdrive
from utils import utils
import folder_tree as ft
import folder_dict as fd

env_path = Path(".") / ".env"
load_dotenv(dotenv_path=env_path) 


logging.basicConfig(filename=f'log.log', format='%(asctime)s %(levelname)-8s %(message)s',
                    level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S', filemode='a')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

app = Flask(__name__)

slack_events_adapter = SlackEventAdapter(
    os.environ['SIGNING_SECRET'], '/slack/events', app)

client = slack.WebClient(token=os.environ['SLACK_TOKEN'])
BOT_ID = client.api_call('auth.test')['user_id']

def removePOST(channel_name: str, ts: float):
    logger.info('Request to remove post, Remove from: ' + channel_name)
    channelID = utils.getChannelID(channelName=channel_name)
    df_messages = pd.read_csv('messages.csv')
    df_messages['postTimeINT'] = df_messages['postTime'].astype(int)
    ts = int(ts)
    ts_list = [ts+i for i in range(1, 5)]
    msg_time = df_messages[(df_messages['postTimeINT'].isin(
        ts_list))]['postTime'].values[0].astype(str)
    df_messages = df_messages[~(df_messages['postTimeINT'].isin(ts_list))]
    client.chat_delete(channel=channelID, ts=str(msg_time))
    df_messages.to_csv('messages.csv', index=False)
    logger.info('Post removed!')
    return

def showTree(channelName: str, folderName: str, folderID: str):
    text = ft.FolderTree().show_tree(name=folderName, id=folderID)
    client.chat_postMessage(channel=channelName, text=str(text))
    return

@slack_events_adapter.on("reaction_added")
def reaction_added(event_data):
    emoji = event_data["event"]["reaction"]
    if emoji == 'white_check_mark':
        ts = event_data['event']['item']['ts']
        channel_id = event_data['event']['item']['channel']
        removePOST(channel_name='_data_entry', ts=float(ts))
        df = pd.read_csv('messages.csv')
        row = df[df['postTime'].astype(str) == str(ts)]

        @after_this_request
        def add_close_action(response):
            @response.call_on_close
            def process_after_request():
                gdrive.Drive().moveToCompleted(
                    channel_id=channel_id, id=str(row['id'].values[0]))
                df.drop(row.index, inplace=True)
                df.to_csv('messages.csv', index=False)
                logger.info('Marked as completed')
            return response
        return Response(), 200

    else:
        pass


@slack_events_adapter.on('message')
def message(payload):
    event = payload.get('event', {})
    channel_id = event.get('channel')
    user_id = event.get('user')
    text = event.get('text')
    return

@app.route("/showtree", methods=['GET', 'POST'])
def show():
    data = request.form
    channel_name = data.get('channel_name')
    folderName = config.drive_slack_info[channel_name]
    folderID = config.drive_id_info[folderName]

    @after_this_request
    def add_close_action(response):
        @response.call_on_close
        def process_after_request():
            showTree(folderName=folderName, folderID=folderID,
                        channelName=channel_name)
        return response
    return Response(), 200


@app.route("/purge", methods=['GET', 'POST'])
def test():
    data = request.form
    channel_name = data.get('channel_name')
    channel_id = data.get('channel_id')
    text = data.get('text')

    @after_this_request
    def add_close_action(response):
        @response.call_on_close
        def process_after_request():
            gdrive.Drive().purgeOldFiles(channel_id=channel_id,
                                         folder=channel_name, subFolder=text)
        return response
    return Response(), 200


@app.route('/move', methods=['POST'])
def move():
    data = request.form
    user_id = data.get('user_id')
    channel_id = data.get('channel_id')
    channel_name = data.get('channel_name')
    text = data.get('text')
    text = text.split(' to ')
    file = text[0].strip()
    folder = text[-1].strip()

    @after_this_request
    def add_close_action(response):
        @response.call_on_close
        def process_after_request():
            gdrive.Drive().moveFile(channel_name=channel_name, file=file, folder=folder)
        return response
    return Response(), 200


# if __name__ == "__main__":
#     drive = gdrive.Drive().get_authenticated()
#     host = config.IP
#     port = config.port
#     app.run(debug=False, host=host, port=port, use_reloader=False)


if __name__ == "__main__":
    drive = gdrive.Drive().get_authenticated()
    app.run(host = '127.0.0.1', port=5000)
 