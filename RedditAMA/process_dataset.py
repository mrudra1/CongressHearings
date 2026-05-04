import os
import re
import json

for filename in os.listdir('./AMA_Json'):
    print("Processing:", filename)
    with open('./AMA_Json/' + filename,'r') as f:
        data = json.loads(f.read())
    question_counter = 0
    answer_counter = 0
    for i in data['content']:
        q_text = re.sub(' +', ' ', re.sub(r"[^\w\s'?]", " ", i['question_text'].replace('\n', ' ')).strip())
        q_text = q_text.lower()
        with open('./AMA_Processed_Data_Q/Questions/' + os.path.splitext(filename)[0] + '_' + str(question_counter) +'.txt', 'w') as f:
            f.write(q_text)
        question_counter += 1

        a_text = re.sub(' +', ' ', re.sub(r"[^\w\s'?]", " ", i['answer_text'].replace('\n', ' ')).strip())
        a_text = a_text.lower()
        with open('./AMA_Processed_Data_Q/Answers/' + os.path.splitext(filename)[0] + '_' + str(answer_counter) +'.txt', 'w') as f:
            f.write(a_text)
        answer_counter += 1
