#import libraries
from multiprocessing import Pool
import os
import time
from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers import pipeline
import json

#Parser Function:

    #PREPROCESSING
    #1. Unpack the input tuple
    #2. Load the correct file

    #PROCESSING
    #1. Identify the beginning of a proceeding
    #2. Do NER token recognition task
    #3. Reconstrutruct the String to include the tokens


def chopFile(args):

    #PREOROCESSING
    #Unpacking
    file = args[0]
    congress = args[1]
    session = args[2]

    #Readying the loader
    path = '/mnt/fstore/data_chrg'
    source = path + '/' + congress + '/' + session + '/html/' + file

    #Readying the processor objects
    days = ['MONDAY','TUESDAY','WEDNESDAY','THURSDAY','FRIDAY', 'SATURDAY','SUNDAY','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
    choppedText = ''

    #debug
    #print('Began parsing file '+source.split('/')[-1]+'\n')

    #Loading File
    with open(source,'r') as f:

        proceedingsFlag=False
        possibleProceedings = False

        #Parsing file line by line
        for line in f:

            #Identifying the beginning of the Proceedings
            if possibleProceedings and len(line.split()):
                if 'House of Representatives' in line or 'United States Senate' in line or 'U.S. Senate' in line:
                    #print('Proceedings',session,'\n')
                    proceedingsFlag = True
                else:
                    possibleProceedings = False

            if 'committee met' in line.casefold() or 'subcommittees met' in line.casefold() or 'subcommittee met' in line.casefold():
                proceedingsFlag = True
                choppedText = ''

            #Identifying the end of the proceedings
            if 'APPENDIX' in line.replace(' ','') and proceedingsFlag:
                proceedingsFlag = False
                #print('\nAPPENDIX '+session)
                break

            for day in days:
                if day in line and not proceedingsFlag:
                    possibleProceedings = True

            if not line.split():
                continue

            if line.isupper():
                continue

            #PROCESSING
            if proceedingsFlag:
                choppedText += line
                
    if choppedText:
        
        if congress not in os.listdir('/mnt/fstore/DataFiles/Chopped'):
            os.mkdir('/mnt/fstore/DataFiles/Chopped/'+congress)
        if session not in os.listdir('/mnt/fstore/DataFiles/Chopped/'+congress):
            os.mkdir('/mnt/fstore/DataFiles/Chopped/'+congress+'/'+session)
                    
        #debug
        print('Writing file '+session+'\n')

        with open('/mnt/fstore/DataFiles/Chopped/'+congress+'/'+session+'/Chopped'+session+'.chop', "a") as f:
            f.write(choppedText)
        return (session, True)
    else:
        return (session, False)

#Driver Function:

    #PREPROCESSING
    #1. Get list structure ready for Multiprocessing

    #PROCESSING
    #Call parser function with Pool.map

    #POSTPROCESSING
    #If Result text not empty, create foders and write text to file

def driver():

    args = []
    path = '/mnt/fstore/data_chrg'
    if 'NoProceedings.err' in os.listdir(os.getcwd()+'/Data/Errata'):
        with open(os.getcwd()+'/Data/Errata/NoProceedings.err', "r") as json_file:
                NoProceedings = json.load(json_file)
    else:
        NoProceedings = {}

    #iterating for the congress sessions
    for congress in os.listdir(path):
        if congress.isdigit():
            
            #debug
            print(congress)
            
            args = []

            #iterating over the hearing sessions for each congress session
            for session in os.listdir(path+'/'+congress):
                if 'CHRG-' in session and '.zip' not in session:
                    if 'html' in os.listdir(path+'/'+congress+'/'+session):
                        for file in os.listdir(path + '/' + congress + '/' + session + '/html/'):
                            if congress in os.listdir('/mnt/fstore/DataFiles/Chopped'):
                                if session in os.listdir('/mnt/fstore/DataFiles/Chopped/'+congress):
                                    continue
                            #if file exists, add the file details to the input list
                            args.append((file,congress,session))
            
            #PROCESSING
            with Pool(50) as pool:
                results = pool.map(chopFile,args)

            #POSTPROCESSING
            for result in results:

                if not result[1]:
                    if congress not in NoProceedings.keys():
                        NoProceedings[congress] = []
                    NoProceedings[congress].append(result[0])

    with open(os.getcwd()+'/Data/Errata/NoProceedings.err', "a") as f:
        json.dump(NoProceedings,f,indent=4,sort_keys=True,ensure_ascii=False)
    


if __name__ == '__main__':
    driver()