import praw
from datetime import datetime
import re
import json
from tqdm import tqdm

CLIENT_ID = 'XXXXXXXXXXXXXXXX'
SECRET_KEY = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'

username = 'XXXXXXXXXXXXXXXX'
userAgent = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
clientId = CLIENT_ID
clientSecret = SECRET_KEY
password = 'XXXXXXXXXXXXXX'

r = praw.Reddit(user_agent=userAgent, client_id=clientId, client_secret=clientSecret)

subreddit = r.subreddit('ama')

for submission in tqdm(subreddit.top(limit=1000)):
    data = {'post_id': submission.id,
            'post_title': submission.title,
            'post_score': submission.score,
            'post_creation_datetime': datetime.utcfromtimestamp(int(submission.created_utc)).strftime('%Y-%m-%d %H:%M:%S'),
            'post_over_18': submission.over_18,
            'content': []}

    # submission.comments.replace_more(limit=None)

    for top_level_comment in submission.comments:
      try:
        if top_level_comment is not None and top_level_comment.author is None:
          data['content'].append({'question_id': top_level_comment.id,
                                  'question_text': re.sub(' +', ' ', re.sub(r"[^\w\s?']", " ", top_level_comment.body.replace('\n', ' ').replace('_', ' ')).strip()),
                                  'answer_id': [x.id for x in top_level_comment.replies][0],
                                  'answer_text': [re.sub(' +', ' ', re.sub(r"[^\w\s?']", " ", x.body.replace('\n', ' ').replace('_', ' ')).strip()) for x in top_level_comment.replies][0],
                                  'question_score': top_level_comment.score,
                                  'question_creation_datetime': datetime.utcfromtimestamp(int(top_level_comment.created_utc)).strftime('%Y-%m-%d %H:%M:%S'),
                                  'question_edited': datetime.utcfromtimestamp(int(top_level_comment.edited)).strftime('%Y-%m-%d %H:%M:%S') if top_level_comment.edited is not False else top_level_comment.edited,
                                  'question_distinguished': top_level_comment.distinguished,
                                  'question_saved': top_level_comment.saved,
                                  'answer_score': [x.score for x in top_level_comment.replies][0],
                                  'answer_creation_datetime': [datetime.utcfromtimestamp(int(x.created_utc)).strftime('%Y-%m-%d %H:%M:%S') for x in top_level_comment.replies][0],
                                  'answer_edited': [datetime.utcfromtimestamp(int(x.edited)).strftime('%Y-%m-%d %H:%M:%S') if x.edited is not False else x.edited for x in top_level_comment.replies][0],
                                  'answer_distinguished': [x.distinguished for x in top_level_comment.replies][0],
                                  'answer_saved': [x.saved for x in top_level_comment.replies][0]})
        elif 'ama_compiler_bot' not in top_level_comment.author.name:
          data['content'].append({'question_id': top_level_comment.id,
                                  'question_text': re.sub(' +', ' ', re.sub(r"[^\w\s?']", " ", top_level_comment.body.replace('\n', ' ').replace('_', ' ')).strip()),
                                  'answer_id': [x.id for x in top_level_comment.replies][0],
                                  'answer_text': [re.sub(' +', ' ', re.sub(r"[^\w\s?']", " ", x.body.replace('\n', ' ').replace('_', ' ')).strip()) for x in top_level_comment.replies][0],
                                  'question_score': top_level_comment.score,
                                  'question_creation_datetime': datetime.utcfromtimestamp(int(top_level_comment.created_utc)).strftime('%Y-%m-%d %H:%M:%S'),
                                  'question_edited': datetime.utcfromtimestamp(int(top_level_comment.edited)).strftime('%Y-%m-%d %H:%M:%S') if top_level_comment.edited is not False else top_level_comment.edited,
                                  'question_distinguished': top_level_comment.distinguished,
                                  'question_saved': top_level_comment.saved,
                                  'answer_score': [x.score for x in top_level_comment.replies][0],
                                  'answer_creation_datetime': [datetime.utcfromtimestamp(int(x.created_utc)).strftime('%Y-%m-%d %H:%M:%S') for x in top_level_comment.replies][0],
                                  'answer_edited': [datetime.utcfromtimestamp(int(x.edited)).strftime('%Y-%m-%d %H:%M:%S') if x.edited is not False else x.edited for x in top_level_comment.replies][0],
                                  'answer_distinguished': [x.distinguished for x in top_level_comment.replies][0],
                                  'answer_saved': [x.saved for x in top_level_comment.replies][0]})
      except:
        pass

    json_string = json.dumps(data)
    with open('./AMA_Json/'+submission.id+'.json', 'w') as outfile:
      outfile.write(json_string)