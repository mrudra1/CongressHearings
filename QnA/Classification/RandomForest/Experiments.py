import os
import json
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.dummy import DummyClassifier
from sklearn.model_selection import GridSearchCV
from tqdm import tqdm

#Loading the Dataset
# A_df = pd.read_pickle('/mnt/fstore/DataFiles/PickledFiles/Answers.pkl')
# Q_df = pd.read_pickle('/mnt/fstore/DataFiles/PickledFiles/Questions.pkl')
# A_df = pd.read_pickle('/mnt/fstore/DataFiles/PickledFiles/AnswersWithConvFeatures.pkl')
# Q_df = pd.read_pickle('/mnt/fstore/DataFiles/PickledFiles/QuestionsWithConvFeatures.pkl')
# A_df.dropna(subset=['RhetoricalRole'], inplace=True)
# Q_df.dropna(subset=['RhetoricalRole'], inplace=True)
# A_df.drop(A_df.loc[A_df['RhetoricalRole']==-1].index, inplace=True)
# Q_df.drop(Q_df.loc[Q_df['RhetoricalRole']==-1].index, inplace=True)
df = pd.read_pickle('/mnt/fstore/DataFiles/PickledFiles/Data_MARK2_withFeatures.pkl')
Q_df = df.loc[df['is_question'] == True]
A_df = df.loc[df['is_answer'] == True]
A_df = A_df.dropna()
A_df['Majority'] = A_df['Majority'].replace([True, False],[1,0])
Q_df['Majority'] = Q_df['Majority'].replace([True, False],[1,0])

#Some Relevant Data
feature_names = [
                "ttr",
                "avg_wordlen",
                "word_count",
                "flesch_kincaid_grade_level",
                "smog_index",
                "coleman_liau_index",
                "lix",
                "bias_words",
                "assertatives",
                "factives",
                "hedges",
                "implicatives",
                "report_verbs",
                "positive_opinion_words",
                "negative_opinion_words",
                "vadneg",
                "vadneu",
                "vadpos",
                "wneg",
                "wpos",
                "wneu",
                "sneg",
                "spos",
                "sneu",
                # 'RR_-1',
                # 'RR_0',
                # 'RR_1',
                # 'RR_2',
                # 'RR_3',
                # 'RR_4',
                # 'RR_5',
                # 'RR_6',
                # 'RR_7'
            ]

#Datastructures
sessions = ['108','109','110','111','112','113','114','115','116','117']
commmittees = A_df['Committee'].unique()
A_party_scores_dict = { 'All' : []}
A_majority_scores_dict = { 'All' : []}
Q_party_scores_dict = { 'All' : []}
Q_majority_scores_dict = {'All' : []}
# gov_A_party_scores_dict = {'All' : []}
# gov_A_majority_scores_dict = {'All' : []}
# gov_Q_party_scores_dict = {'All' : []}
# gov_Q_majority_scores_dict = {'All' : []} 

params = {
    # 'n_estimators' : [int(x) for x in np.linspace(10, 100, num = 10)],
    # 'criterion':('gini', 'entropy'), 
    'max_depth':[int(x) for x in np.linspace(50, 500, num = 10)],
    # 'min_samples_split' : [0.0001, 0.001, 0.005, 0.01, 0.05, 0.1, 0.2, 0.5]
    'min_samples_split' : [0.01, 0.1, 0.2, 0.5]
}

#Grid Search
def search_grid(X,y, params, clf):
    # dummy_clf = DummyClassifier(strategy="most_frequent")
    # dummy_clf.fit(X, y)
    # print('Dummy Clssifier:', dummy_clf.score(X, y))
    gs1 = GridSearchCV(estimator=clf, param_grid= params, cv= 5, return_train_score=True)
    gs1.fit(X,y)                             
    return pd.DataFrame(gs1.cv_results_), gs1.best_score_

def searchAndWrite(X, y, params, answer, party, committee, congress, clf = RandomForestClassifier(n_jobs=50)):
    #Gridsearching
    resdf, bestScore = search_grid(X, y, params=params, clf = clf)

    #Writing Result
    if answer and party:
        A_party_scores_dict[committee].append(bestScore)
        fileName = 'Answers/Party/'
    elif answer and not party:
        A_majority_scores_dict[committee].append(bestScore)
        fileName = 'Answers/Majority/'
    elif not answer and party:
        Q_party_scores_dict[committee].append(bestScore)
        fileName = 'Questions/Party/'
    else:
        Q_majority_scores_dict[committee].append(bestScore)
        fileName = 'Questions/Majority/'
    
    resdf.to_pickle('/mnt/fstore/DataFiles/PickledFiles/GridSearches/NELA/'+ fileName + congress+'/'+committee+'.pkl')

#Classification by Dataset

#Whole Dataset

#Preparing the Data
A_X = A_df[feature_names]
A_y1 = A_df['Party']
A_y2 = A_df['Majority']

Q_X = Q_df[feature_names]
Q_y1 = Q_df['Party']
Q_y2 = Q_df['Majority']

#Grid Searching
searchAndWrite(A_X, A_y1, params=params, answer=True, party=True, committee='All', congress = 'All')
searchAndWrite(A_X, A_y2, params=params, answer=True, party=False, committee='All', congress = 'All')
searchAndWrite(Q_X, Q_y1, params=params, answer=False, party=True, committee='All', congress = 'All')
searchAndWrite(Q_X, Q_y2, params=params, answer=False, party=False, committee='All', congress = 'All')

