#the inclusions go here
import os
from multiprocessing import Pool
import re
import json
import shutil
import traceback
import xmltodict
from nameparser import HumanName

#The XML to JSON converter
def parseXML(source):
    with open(source) as xml_file:
        data_dict = xmltodict.parse(xml_file.read())
    return data_dict


#The name list generator
def getNames(raw, session):
    metadata = {}
    errorList = []
    #Check if the Members structure is there at all
    if len(raw['mods']['extension'])<3:
        errorList.append('NoMembers')
        return errorList,None

    if 'congMember' not in raw['mods']['extension'][2]:
        errorList.append('NoMembers')
        return errorList,None

    #Setting the title of the hearing
    metadata['title'] = raw['mods']['titleInfo'][0]['title']

    #Fetching the Committee(s) of the hearing keeping in mind different structures found up till now
    metadata['committee'] = []
    if 'congCommittee' in raw['mods']['extension'][2]:
        if type(raw['mods']['extension'][2]['congCommittee']) is list:
            for commitee in raw['mods']['extension'][2]['congCommittee']:
                if type(commitee['name']) is list:
                    metadata['committee'].append(commitee['name'][0]['#text'])
                else:
                    metadata['committee'].append(commitee['name']['#text'])
        else:
            if type(raw['mods']['extension'][2]['congCommittee']['name']) is list:
                metadata['committee'].append(raw['mods']['extension'][2]['congCommittee']['name'][0]['#text'])
            else:
                metadata['committee'].append(raw['mods']['extension'][2]['congCommittee']['name']['#text'])
    elif 'otherHostingOrg' in raw['mods']['extension'][2]:
        if type(raw['mods']['extension'][2]['otherHostingOrg']) is list:
            for commitee in raw['mods']['extension'][2]['otherHostingOrg']:
                metadata['committee'].append(commitee)
        else:
            metadata['committee'].append(raw['mods']['extension'][2]['otherHostingOrg'])
    else:
        errorList.append('NoCommittee')
    
    #Fetching the witnesses by last name
    #This is not the most accurate method but it is the one that works on all documents without significant complexity of code
    metadata['witnesses'] = []
    witnesses = None

    if 'witness' in raw['mods']['extension'][2].keys():
        witnesses = raw['mods']['extension'][2]['witness']

    members = raw['mods']['extension'][2]['congMember']
    person = {}
    if type(witnesses) is list and len(witnesses):
        for witness in witnesses:
            person = {}
            for word in witness.split():
                if word[-1] == ',':
                    person['last'] = word[:-1]
                    person['Complete'] = witness
                    metadata['witnesses'].append(person)
                    break
    elif witnesses:
        for word in witnesses.split():
                if word[-1] == ',':
                    person['last'] = word[:-1]
                    person['Complete'] = witnesses
                    metadata['witnesses'].append(person)
                    break

    #Incase there are no witnesses we would like to know that
    if len(metadata['witnesses']) == 0:
        errorList.append('NoWitnesses')
        return errorList,None

    #Getting the names of the Congress Members
    metadata['members'] = []
    if not type(members) is list:
        person = {}
        if type(members['name']) is list:
            person['first'] = members['name'][1]['#text'].split()[0]
            person['last'] = members['name'][2]['#text'].split()[0][:-1]
            person['fCap'] = person['first'].upper()
            if 'of' in members['name'][0]['#text'].split():
                person['lCap'] = members['name'][0]['#text'].split()[members['name'][0]['#text'].split().index('of') - 1]
            else:
                person['lCap'] = person['last'].upper()
        else:

            errorList.append('MemberStructureIssue')

            if members['name']['#text'].split()[0].isupper() :
                person['fCap'] = members['name']['#text'].split()[0]
            else:
                person['first'] = members['name']['#text'].split()[0]
                person['fCap'] = person['first'].upper()
            
            if members['name']['#text'].split()[2] == 'of':
                if members['name']['#text'].split()[1].isupper():
                    person['lCap'] = members['name']['#text'].split()[1]
                else:
                    person['last'] = members['name']['#text'].split()[1]
                    person['lCap'] = person['last'].upper()
            else:
                person['middle'] = members['name']['#text'].split()[1]
                if members['name']['#text'].split()[2].isupper():
                    person['lCap'] = members['name']['#text'].split()[2]
                else:
                    person['last'] = members['name']['#text'].split()[2]
                    person['lCap'] = person['last'].upper()

        metadata['members'].append(person)
        return errorList, metadata

    for member in members:
        person = {}
        if type(member['name']) is list:
            person['first'] = member['name'][1]['#text'].split()[0]
            person['last'] = member['name'][2]['#text'].split()[0][:-1]
            person['fCap'] = person['first'].upper()
            if 'of' in member['name'][0]['#text'].split():
                person['lCap'] = member['name'][0]['#text'].split()[member['name'][0]['#text'].split().index('of') - 1]
            else:
                person['lCap'] = person['last'].upper()
        else:

            errorList.append('MemberStructureIssue')

            if member['name']['#text'].split()[0].isupper() :
                person['fCap'] = member['name']['#text'].split()[0]
            else:
                person['first'] = member['name']['#text'].split()[0]
                person['fCap'] = person['first'].upper()
            
            if member['name']['#text'].split()[2] == 'of':
                if member['name']['#text'].split()[1].isupper():
                    person['lCap'] = member['name']['#text'].split()[1]
                else:
                    person['last'] = member['name']['#text'].split()[1]
                    person['lCap'] = person['last'].upper()
            else:
                person['middle'] = member['name']['#text'].split()[1]
                if member['name']['#text'].split()[2].isupper():
                    person['lCap'] = member['name']['#text'].split()[2]
                else:
                    person['last'] = member['name']['#text'].split()[2]
                    person['lCap'] = person['last'].upper()

        metadata['members'].append(person)

    return errorList, metadata

