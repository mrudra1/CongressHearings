#imports
import os
import json
import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import KFold
from transformers import BertTokenizer
from torch import nn
from torch.utils.data import Dataset, DataLoader, TensorDataset,random_split,SubsetRandomSampler, ConcatDataset
from transformers import BertModel
from torch.optim import Adam
from tqdm import tqdm
from torchmetrics.classification import BinaryStatScores

#switchign to CUDA
# Get cpu or gpu device for training.
use_cuda = torch.cuda.is_available()
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using {device} device")

#DATSET CLASS

tokenizer = BertTokenizer.from_pretrained('bert-base-cased')
labels_dict = {'Answers':0,
          'Questions':1}

class Dataset(Dataset):

    def __init__(self, df, isPredict = False, has_ID = False):

        if isPredict:
            self.labels = [int(label) for label in df['Labels']]
        else:
            self.labels = [labels_dict[label] for label in df['Labels']]
        
        self.has_ID = has_ID
        self.texts = [tokenizer(str(text), padding='max_length', max_length = 512, truncation=True, return_tensors="pt") for text in df['Texts']]
        if has_ID:
            self.IDs = df['ID']

    def classes(self):
        return self.labels

    def __len__(self):
        return len(self.labels)

    def get_batch_labels(self, idx):
        # Fetch a batch of labels
        return np.array(self.labels[idx])

    def get_batch_texts(self, idx):
        # Fetch a batch of inputs
        return self.texts[idx]
    
    def get_batch_IDs(self, idx):
        #Fetch a batch of IDs
        return self.IDs[idx]

    def __getitem__(self, idx):
        
        batch_texts = self.get_batch_texts(idx)
        batch_y = self.get_batch_labels(idx)
        batch_IDs = self.get_batch_IDs(idx)

        return batch_texts, batch_y, batch_IDs
    
#MODEL CLASS
class BertClassifier(nn.Module):

    def __init__(self, dropout=0.5):

        super(BertClassifier, self).__init__()

        self.bert = BertModel.from_pretrained('bert-base-cased')
        self.dropout = nn.Dropout(dropout)
        self.linear = nn.Linear(768, 5)
        self.relu = nn.ReLU()

    def forward(self, input_id, mask):

        _, pooled_output = self.bert(input_ids= input_id, attention_mask=mask,return_dict=False)
        dropout_output = self.dropout(pooled_output)
        linear_output = self.linear(dropout_output)
        final_layer = self.relu(linear_output)

        return final_layer
    
#LOADING THE MODEL

model = BertClassifier()
model.load_state_dict(torch.load('/mnt/fstore/DataFiles/QnA/Models/BERT1.pth'))
model.eval()

##Prediction

def predict(model, predict_data):

    predict = Dataset(predict_data, isPredict=True)

    predict_dataloader = DataLoader(predict, batch_size=1)

    use_cuda = torch.cuda.is_available()
    device = torch.device("cuda" if use_cuda else "cpu")

    if use_cuda:

        model = model.cuda()

    Labels = []
    IDs = []
    total_acc_test = 0
    with torch.no_grad():
        for predict_input, predict_label in predict_dataloader:

            predict_label = predict_label.to(device)
            mask = predict_input['attention_mask'].to(device)
            input_id = predict_input['input_ids'].squeeze(1).to(device)

            output = model(input_id, mask)

            Labels.append(output.argmax(dim=1))
            IDs.append(predict_label)

    return Labels,IDs

#Predicting the unlabled congressional data

path = '/mnt/fstore/DataFiles/Split'
path1 = '/mnt/fstore/DataFiles/LabeledFiles_BERT1'
dict_label = {
    0:'Answers',
    1:'Questions'
}
for congress in os.listdir(path):
    print(congress)
    for session in os.listdir(path+'/'+congress):
        print(session)
        texts = []
        IDs = []
        data = {}
        with open(path+'/'+congress+'/'+session+'/'+'Split'+session+'.split', 'r') as json_file:
            data = json.load(json_file)
        for proceeding in data:
            if proceeding['label']:
                continue
            text = ''
            text = proceeding['utterance']
            texts.append(text)
            IDs.append(str(proceeding['ID']))
        predict_df = pd.DataFrame({'Texts': texts, 'Labels':IDs})
        Labels, IDs = predict(model, predict_df)

        for i in range(len(IDs)):
            if i>=len(Labels):
                print('IDs',len(IDs),'Labels',len(Labels))
            if len(dict_label) <= int(Labels[i]):
                print(len(dict_label),Labels)

            try:
                data[IDs[i]]['label'] = dict_label[int(Labels[i])]
            except:
                with open(os.getcwd()+'Errors.er', 'r') as json_file:
                    errors = json.load(json_file)
                errors.append(session)
                with open(os.getcwd()+'Errors.er', "w") as json_file:
                    json.dump( errors, json_file, indent = 4, ensure_ascii = False)


        with open(path1+'/'+congress+'/'+session+'/'+'Labeled'+session+'.lbd', "w") as json_file:
            json.dump( data, json_file, indent = 4, ensure_ascii = False)
