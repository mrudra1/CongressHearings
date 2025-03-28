#imports
import os
from multiprocessing import Pool
import json

def labelSplitter(deets):

    #Unpack the tupples
    congress, session = deets

    #Fetch the files
    source = '/mnt/fstore/DataFiles/Split/'+congress+'/'+session+'/'+'Split'+session+'.spl'

    with open(source, "r") as json_file:
        try:
            texts = json.load(json_file)
        except Exception as err:
            print(session, err)
            return False
    #print(session)

    for i in range(len(texts)):
        if texts[i]['label'] == 'Q':
            with open('/mnt/fstore/DataFiles/LabeledFiles/Questions/'+'Labeled'+session+'_'+ str(texts[i]['ID']) +'.lbd', "a") as f:
                json.dump([texts[i-1],texts[i],texts[i+1]],f,indent=4,ensure_ascii=False)

        if texts[i]['label'] == 'A':
            with open('/mnt/fstore/DataFiles/LabeledFiles/Answers/'+'Labeled'+session+'_'+ str(texts[i]['ID']) +'.lbd', "a") as f:
                json.dump([texts[i-1],texts[i],texts[i+1]],f,indent=4,ensure_ascii=False)
        
        if texts[i]['label'] == 'S':
            with open('/mnt/fstore/DataFiles/LabeledFiles/Statements/'+'Labeled'+session+'_'+ str(texts[i]['ID']) +'.lbd', "a") as f:
                json.dump([texts[i-1],texts[i],texts[i+1]],f,indent=4,ensure_ascii=False)

    return True

def driver():

    path = '/mnt/fstore/DataFiles/Split'
    args = []

    for congress in os.listdir(path):
        args = []
        for session in os.listdir(path+'/'+congress):
            args.append((congress,session))
    
        with Pool(50) as pool:
            results = pool.map(labelSplitter,args)
        


if __name__ == '__main__':
    driver()
