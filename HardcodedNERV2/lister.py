import requests
import os
import json


def driver():
    members = {}
    congresses = ['104','105','106','107','108','109','110','111','112','113','114','115','116','117']
    chambers = ['house','senate']

    headers = {
        'X-API-Key' : 'B7O3XJ5RirCAXpDRDMDz2ziBW6wHAA9nMiTuhKA8'
    }

    for congress in congresses:
        for chamber in chambers:
            result = requests.get(url = f'https://api.propublica.org/congress/v1/{congress}/{chamber}/members.json', headers=headers)
            if congress not in members.keys():
                members[congress] = []
            members[congress].extend(result.json()['results'][0]['members'])

    with open(os.getcwd()+'/Data/members.meta', "a") as f:
        json.dump(members,f,indent=4,sort_keys=True,ensure_ascii=False)

if __name__ == '__main__':
    driver()