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
from datetime import datetime
from collections import Counter
from utils import write_and_print
from torcheval.metrics import BinaryAUROC, BinaryAccuracy, BinaryF1Score, BinaryPrecision, BinaryRecall, BinaryConfusionMatrix
from pytz import timezone
tz = timezone('EST')
fmt = '%Y-%m-%d %H:%M:%S %Z%z'

# TODO: Make changes here to switch the code between tasks quickly
AMA_PATH = '/mnt/fstore/DataFiles/PickledFiles/AMA.pkl'
UKP_PATH = '/mnt/fstore/DataFiles/PickledFiles/UK_Parliamentary.pkl'
# CON_PATH = '/mnt/fstore/DataFiles/PickledFiles/HandLabeledQA.pkl'
LOAD_MODEL = False
LOAD_MODEL_PATH = '/mnt/fstore/DataFiles/Saved_Models/AM_UKPA_QABERT_ReLU.pth'      # This value is required only if the LOAD_MODEL value is True, example: '/mnt/fstore/DataFiles/Saved_Models/AnswerPartyBERT5.pth'
LOAD_TRAINSET_PATH = '/mnt/fstore/DataFiles/Saved_Datasets/QALabeling/AMA_UKP/trainSet_1.pt'
LOAD_TESTSET_PATH = '/mnt/fstore/DataFiles/Saved_Datasets/QALabeling/AMA_UKP/testSet_1.pt'
EPOCH_OFFSET = 1
SAVE_MODEL_PATH = '/mnt/fstore/DataFiles/Saved_Models/AMA_UKP_QABERT_ReLU'
LOG_PATH = '/mnt/fstore/DataFiles/Logs/' + 'AMA_UKP_QABERT_ReLU' + '.log' 

LABEL = 'Labels'
INPUT = 'Texts'          
LABEL1 = 'Answers'     
LABEL2 = 'Questions'        
LABEL1_VALUE = 'Answer'   
LABEL2_VALUE = 'Question' 
# COLUMN_FILTER = 'is_answer' # Alternate options: 'is_question'  'is_answer'
CROSS_VALIDATION = False
TRAIN = True
TEST = True
SPLIT_LENGTHS = [0.9,0.1]

# TODO: Hyperparameter Configurations
LR = 1e-5
EPOCHS = 1
BATCH_SIZE = 2
NFOLDS = 5

#DATASET CLASS
tokenizer = BertTokenizer.from_pretrained('bert-base-cased')
labels_dict = {LABEL1:0,LABEL2:1}

class QuestionAnswer(Dataset):

    def __init__(self, df, hasLabels = True):

        self.hasLabels = False

        if hasLabels:
            self.hasLabels = True
            self.labels = [labels_dict[label] for label in df[LABEL]]
        
        self.texts = [tokenizer(str(text), padding='max_length', max_length = 512, truncation=True, return_tensors="pt") for text in df[INPUT]]     

    def classes(self):
        return self.labels

    def __len__(self):
        return len(self.texts)
    
    def get_batch_labels(self, idx):
        # Fetch a batch of labels
        return np.array(self.labels[idx])

    def get_batch_texts(self, idx):
        # Fetch a batch of inputs
        return self.texts[idx]

    def __getitem__(self, idx):
        if self.hasLabels:
            batch_texts = self.get_batch_texts(idx)
            batch_y = self.get_batch_labels(idx)
            return batch_texts, batch_y
        else:
            batch_texts = self.get_batch_texts(idx)
            return batch_texts
    
#MODEL CLASS
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
    
#TRAINING
def trainer(model, dataloader, criterion, optimizer, epoch):
    total_acc_train = 0
    total_loss_train = 0

    for train_input, train_label in tqdm(dataloader, desc=f'Training epoch {epoch} model'):

        train_label = train_label.to(device)
        mask = train_input['attention_mask'].to(device)
        input_id = train_input['input_ids'].squeeze(1).to(device)

        output = model(input_id, mask)
        
        batch_loss = criterion(output, train_label.long())
        total_loss_train += batch_loss.item()
        
        acc = (output.argmax(dim=1) == train_label).sum().item()
        total_acc_train += acc

        model.zero_grad()
        batch_loss.backward()
        optimizer.step()

    return total_acc_train, total_loss_train

