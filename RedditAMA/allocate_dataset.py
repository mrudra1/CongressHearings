import os

count = 0
for filename in os.listdir('./AMA_Processed_Data_Q/Questions'):
    if count <= 54681:
        os.system('cp ./AMA_Processed_Data_Q/Questions/' + filename + ' ./AMA_Processed_Data_Q/Training/Questions/')
    else:
        os.system('cp ./AMA_Processed_Data_Q/Questions/' + filename + ' ./AMA_Processed_Data_Q/Testing/Questions/')
    count+=1

count = 0
for filename in os.listdir('./AMA_Processed_Data_Q/Answers'):
    if count <= 54681:
        os.system('cp ./AMA_Processed_Data_Q/Answers/' + filename + ' ./AMA_Processed_Data_Q/Training/Answers/')
    else:
        os.system('cp ./AMA_Processed_Data_Q/Answers/' + filename + ' ./AMA_Processed_Data_Q/Testing/Answers/')
    count+=1
