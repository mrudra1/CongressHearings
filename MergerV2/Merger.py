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

def finder(aner, text):
    return 'Hi'
def parseMerger(deets):

    #Unpack the tupples
    congress, session = deets

    #Fetch the files
    aner_source = '/mnt/fstore/DataFiles/NER/ANER/'+congress+'/'+session+'/'+'Parsed'+session+'.aner'
    hner_source = '/mnt/fstore/DataFiles/NER/HNER/'+congress+'/'+session+'/'+'Parsed'+session+'.hner'

    with open(aner_source,'r') as a:
        with open(hner_source,'r') as h:
            
            aner = a.read().split('\n')
            hner = h.read().split('\n')

            ai = 0 #The ANER iterator
            hi = 0 #The HNER iterator
            text = '' #The final text

            while hi<len(hner) and ai<len(aner):

                # if tagRemover(aner[ai]).isupper():
                #     ai+=1
                #     hi+=1
                #     continue

                ##Assumption 1: ANER will have have the same text in either the same line or the subsequent next line.
                ##Assumption 2: Each tag can only be in one line, it cannot be split across lines.

                if tagRemover(hner[hi]).replace(' ','') == tagRemover(aner[ai]).replace(' ',''):
                    #print('Found Equality')
                        
                    if '<member>' in hner[hi]:
                        text += hner[hi] + '\n'
                        ai+=1
                        hi+=1
                        continue
                    elif '<member>' in aner[ai]:
                        text+= aner[ai] +'\n'
                        ai+=1
                        hi+=1
                        continue
                    else: 
                        text += hner[hi]+'\n'
                        hi+=1
                        ai+=1

                else:
                    # print(hi,ai)
                    # print(hner[hi],aner[ai])
                    if tagRemover(hner[hi+1]).replace(' ','') == tagRemover(aner[ai+1]).replace(' ',''):
                        text += hner[hi]+'\n'
                        hi+=1
                        ai+=1
                    else:
                        hi+=1
                        ai+=1
                #Check if beginning with paragraph
                """if '<member>' in hner[hi]:
                    while ai < len(aner):
                        if tagRemover(aner[ai]).isUpper():
                            i+=1
                        if tagRemover(hner[hi]) == tagRemover(aner[ai]):
                            if aner[ai].splt(' ')[1][0] == '<':
                                if len(line.split())>2 """

                            
                #Read both lines
                #Get rid of tags from both lines
                #check for equality
                    #if equal:
                    #Decide Named Entity
                    #increment both
                #Otherwise Incriment the ANER
    if len(text.split('\n')) == len(hner) or len(text.split('\n')) == len(hner)+1:
        print('Writing File ', session)
        if congress not in os.listdir('/mnt/fstore/DataFiles/Merged'):
            os.mkdir('/mnt/fstore/DataFiles/Merged/'+congress)
        if session not in os.listdir('/mnt/fstore/DataFiles/Merged/'+congress):
            os.mkdir('/mnt/fstore/DataFiles/Merged/'+congress+'/'+session)
        with open('/mnt/fstore/DataFiles/Merged/'+congress+'/'+session+'/Merged'+session+'.mer', "a") as f:
            f.write(text)
            return (True, session)
    else:
        print('Length of hner : ',len(hner),' Length of text', len(text.split('\n')))
        return (False, session)

def driver():

    path = '/mnt/fstore/DataFiles/NER/HNER'
    path1 = '/mnt/fstore/DataFiles/NER/ANER'
    args = []
    errors = {
    }

    #parseMerger(('108','CHRG-108hhrg20052'))
    for congress in os.listdir(path):
        args = []
        for session in os.listdir(path+'/'+congress):
            if session in os.listdir(path1+'/'+congress):
                args.append((congress,session))
    
        with Pool(30) as pool:
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
    #parseMerger(('105','CHRG-105hhrg43774'))