def validator( model, dataloader, criterion, optimizer):
    total_acc_val = 0
    total_loss_val = 0

    with torch.no_grad():

        for val_input, val_label in dataloader:

            val_label = val_label.to(device)
            mask = val_input['attention_mask'].to(device)
            input_id = val_input['input_ids'].squeeze(1).to(device)

            output = model(input_id, mask)

            batch_loss = criterion(output, val_label.long())
            total_loss_val += batch_loss.item()
            
            acc = (output.argmax(dim=1) == val_label).sum().item()
            total_acc_val += acc

    return total_acc_val, total_loss_val

def train(train, learning_rate, epochs, batch_size, folds):

    criterion = nn.CrossEntropyLoss()

    train_classes = [label for _, label in train]
    count = Counter(i.item() for i in train_classes)
    write_and_print(f'Total number of samples in train subset: {len(train)}\
      \nNumber of {LABEL1_VALUE} samples: {count[0]}, {count[0]/len(train_classes)*100: .3f}%\
      \nNumber of {LABEL2_VALUE} samples: {count[1]}, {count[1]/len(train_classes)*100: .3f}%\n', LOG_PATH)
    
    if not CROSS_VALIDATION:
        model = BertClassifier()
        if LOAD_MODEL:
            write_and_print('The model is being loaded from a previously saved checkpoint', LOG_PATH)
            model.load_state_dict(torch.load(LOAD_MODEL_PATH))
        else:
            write_and_print('Starting with a fresh model', LOG_PATH)
        optimizer = Adam(model.parameters(), lr= learning_rate)

        if use_cuda:
            model = model.cuda()
            criterion = criterion.cuda()
        train_dataloader = DataLoader(train_data, batch_size= batch_size)
        for epoch_num in range(epochs):
            write_and_print(f'------------------------------------------------------------------------------\
            \nStarting Epoch {epoch_num+EPOCH_OFFSET} at: {datetime.now(tz).strftime(fmt)}\n', LOG_PATH)
            total_acc_train, total_loss_train = trainer(model, train_dataloader, criterion, optimizer, epoch_num+EPOCH_OFFSET)
            write_and_print(
                    f'Epoch {epoch_num + EPOCH_OFFSET} Result: | Train Loss: {total_loss_train / len(train_dataloader.sampler): .3f} \
                    | Train Accuracy: {total_acc_train / len(train_dataloader.sampler): .3f}', LOG_PATH)
            torch.save(model.state_dict(), SAVE_MODEL_PATH + str(epoch_num+EPOCH_OFFSET) +'.pth')
        return model

    else:
        
        splits=KFold(n_splits=folds,shuffle=True,random_state=42)
        for fold, (train_idx,val_idx) in enumerate(splits.split(np.arange(len(train)))):
            model = BertClassifier()
            optimizer = Adam(model.parameters(), lr= learning_rate)
            write_and_print('Starting with a fresh model', LOG_PATH)
            write_and_print(f'\n----------------------------\nFold{fold + 1}\n----------------------------', LOG_PATH)
            train_sampler = SubsetRandomSampler(train_idx)
            test_sampler = SubsetRandomSampler(val_idx)
            train_dataloader = DataLoader(train, batch_size=batch_size, sampler=train_sampler)
            val_dataloader = DataLoader(train, batch_size=batch_size, sampler=test_sampler)

            if use_cuda:
                model = model.cuda()
                criterion = criterion.cuda()

            for epoch_num in range(epochs):
                write_and_print(f'\nStarting Epoch {epoch_num+1} at: {datetime.now(tz).strftime(fmt)}\n', LOG_PATH) 
                total_acc_train, total_loss_train = trainer(model, train_dataloader, criterion, optimizer, epoch_num)
                total_acc_val, total_loss_val = validator(model, val_dataloader, criterion, optimizer)
                            
                write_and_print(
                    f'Epochs {epoch_num + EPOCH_OFFSET} result: Train Loss: {total_loss_train / len(train_dataloader.sampler): .3f} \
                    | Train Accuracy: {total_acc_train / len(train_dataloader.sampler): .3f} \
                    | Val Loss: {total_loss_val / len(val_dataloader.sampler): .3f} \
                    | Val Accuracy: {total_acc_val / len(val_dataloader.sampler): .3f}', LOG_PATH)