def findMemberName(text, memberList):
    for member in memberList:
        if 'lcap' in member.keys():
            if member['lcap'] in text:
                return member
        if 'last' in member.keys():
            if member['last'] in text:
                return member

    return False

def getMemberByLastName(last, meta):
    namelist = []
    for member in meta['members']:
        if 'last' in member.keys() and 'lcap' in member.keys():
            if last == member['last'] or last == member['lCap']:
                namelist.append(member)
        elif 'last' in member.keys():
            if last == member['last']:
                namelist.append(member)
        elif 'lcap' in member.keys():
            if last == member['lcap']:
                namelist.append(member)

    return namelist

def getWitnessByLastName(last, meta):
    namelist = []
    for witness in meta['witnesses']:
        if last == witness['last']:
            namelist.append(witness)

    return namelist

def getMoreMembers(last, congress):
    with open(os.getcwd()+'/Data/members.meta', "r") as json_file:
        members = json.load(json_file)

    if congress in members.keys():
        for member in members[congress]:
            if last.casefold() == member['last_name'].casefold():
                return True
    
    return False

#The actual parser
def parseFile(args):

    file = args[0]
    congress = args[1]
    session = args[2]

    parsedText = ''

    path = '/mnt/fstore/data_chrg'
    errorList, metadata = getNames(parseXML(path +'/'+congress+'/'+session+'/mods.xml'), session)
    path = '/mnt/fstore/DataFiles/Chopped'
    source = path + '/' + congress + '/' + session + '/' + file
    
    if not metadata:
        # for error in errorList:
        #     parsedText['proceedings'] = error + '\n' + parsedText['proceedings']
        return (session, errorList)

    wordCount = 0
    wordCounts = []

    with open(source,'r') as f:
        for line in f:

                #if paragraph(line):
                if len(line.split())>2 and line.split()[1][-1] == '.':

                    #print(metadata['witnesses'])
                    memberList = getMemberByLastName(line.split()[1][:-1],metadata)
                    witnessList = None
                    if len(metadata['witnesses'])>0:
                        witnessList = getWitnessByLastName(line.split()[1][:-1],metadata)


                    if memberList or witnessList or getMoreMembers(line.split()[1][:-1],congress):
                        wordCounts.append(wordCount)
                        wordCount = len(line.split())
                        parsedText += line[0:line.index(line.split()[0])] +'<member>'+line[line.index(line.split()[0]):line.index(line.split()[1])+len(line.split()[1])]+'<member-end>' + line[line.index(line.split()[1])+len(line.split()[1]):]
                        memberList = None
                        continue

                    elif getMoreMembers(line.split()[1][:-1],congress):
                        wordCounts.append(wordCount)
                        wordCount = len(line.split())
                        parsedText += line[0:line.index(line.split()[0])] +'<member>'+line[line.index(line.split()[0]):line.index(line.split()[1])+len(line.split()[1])]+'<member-end>' + line[line.index(line.split()[1])+len(line.split()[1]):]
                        memberList = None
                        continue

                    elif not line[:3].split():
                        if line.split()[1][0].isupper():
                            if HumanName(line.split()[1]).first:
                                if len(line.split()[1][:-1].split('.'))<2:
                                    if len(parsedText):
                                        if (parsedText.split()[-1][-1] == '.' or parsedText.split()[-1][-1] == '!' or parsedText.split()[-1][-1] == '?'):
                                            wordCounts.append(wordCount)
                                            wordCount = len(line.split())
                                            parsedText += line[0:line.index(line.split()[0])] +'<member>'+line[line.index(line.split()[0]):line.index(line.split()[1])+len(line.split()[1])]+'<member-end>' + line[line.index(line.split()[1])+len(line.split()[1]):]
                                            memberList = None
                                            continue
                                    else:
                                        wordCounts.append(wordCount)
                                        wordCount = len(line.split())
                                        parsedText += line[0:line.index(line.split()[0])] +'<member>'+line[line.index(line.split()[0]):line.index(line.split()[1])+len(line.split()[1])]+'<member-end>' + line[line.index(line.split()[1])+len(line.split()[1]):]
                                        memberList = None
                                        continue

                parsedText += line
                wordCount += len(line.split())

    metadata['wordCounts'] = wordCounts
        
    if not len(parsedText):
        errorList.append('NoProceedings')
        # for error in errorList:
        #     parsedText['proceedings'] = error + '\n' + parsedText['proceedings']
        #metadata['contents'] = parsedText['contents']
        return (session, errorList)

    # for error in errorList:
    #         parsedText['proceedings'] = error + '\n' + parsedText['proceedings']
    
    # with open(source, 'r') as f:
    #     otext = f.read()

    # if  parsedText and len(parsedText.split('\n')) == len(otext.split('\n')):

    #     if congress not in os.listdir('/mnt/fstore/DataFiles/NER/HNER'):
    #         os.mkdir('/mnt/fstore/DataFiles/NER/HNER/'+congress)


    #     if session not in os.listdir('/mnt/fstore/DataFiles/NER/HNER/'+congress):
    #         os.mkdir('/mnt/fstore/DataFiles/NER/HNER/'+congress+'/'+session)
                    
    #     #debug
    #     print('Writing file '+session+'\n')

    #     #write the file
    #     with open('/mnt/fstore/DataFiles/NER/HNER/'+congress+'/'+session+'/Parsed'+session+'.hner', "a") as f:
    #         f.write(parsedText)

    #     #write the metadata
    #     with open('/mnt/fstore/DataFiles/NER/HNER/'+congress+'/'+session+'/mods.meta', "a") as f:
    #         json.dump(metadata,f,indent=4,sort_keys=True, ensure_ascii= False)

    print()
    
    return(session, errorList)