#Classification by Session
for congress in sessions:
    print(congress)
    os.mkdir('/mnt/fstore/DataFiles/PickledFiles/GridSearches/NELA/Answers/Party/'+congress)
    os.mkdir('/mnt/fstore/DataFiles/PickledFiles/GridSearches/NELA/Answers/Majority/'+congress)
    os.mkdir('/mnt/fstore/DataFiles/PickledFiles/GridSearches/NELA/Questions/Party/'+congress)
    os.mkdir('/mnt/fstore/DataFiles/PickledFiles/GridSearches/NELA/Questions/Majority/'+congress)

    #Prepping Data 
    A_X = A_df[A_df['Congress'] == congress][feature_names]
    A_y1 = A_df[A_df['Congress'] == congress]['Party']
    A_y2 = A_df[A_df['Congress'] == congress]['Majority']

    Q_X = Q_df[Q_df['Congress'] == congress][feature_names]
    Q_y1 = Q_df[Q_df['Congress'] == congress]['Party']
    Q_y2 = Q_df[Q_df['Congress'] == congress]['Majority']

    #Grid Searching
    #searchAndWrite(A_X, A_y1, answer=True, party=True, params=params, committee='All', congress = congress)
    try:
        searchAndWrite(A_X, A_y2, answer=True, party=False, params=params, committee='All', congress = congress)
    except Exception as error:
        print(error)
    searchAndWrite(Q_X, Q_y1, answer=False, party=True, params=params, committee='All', congress = congress)
    searchAndWrite(Q_X, Q_y2, answer=False, party=False, params=params, committee='All', congress = congress)

#Classification by Committee
for committee in commmittees:

    print(committee)
    A_party_scores_dict[committee] = []
    A_majority_scores_dict[committee] = []
    Q_party_scores_dict[committee] = []
    Q_majority_scores_dict[committee] = []

    #Prepping Data
    A_X = A_df[A_df['Committee'] == committee][feature_names]
    A_y1 = A_df[A_df['Committee'] == committee]['Party']
    A_y2 = A_df[A_df['Committee'] == committee]['Majority']

    Q_X = Q_df[Q_df['Committee'] == committee][feature_names]
    Q_y1 = Q_df[Q_df['Committee'] == committee]['Party']
    Q_y2 = Q_df[Q_df['Committee'] == committee]['Majority']

    #Grid Searching
    if len(A_X) > 10:
        searchAndWrite(A_X, A_y1, params=params, answer=True, party=True, committee= committee, congress = 'All')
        searchAndWrite(A_X, A_y2, params=params, answer=True, party=False, committee= committee, congress = 'All')
    if len(Q_X) > 10:
        searchAndWrite(Q_X, Q_y1, params=params, answer=False, party=True, committee= committee, congress = 'All')
        searchAndWrite(Q_X, Q_y2, params=params, answer=False, party=False, committee= committee, congress = 'All')

#Classification by Session and Committee
for congress in sessions:
    print(congress)
    for committee in commmittees:
        print(committee)
        
        if committee not in A_df[A_df['Congress']==congress]['Committee'].unique():
            A_party_scores_dict[committee].append(None)
            A_majority_scores_dict[committee].append(None)
            Q_majority_scores_dict[committee].append(None)
            Q_party_scores_dict[committee].append(None)
            continue

        A_X = A_df[(A_df['Congress'] == congress) & (A_df['Committee'] == committee)][feature_names]
        A_y1 = A_df[(A_df['Congress'] == congress) & (A_df['Committee'] == committee)]['Party']
        A_y2 = A_df[(A_df['Congress'] == congress) & (A_df['Committee'] == committee)]['Majority']

        Q_X = Q_df[(Q_df['Congress'] == congress) & (Q_df['Committee'] == committee)][feature_names]
        Q_y1 = Q_df[(Q_df['Congress'] == congress) & (Q_df['Committee'] == committee)]['Party']
        Q_y2 = Q_df[(Q_df['Congress'] == congress) & (Q_df['Committee'] == committee)]['Majority']

        #Grid Searching
        if len(A_X) > 10:
            searchAndWrite(A_X, A_y1, params=params, answer=True, party=True, committee= committee, congress = congress)
            searchAndWrite(A_X, A_y2, params=params, answer=True, party=False, committee= committee, congress = congress)
        if len(Q_X) > 10:
            searchAndWrite(Q_X, Q_y1, params=params, answer=False, party=True, committee= committee, congress = congress)
            searchAndWrite(Q_X, Q_y2, params=params, answer=False, party=False, committee= committee, congress = congress)

pd.DataFrame(A_party_scores_dict).to_pickle('/mnt/fstore/DataFiles/PickledFiles/GridSearches/NELA/Answers/party_scores.pkl')
pd.DataFrame(A_majority_scores_dict).to_pickle('/mnt/fstore/DataFiles/PickledFiles/GridSearches/NELA/Answers/majority_scores.pkl')
pd.DataFrame(Q_party_scores_dict).to_pickle('/mnt/fstore/DataFiles/PickledFiles/GridSearches/NELA/Questions/party_scores.pkl')
pd.DataFrame(Q_majority_scores_dict).to_pickle('/mnt/fstore/DataFiles/PickledFiles/GridSearches/NELA/Questions/majority_scores.pkl')