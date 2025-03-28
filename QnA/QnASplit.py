#the inclusions go here
import os
from multiprocessing import Pool
import json
import xmltodict
from nela_features.nela_features import NELAFeatureExtractor

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

    #debug
    #print(json.dumps(raw, indent=2))

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
        if '@party' in members.keys():
            #print(member['@party'])
            person['party'] = members['@party']
        if type(members['name']) is list:
            person['Complete'] = members['name'][0]['#text']
            person['first'] = members['name'][1]['#text'].split()[0]
            person['last'] = members['name'][2]['#text'].split()[0][:-1]
            person['fCap'] = person['first'].upper()
            if 'of' in members['name'][0]['#text'].split():
                person['lCap'] = members['name'][0]['#text'].split()[members['name'][0]['#text'].split().index('of') - 1]
            else:
                person['lCap'] = person['last'].upper()
        else:

            errorList.append('MemberStructureIssue')

            person['Complete'] = members['name']['#text']
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
        if '@party' in member.keys():
            #print(member['@party'])
            person['party'] = member['@party']
        if type(member['name']) is list:
            person['Complete'] = member['name'][0]['#text']
            person['first'] = member['name'][1]['#text'].split()[0]
            person['last'] = member['name'][2]['#text'].split()[0][:-1]
            person['fCap'] = person['first'].upper()
            if 'of' in member['name'][0]['#text'].split():
                person['lCap'] = member['name'][0]['#text'].split()[member['name'][0]['#text'].split().index('of') - 1]
            else:
                person['lCap'] = person['last'].upper()
        else:

            errorList.append('MemberStructureIssue')

            person['Complete'] = member['name']['#text']

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
    with open('/home/manjari/CongressionalHearingsProject/HardcodedNERV2/Data/members.meta', "r") as json_file:
        members = json.load(json_file)

    if congress in members.keys():
        for member in members[congress]:
            if last.casefold() == member['last_name'].casefold():
                return member
    
    return False

def featureExtractor(text):
    nela = NELAFeatureExtractor()
    try:
        feature_vector, feature_names = nela.extract_all(text)
    except:
        print("Handling Exception")

    return feature_vector, feature_names


#The actual parser
def parseFile(args):
    congress, session = args

    parsedText = ''

    path = '/mnt/fstore/data_chrg'
    errorList, metadata = getNames(parseXML(path +'/'+congress+'/'+session+'/mods.xml'), session)
    path = '/mnt/fstore/DataFiles/LabeledFiles_BERT1'
    unidentified = 0

    firstflag = True
    
    if not metadata:
        return (session, errorList)

    with open(path+'/'+congress+'/'+session+'/'+'Labeled'+session+'.lbd', 'r') as json_file:
        proceedings = json.load(json_file)

    conversations = []
    conversation = {
        'Question' : None,
        'Answer' : None
    }
    questionFlag = False

    for proceeding in proceedings:

        if firstflag:
            firstflag = False
            continue

        proceeding['feature_vector'], proceeding['feature_names'] = featureExtractor(proceeding['utterance'])

        lastName = proceeding['utterance'].split()[1][:-1]
        #print(lastName)
        memberList = getMemberByLastName(lastName,metadata)
        witnessList = getWitnessByLastName(lastName,metadata)
        member = getMoreMembers(lastName, congress)
        
        
        if witnessList:
            #print(witnessList[0]['Complete'])
            proceeding['role'] = 'witness'
            proceeding['speaker'] = witnessList[0]['Complete']

        elif memberList:
            #print(memberList[0]['Complete'])
            proceeding['role'] = 'member'
            if 'party' in proceeding.keys():
                proceeding['party'] = memberList[0]['party']
            else:
                if member:
                    proceeding['party'] = member['party']
            proceeding['speaker'] = memberList[0]['Complete']
        
        elif member:
            proceeding['role'] = 'member'
            proceeding['party'] = member['party']
            proceeding['speaker'] = member['first_name']+' '+member['last_name']+' of '+member['state']

        else:
            unidentified +=1
            proceeding['role'] = None
            proceeding['speaker'] = None

        if questionFlag and proceeding['label'] == 'Answers' and proceeding['role']=='witness':
            questionFlag = False
            conversation['Answer'] = proceeding
            conversations.append(conversation.copy())
            conversation = {
                'Question' : None,
                'Answer' : None
            }
        else:
            questionFlag = False
            conversation = {
                'Question' : None,
                'Answer' : None
            }

        if proceeding['label'] == 'Questions' and proceeding['role'] == 'member':
            questionFlag = True
            conversation['Question'] = proceeding
            

    
    print('Writing '+session)
    with open(path + '/' + congress + '/' + session + '/' + session + '.lbd', "w") as json_file:
        json.dump( proceedings, json_file, indent = 4, ensure_ascii = False)

    with open(path + '/' + congress + '/' + session + '/Convos' + session + '.cnv', "w") as json_file:
        json.dump( conversations, json_file, indent = 4, ensure_ascii = False)

    return (session, unidentified)

def driver():
    path = '/mnt/fstore/DataFiles/LabeledFiles_BERT1'

    if 'unidentified.err' in os.listdir(path):
        with open('/mnt/fstore/DataFiles/LabeledFiles_BERT1/unidentified.err', 'r') as json_file:
            errors = json.load(json_file)
    else:
        errors = {}
    #iterating for the congress sessions
    for congress in os.listdir(path):
        if congress.isdigit():
            args = []
            #debug
            print(congress)
            
            #iterating over the hearing sessions for each congress session
            for session in os.listdir(path+'/'+congress):
                # print(session)
                # if session+'.lbd' in os.listdir(path+'/'+congress+'/'+session):
                #     continue
                if 'Labeled'+session+'.lbd' in os.listdir(path+'/'+congress+'/'+session):
                    args.append((congress,session))

        with Pool(50) as pool:
            results = pool.map(parseFile,args)

        for result in results:
            if result:
                session, unidentified = result
                if congress not in errors.keys():
                    errors[congress] = []
                if unidentified:
                    errors[congress].append(session)

        errors[congress].sort()

    with open('/mnt/fstore/DataFiles/LabeledFiles_BERT1/unidentified.err', "w") as f:
        json.dump(errors,f,indent=4,sort_keys=True,ensure_ascii=False)

    return True

if __name__ == '__main__':
    driver()