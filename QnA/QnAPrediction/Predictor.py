import numpy as np
import pandas as pd
import torch
import json
from sklearn.model_selection import KFold
from transformers import BertTokenizer
from torch import nn
from torch.utils.data import Dataset, DataLoader, TensorDataset,random_split,SubsetRandomSampler, ConcatDataset
from transformers import BertModel
from torch.optim import Adam
from tqdm import tqdm
from torchmetrics.classification import BinaryStatScores
from datetime import datetime
from collections import Counter
from torcheval.metrics import BinaryAUROC, BinaryAccuracy, BinaryF1Score, BinaryPrecision, BinaryRecall, BinaryConfusionMatrix
from pytz import timezone
tz = timezone('EST')
fmt = '%Y-%m-%d %H:%M:%S %Z%z'

from QuestionBERT_Trainer import predict, QuestionAnswer
# import QuestionBERT_Trainer as qt

class BertClassifier(nn.Module):

    def __init__(self, dropout=0.5):

        super(BertClassifier, self).__init__()
        self.bert = BertModel.from_pretrained('bert-base-cased')
        self.dropout = nn.Dropout(dropout)
        self.linear = nn.Linear(768, 2)
        self.relu = nn.ReLU()

    def forward(self, input_id, mask):

        _, pooled_output = self.bert(input_ids= input_id, attention_mask=mask,return_dict=False)
        dropout_output = self.dropout(pooled_output)
        linear_output = self.linear(dropout_output)
        final_layer = self.relu(linear_output)

        return final_layer

print('Reading Dataset')
df = pd.read_pickle('/mnt/fstore/DataFiles/PickledFiles/Data.pkl')
data = pd.DataFrame(df.Utterance)
data = data.rename(columns={'Utterance':'Texts'})
print(f'Dataset created at {datetime.now(tz).strftime(fmt)}')

predict_data = QuestionAnswer(data, hasLabels=False)
print(f'Dataset loaded at {datetime.now(tz).strftime(fmt)}')

model = BertClassifier()
print(f'New model created at {datetime.now(tz).strftime(fmt)}')
model.load_state_dict(torch.load('/mnt/fstore/DataFiles/Saved_Models/AMA_QABERT_ReLU2.pth'))
print(f'Model Loaded at {datetime.now(tz).strftime(fmt)}')

print('Beginning Prediction')
labels = predict(model, predict_data)
torch.save(labels,'/mnt/fstore/DataFiles/Saved_Datasets/QALabeling/AMA/PredictedLabels_1.pt')

cpu_labels = []
for label in tqdm(labels):
    cpu_labels.append(label.tolist()[0])

df['Predicted_labels2'] = cpu_labels
df['conversation_id'] = df['Hearing']+'_'+df['ID'].astype(str)
df = df.set_index(['conversation_id'])
# df.to_pickle('/mnt/fstore/DataFiles/PickledFiles/Data_predictedQA.pkl')

test_df = pd.read_pickle('/mnt/fstore/DataFiles/PickledFiles/HandLabeledQA.pkl')

print(len(test_df.loc[test_df['Labels'] == 'Questions']), len(test_df.loc[test_df['Labels'] == 'Answers']))

indices = list(test_df['ID'])
elements = ['CHRG-117shrg45040_66_0','CHRG-117shrg45040_66_1','CHRG-116hhrg37451_60_1','CHRG-116hhrg37451_40_1','CHRG-116hhrg37451_61_1','CHRG-116hhrg37451_62_1','CHRG-116hhrg37451_63_1']
for element in elements:
    indices.remove(element)

test_df = test_df.set_index(['ID'])
test_df = test_df.drop(index=elements)

y_true = []
y_pred = []
LABEL1 = 'Answers'     
LABEL2 = 'Questions' 
labels_dict = {LABEL1:0,LABEL2:1}
for index in indices:
    y_pred.append(df.loc[index,'Predicted_labels'])
    y_true.append(labels_dict[test_df.loc[index,'Labels']])

y_pred = torch.LongTensor(list(y_pred))
y_true = torch.LongTensor(list(y_true))

print(y_pred.size(),y_true.size())
metric = BinaryConfusionMatrix()
metric.update(y_pred, y_true)
print(f'Confusion Matrix: {metric.compute()}')
metric = BinaryAccuracy()
metric.update(y_pred,y_true)
print(f'Accuracy: {metric.compute()}')
metric = BinaryAUROC()
metric.update(y_pred,y_true)
print(f'AUCROC: {metric.compute()}')
metric = BinaryF1Score()
metric.update(y_pred,y_true)
print(f'F1 Score: {metric.compute()}')
metric = BinaryPrecision()
metric.update(y_pred,y_true)
print(f'Precision: {metric.compute()}')
metric = BinaryRecall()
metric.update(y_pred,y_true)
print(f'Recall: {metric.compute()}')