def driver():

    args = []
    path = '/mnt/fstore/DataFiles/Chopped'

    if 'NoProceedings.err' in os.listdir(os.getcwd()+'/Data/Errata'):
        with open(os.getcwd()+'/Data/Errata/NoProceedings.err', "r") as json_file:
                NoProceedings = json.load(json_file)
    else:
        NoProceedings = {}

    if 'MemberStructureIssue.err' in os.listdir(os.getcwd()+'/Data/Errata'):
        with open(os.getcwd()+'/Data/Errata/MemberStructureIssue.err', "r") as json_file:
                MemberStructureIssue = json.load(json_file)
    else:
        MemberStructureIssue = {}

    if 'NoCommittee.err' in os.listdir(os.getcwd()+'/Data/Errata'):
        with open(os.getcwd()+'/Data/Errata/NoCommittee.err', "r") as json_file:
                NoCommittee = json.load(json_file)
    else:
        NoCommittee = {}

    if 'NoMembers.err' in os.listdir(os.getcwd()+'/Data/Errata'):
        with open(os.getcwd()+'/Data/Errata/NoMembers.err', "r") as json_file:
                NoMembers = json.load(json_file)
    else:
        NoMembers = {}

    if 'NoWitnesses.err' in os.listdir(os.getcwd()+'/Data/Errata'):
        with open(os.getcwd()+'/Data/Errata/NoWitnesses.err', "r") as json_file:
                NoWitnesses = json.load(json_file)
    else:
        NoWitnesses = {}

    if 'ProceedingsIssue.err' in os.listdir(os.getcwd()+'/Data/Errata'):
        with open(os.getcwd()+'/Data/Errata/ProceedingsIssue.err', "r") as json_file:
                ProceedingsIssue = json.load(json_file)
    else:
        ProceedingsIssue = {}

    #iterating for the congress sessions
    for congress in os.listdir(path):
        if congress.isdigit():
            
            #debug
            print(congress)
            
            args = []

            #iterating over the hearing sessions for each congress session
            for session in os.listdir(path+'/'+congress):
                for file in os.listdir(path + '/' + congress + '/' + session):

                    #Ensure file has not been parsed already
                    if congress in os.listdir('/mnt/fstore/DataFiles/NER/HNER'):
                        if session in os.listdir('/mnt/fstore/DataFiles/NER/HNER/'+congress+'/'):
                            if 'Parsed'+session+'.hner' in os.listdir('/mnt/fstore/DataFiles/NER/HNER/'+congress+'/'+session):
                                continue
                    #if file exists, add the file details to the input list
                    args.append((file,congress,session))
            
            #PROCESSING
            with Pool(10) as pool:
                results = pool.map(parseFile,args)

            #POSTPROCESSING
            for result in results:
                
                if result[1]:

                    #First look for errors:
                    for error in result[1]:

                        if 'NoProceedings' == error:
                            if congress not in NoProceedings.keys():
                                NoProceedings[congress] = []
                            NoProceedings[congress].append(result[0])

                        if 'NoMembers' == error:
                            if congress not in NoProceedings.keys():
                                NoProceedings[congress] = []
                            NoProceedings[congress].append(result[0])

                        if 'MemberStructureIssue' == error:
                            if congress not in MemberStructureIssue.keys():
                                MemberStructureIssue[congress] = []
                            MemberStructureIssue[congress].append(result[0])

                        if 'NoCommittee' == error:
                            if congress not in NoCommittee.keys():
                                NoCommittee[congress] = []
                            NoCommittee[congress].append(result[0])

                        if 'NoMembers' == error:
                            if congress not in NoMembers.keys():
                                NoMembers[congress] = []
                            NoMembers[congress].append(result[0])

                        if 'NoWitnesses' == error:
                            if congress not in NoWitnesses.keys():
                                NoWitnesses[congress] = []
                            NoWitnesses[congress].append(result[0])

                        if 'ProceedingsIssue' == error:
                            if congress not in ProceedingsIssue.keys():
                                ProceedingsIssue[congress] = [] 
                            ProceedingsIssue[congress].append(result[0])

    with open(os.getcwd()+'/Data/Errata/NoProceedings.err', "a") as f:
        json.dump(NoProceedings,f,indent=4,sort_keys=True,ensure_ascii=False)

    with open(os.getcwd()+'/Data/Errata/MemberStructureIssue.err', "a") as f:
        json.dump(MemberStructureIssue,f,indent=4,sort_keys=True,ensure_ascii=False)

    with open(os.getcwd()+'/Data/Errata/NoCommittee.err', "a") as f:
        json.dump(NoCommittee,f,indent=4,sort_keys=True,ensure_ascii=False)

    with open(os.getcwd()+'/Data/Errata/NoMembers.err', "a") as f:
        json.dump(NoMembers,f,indent=4,sort_keys=True,ensure_ascii=False)

    with open(os.getcwd()+'/Data/Errata/NoWitnesses.err', "a") as f:
        json.dump(NoWitnesses,f,indent=4,sort_keys=True,ensure_ascii=False)

    with open(os.getcwd()+'/Data/Errata/ProceedingsIssue.err', "a") as f:
        json.dump(ProceedingsIssue,f,indent=4,sort_keys=True,ensure_ascii=False)

    return True

if __name__ == '__main__':
    #driver()
    parseFile(('CHRG-114hhrg20557','114','CHRG-114hhrg20557'))