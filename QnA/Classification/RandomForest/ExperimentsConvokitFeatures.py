import os
import json
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.dummy import DummyClassifier
from sklearn.model_selection import GridSearchCV
from tqdm import tqdm

#Loading the Dataset
A_df = pd.read_pickle('/mnt/fstore/DataFiles/PickledFiles/AnswersWithConvFeatures.pkl')
Q_df = pd.read_pickle('/mnt/fstore/DataFiles/PickledFiles/QuestionsWithConvFeatures.pkl')

#Some Relevant Data
feature_names = 'meta.prompt_types__prompt_type__8'

#Datastructures
sessions = ['108','109','110','111','112','113','114','115','116','117']
commmittees = A_df['Committee'].unique()
A_party_scores_dict = { 'All' : []}
A_majority_scores_dict = { 'All' : []}
Q_party_scores_dict = { 'All' : []}
Q_majority_scores_dict = { 'All' : []}


params = {
    'n_estimators' : [int(x) for x in np.linspace(10, 100, num = 10)],
    'criterion':('gini', 'entropy'), 
    'max_depth':[int(x) for x in np.linspace(10, 500, num = 246)],
    'min_samples_split' : [0.0001, 0.001, 0.005, 0.01, 0.05, 0.1, 0.2, 0.5]
}

#Grid Search
def search_grid(X,y, params, clf):
    gs1 = GridSearchCV(estimator=clf, param_grid= params, n_jobs=100, cv= 5, return_train_score=True)
    gs1.fit(X,y)
    return pd.DataFrame(gs1.cv_results_), gs1.best_score_

def searchAndWrite(X, y, params, party, committee, congress, clf = RandomForestClassifier()):
    #Gridsearching
    resdf, bestScore = search_grid(X, y, params=params, clf = clf)

    #Writing Result
    if party:
        A_party_scores_dict[committee].append(bestScore)
        fileName = 'Answers/Party/'
    else:
        A_majority_scores_dict[committee].append(bestScore)
        fileName = 'Answers/Majority/'
    
    resdf.to_pickle('/mnt/fstore/DataFiles/PickledFiles/GridsearchResults/'+ fileName + congress+'/'+committee+'.pkl')

#Classification by Committee
for committee in commmittees:

    print(committee)
    A_party_scores_dict[committee] = []
    A_majority_scores_dict[committee] = []

    #Prepping Data
    A_X = A_df[A_df['Committee'] == committee][feature_names]
    A_y1 = A_df[A_df['Committee'] == committee]['Party']
    A_y2 = A_df[A_df['Committee'] == committee]['Majority']

    #Grid Searching
    if len(A_X) > 10:
        searchAndWrite(A_X, A_y1, params=params, answer=True, party=True, committee= committee, congress = 'All')
        searchAndWrite(A_X, A_y2, params=params, answer=True, party=False, committee= committee, congress = 'All')

#Classification by Session and Committee
for congress in sessions:
    print(congress)
    for committee in commmittees:
        print(committee)
        
        if committee not in A_df[A_df['Congress']==congress]['Committee'].unique():
            A_party_scores_dict[committee].append(None)
            A_majority_scores_dict[committee].append(None)
            continue

        A_X = A_df[(A_df['Congress'] == congress) & (A_df['Committee'] == committee)][feature_names]
        A_y1 = A_df[(A_df['Congress'] == congress) & (A_df['Committee'] == committee)]['Party']
        A_y2 = A_df[(A_df['Congress'] == congress) & (A_df['Committee'] == committee)]['Majority']

        #Grid Searching
        if len(A_X) > 10:
            searchAndWrite(A_X, A_y1, params=params, answer=True, party=True, committee= committee, congress = congress)
            searchAndWrite(A_X, A_y2, params=params, answer=True, party=False, committee= committee, congress = congress)

pd.DataFrame(A_party_scores_dict).to_pickle('/mnt/fstore/DataFiles/PickledFiles/GridsearchResults/Answers/party_scores.pkl')
pd.DataFrame(A_majority_scores_dict).to_pickle('/mnt/fstore/DataFiles/PickledFiles/GridsearchResults/Answers/majority_scores.pkl')
pd.DataFrame(Q_party_scores_dict).to_pickle('/mnt/fstore/DataFiles/PickledFiles/GridsearchResults/Questions/party_scores.pkl')
pd.DataFrame(Q_majority_scores_dict).to_pickle('/mnt/fstore/DataFiles/PickledFiles/GridsearchResults/Questions/majority_scores.pkl')