def predict(model, predict):

    predict_dataloader = DataLoader(predict)

    use_cuda = torch.cuda.is_available()
    device = torch.device("cuda" if use_cuda else "cpu")

    if use_cuda:
        model = model.cuda()

    Labels = []
    with torch.no_grad():
        for predict_input, _ in tqdm(predict_dataloader, desc=f'Predicting ... '):

            mask = predict_input['attention_mask'].to(device)
            input_id = predict_input['input_ids'].squeeze(1).to(device)

            output = model(input_id, mask)

            Labels.append(output.argmax(dim=1))

    return Labels

def copmute_test_error(model, test_df):

    y_pred = torch.tensor(predict(model, test_df))
    y_true = []
    for x, y in test_data:
        y_true.append(y)
    y_true = torch.tensor(np.array(y_true))
    y_pred = y_pred.to(device)
    y_true = y_true.to(device)

    print(y_pred.size(),y_true.size())
    metric = BinaryConfusionMatrix()
    metric.update(y_pred, y_true)
    write_and_print(f'Confusion Matrix: {metric.compute()}', LOG_PATH)
    metric = BinaryAccuracy()
    metric.update(y_pred,y_true)
    write_and_print(f'Accuracy: {metric.compute()}', LOG_PATH)
    metric = BinaryAUROC()
    metric.update(y_pred,y_true)
    write_and_print(f'AUCROC: {metric.compute()}', LOG_PATH)
    metric = BinaryF1Score()
    metric.update(y_pred,y_true)
    write_and_print(f'F1 Score: {metric.compute()}', LOG_PATH)
    metric = BinaryPrecision()
    metric.update(y_pred,y_true)
    write_and_print(f'Precision: {metric.compute()}', LOG_PATH)
    metric = BinaryRecall()
    metric.update(y_pred,y_true)
    write_and_print(f'Recall: {metric.compute()}', LOG_PATH)

#Create the Dataset instance
if __name__ == '__main__':
    #Write preliminary info to log
    write_and_print(f'-----------------------------------------------------------------\
                    \n Beginning run at {datetime.now(tz).strftime(fmt)} with:\
                    \n Learning Rate = {LR}\
                    \n Number of Epochs = {EPOCHS}\
                    \n Epoch offset = {EPOCH_OFFSET}\
                    \n------------------------------------------------------------------\n', LOG_PATH)

    #Get cpu or gpu device for training.
    use_cuda = torch.cuda.is_available()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    write_and_print(f"Using {device} device", LOG_PATH) 

    if CROSS_VALIDATION:
        ama_df = pd.read_pickle(AMA_PATH)
        ukp_df = pd.read_pickle(UKP_PATH)
        # test_df = pd.read_pickle(CON_PATH)
        write_and_print('\n\nCreating the Dataset', LOG_PATH)
        #Creating the Dataset
        train_data1 = QuestionAnswer(ama_df)
        train_data2 = QuestionAnswer(ukp_df)
        #Concatenating the two datasets
        train_data = ConcatDataset([train_data1,train_data2])
        #Creating a train/test split
        train_data, test_data = random_split(dataset=train_data, lengths=SPLIT_LENGTHS)
        #Saving the train/test splits to disk
        torch.save(train_data, LOAD_TRAINSET_PATH)
        torch.save(test_data, LOAD_TESTSET_PATH)
    else:
        write_and_print('\n\nLoading the Dataset', LOG_PATH)
        train_data = torch.load(LOAD_TRAINSET_PATH)
        test_data = torch.load(LOAD_TESTSET_PATH)

    if TRAIN:
        write_and_print(f'\n\nBeginning the training at: {datetime.now(tz).strftime(fmt)}', LOG_PATH)
        model = train(train_data, learning_rate= LR, epochs= EPOCHS, batch_size=BATCH_SIZE, folds=NFOLDS)

    if TEST:
        if not TRAIN:
            model = BertClassifier()
            write_and_print('The model is being loaded from a previously saved checkpoint', LOG_PATH)
            model.load_state_dict(torch.load(LOAD_MODEL_PATH))
        write_and_print(f'\n\nBeginning Testing at: {datetime.now(tz).strftime(fmt)}', LOG_PATH)
        copmute_test_error(model, test_data)