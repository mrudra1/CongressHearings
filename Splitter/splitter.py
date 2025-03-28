#imports
import os
from multiprocessing import Pool
import json

def tagRemover(text):

    flag = False
    reText = ''
    for char in text:
        if flag:
            if char == '>':
                flag = False
                continue
            else:
                continue
        
        if char == '<':
            flag = True
            continue

        if char == '#':
            continue

        reText +=char

    return reText

def parseMerger(deets):

    #Unpack the tupples
    congress, session = deets

    #Fetch the files
    source = '/mnt/fstore/DataFiles/Merged/'+congress+'/'+session+'/'+'Merged'+session+'.mer'

    #initiate variables
    texts = [] #for the entire proceeding
    text = ''   #for a single utterance
    pLen = []    #Length of the entire proceeding
    uLen = 0    #Length of a proceeding
    length = 0

    with open(source,'r') as f:

        for line in f:

            length+=1

            if '<member>' in line and text:
                pLen.append(uLen)
                text = text.replace('\n','')
                texts.append({'label':'','utterance':text, 'length':uLen, 'ID':len(texts)})
                uLen = 0
                text = ''
                text+= tagRemover(line)
                uLen+=len(line.split())
            
            else:
                uLen+=len(line.split())
                text += line

    #sanity check and write file
    with open(source,'r') as f:
        oLen = f.read().split('\n')
        if length == len(oLen) or length == len(oLen)-1 and len(texts):
            print('Writing File ', session)
            if congress not in os.listdir('/mnt/fstore/DataFiles/Split'):
                os.mkdir('/mnt/fstore/DataFiles/Split/'+congress)
            if session not in os.listdir('/mnt/fstore/DataFiles/Split/'+congress):
                os.mkdir('/mnt/fstore/DataFiles/Split/'+congress+'/'+session)
            with open('/mnt/fstore/DataFiles/Split/'+congress+'/'+session+'/Split'+session+'.split', "a") as f:
                json.dump(texts, f, indent = 4, ensure_ascii = False, sort_keys=True)
            with open('/mnt/fstore/DataFiles/Split/'+congress+'/'+session+'/stats.split', "a") as f:
                json.dump(pLen, f, indent = 4, ensure_ascii = False, sort_keys=True)
                return (True, session)
        else:
            print('Length of hner : ',len(oLen),' Length of text', length)
            return (False, session)

def driver():

    path = '/mnt/fstore/DataFiles/Merged'
    path1 = '/mnt/fstore/DataFiles/Split'
    args = []
    errors = {
    }

    for congress in os.listdir(path):
        args = []
        for session in os.listdir(path+'/'+congress):
            if congress in os.listdir(path1):
                if session in os.listdir(path1+'/'+congress):
                    if 'Split'+session+'.split' in os.listdir(path1+'/'+congress+'/'+session):
                        continue
            args.append((congress,session))
    
        with Pool(50) as pool:
            results = pool.map(parseMerger,args)

        for result in results:
            if result:
                error, session = result
                if congress not in errors.keys():
                    errors[congress] = []
                if not error:
                    errors[congress].append(session)

        errors[congress].sort()
    
    with open(os.getcwd()+'/Data/Errata/ANER_HNER_Mismatch.err', "a") as f:
        json.dump(errors,f,indent=4,sort_keys=True,ensure_ascii=False)


if __name__ == '__main__':
    driver()
