# import libraries
from multiprocessing import Pool
import os
import time
from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers import pipeline
import json


def paraTokenizer(file):
    '''
    Objective:
        1. Identifying beginning and end of Proceeedings
        2. Splitting Proceedings into paragraphs
        3. Creating a single string containing the first line of each paraghraph

    Input: Text File

    Output: Text split into paragraphs, string containing the first line of every paragraph
    '''

    # Readying the processor objects
    days = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY',
        'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    paras = ['']
    text = ''
    counter = 0

    with open(file, 'r') as f:
        proceedingsFlag = False
        possibleProceedings = False

        # Parsing file line by line
        for line in f:

            # Identifying the beginning of the Proceedings
            if possibleProceedings and len(line.split()):
                if 'House of Representatives' in line or 'United States Senate' in line or 'U.S. Senate' in line:
                    # print('Proceedings',session,'\n')
                    proceedingsFlag = True
                else:
                    possibleProceedings = False

            if 'committee met' in line or 'subcommittees met' in line or 'subcommittee met' in line:
                proceedingsFlag = True
                paras = ['']
                text = []
                counter = 0

            # Identifying the end of the proceedings
            if 'APPENDIX' in line.replace(' ', '') and proceedingsFlag:
                proceedingsFlag = False
                # print('\nAPPENDIX '+session)
                break

            for day in days:
                if day in line and not proceedingsFlag:
                    possibleProceedings = True

            if not line.split():
                continue

            if line.isupper():
                continue

            # PROCESSING
            if proceedingsFlag:

                if len(line.split()) > 2 and line[:3].isspace():
                    counter += 1
                    text += '<nl>'+line
                    paras.append('')

                paras[counter] += line

    return paras, text


def reconstructor(ner_results, line):
    start = 0
    end = len(line)
    text = ''

    for result in ner_results:
        end = result['start']
        text += line[start:end]+'<'+result['entity'] + '> ' + result['word'] + ' <' + result['entity']+'-end>'
        start = result['end']
        if start < len(line):
            text += line[start:]

    return text

def matcher(paras, text):

    texts = text.split('<nl>')
    result = ''
    for i in range(len(texts)):
        if '<B-PER>' in text.split()[1]:
            result += paras[i][:paras[i].index(text.split()[0])] + '<member>' + paras[i][paras[i].index(text.split()[0]):paras[i].index(paras[i].split('.')[2]-1)] + '<member-end>' + paras[i][paras[i].index(paras[i].split('.')[2]-1):]
        else:
            result += paras[i]
    
    return result


# Parser Function:

    # PREPROCESSING
    # 1. Unpack the input tuple
    # 2. Load the correct file

    # PROCESSING
    # 1. Identify the beginning of a proceeding
    # 2. Do NER token recognition task
    # 3. Reconstrutruct the String to include the tokens


def parseFile(args):

    # PREOROCESSING
    # Unpacking
    file = args[0]
    congress = args[1]
    session = args[2]

    # Readying the loader
    path = '/mnt/fstore/data_chrg'
    source = path + '/' + congress + '/' + session + '/html/' + file

    # Readying the processor objects
    tokenizer = AutoTokenizer.from_pretrained("dslim/bert-base-NER")
    model = AutoModelForTokenClassification.from_pretrained(
        "dslim/bert-base-NER")
    nlp = pipeline("ner", model=model, tokenizer=tokenizer)
    parsedText = ''

    print('Tokenizer')
    paras, text = paraTokenizer(source)
    print('NER')
    ner_results = nlp(text)
    print('Reconstruction')
    reconstructedText = reconstructor(ner_results,text)
    print('Matcher')
    parsedText = matcher(paras, reconstructedText)

    if parsedText:

        if congress not in os.listdir(os.getcwd()+'/Data'):
            os.mkdir(os.getcwd()+'/Data/'+congress)
        if session not in os.listdir(os.getcwd()+'/Data/'+congress):
            os.mkdir(os.getcwd()+'/Data/'+congress+'/'+session)

        # debug
        print('Writing file '+session+'\n')

        with open(os.getcwd()+'/Data/'+congress+'/'+session+'/Parsed'+session+'.aner', "a") as f:
            f.write(parsedText)
        return (session, True)
    else:
        return (session, False)

# Driver Function:

    # PREPROCESSING
    # 1. Get list structure ready for Multiprocessing

    # PROCESSING
    # Call parser function with Pool.map

    # POSTPROCESSING
    # If Result text not empty, create foders and write text to file


def driver():

    with open('/home/manjari/CongressionalHearingsProject/HardcodedNER/Data/Errata/NoProceedings.err', "r") as json_file:
        NP = json.load(json_file)
    args = []
    path = '/mnt/fstore/data_chrg'
    if 'NoProceedings.err' in os.listdir(os.getcwd()+'/Data/Errata'):
        with open(os.getcwd()+'/Data/Errata/NoProceedings.err', "r") as json_file:
            NoProceedings = json.load(json_file)
    else:
        NoProceedings = {}

    # iterating for the congress sessions
    for congress in os.listdir(path):
        if congress.isdigit():

            # debug
            print(congress)

            args = []

            # iterating over the hearing sessions for each congress session
            for session in os.listdir(path+'/'+congress):
                if 'CHRG-' in session and '.zip' not in session:
                    if 'html' in os.listdir(path+'/'+congress+'/'+session):
                        for file in os.listdir(path + '/' + congress + '/' + session + '/html/'):
                            if congress in os.listdir('/home/manjari/CongressionalHearingsProject/AutomatedNERV2/Data'):
                                if session in os.listdir('/home/manjari/CongressionalHearingsProject/AutomatedNERV2/Data/'+congress):
                                    continue
                            if congress in NP.keys():
                                if session in NP[congress]:
                                    continue
                            # if file exists, add the file details to the input list
                            args.append((file, congress, session))

            # PROCESSING
            with Pool(40) as pool:
                results = pool.map(parseFile, args)

            # POSTPROCESSING
            for result in results:
                if congress not in NoProceedings.keys():
                    NoProceedings[congress] = []
                NoProceedings[congress].append(result[0])

    with open(os.getcwd()+'/Data/Errata/NoProceedings.err', "a") as f:
        json.dump(NoProceedings, f, indent=4, sort_keys=True,ensure_ascii=False)


if __name__ == '__main__':
    #driver()
    start = time.time()
    file = 'CHRG-108hhrg21510.htm'
    session = 'CHRG-108hhrg21510'
    parseFile((file, '108', session))
    end = time.time()
    print('Execution time of ANERV2 ', end-start, ' seconds')