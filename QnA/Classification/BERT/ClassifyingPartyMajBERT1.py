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
import datetime
from collections import Counter
from utils import write_and_print

# TODO: Make changes here to switch the code between tasks quickly
DF_PATH = '/mnt/fstore/DataFiles/PickledFiles/Data_MARK2_Formatted4BERT.pkl'
LOAD_MODEL = False
LOAD_MODEL_PATH = '/mnt/fstore/DataFiles/Saved_Models/ParQBERT_MARK2_1.pth'      # This value is required only if the LOAD_MODEL value is True, example: '/mnt/fstore/DataFiles/Saved_Models/AnswerPartyBERT5.pth'
LOAD_TRAINSET_PATH = '/mnt/fstore/DataFiles/Saved_Datasets/PartyMajorityClassification/Party/Answer/trainSet.pt'
LOAD_VALSET_PATH = '/mnt/fstore/DataFiles/Saved_Datasets/PartyMajorityClassification/Party/Answer/valSet.pt'
LOAD_TESTSET_PATH = '//mnt/fstore/DataFiles/Saved_Datasets/PartyMajorityClassification/Party/Answer/testSet.pt'
EPOCH_OFFSET = 1
SAVE_MODEL_PATH = '/mnt/fstore/DataFiles/Saved_Models/ParABERT_MARK2_'
LOG_PATH = '/mnt/fstore/DataFiles/Logs/' + 'ParABERT_MARK2' + '.log'
LOAD_DATASETS = True

LABEL = 'Party'          # Alternate options: 'Party' 'Majority'
LABEL1 = 'R'             # Alternate options: 'R' True
LABEL2 = 'D'            # Alternate options: 'D' False
LABEL1_VALUE = 'Republican'   # Alternate options: 'Republican' 'Majority'
LABEL2_VALUE = 'Democrat'   # Alternate options: 'Minority'  'Democrat'
COLUMN_FILTER = 'is_answer' # Alternate options: 'is_question'  'is_answer'
CROSS_VALIDATION = False
TRAIN = True
TEST = False
SPLIT_LENGTHS = [0.2, 0.05, 0.75]

# TODO: Hyperparameter Configurations
LR = 1e-5
EPOCHS = 10
BATCH_SIZE = 2
NFOLDS = 5

#Get cpu or gpu device for training.
use_cuda = torch.cuda.is_available()
device = "cuda" if torch.cuda.is_available() else "cpu"
write_and_print(f"Using {device} device", LOG_PATH)


train_df = pd.read_pickle(DF_PATH)
train_df = train_df.loc[((train_df[LABEL] == LABEL1)|(train_df[LABEL] == LABEL2))&(train_df[COLUMN_FILTER] == True),['text_without_stopwords',LABEL]]
L1 = len(train_df.loc[train_df[LABEL]==LABEL1])
L2 = len(train_df.loc[train_df[LABEL]==LABEL2])
write_and_print(
    f'\nTotal number of utterances: {len(train_df)}\
    \nTotal number of {LABEL1_VALUE} utterances: {L1}, {L1/len(train_df): .2f}%\
    \nTotal number of {LABEL2_VALUE} utterances: {L2}, {L2/len(train_df): .2f}%\n\n\n', LOG_PATH
)

#DATASET CLASS
tokenizer = BertTokenizer.from_pretrained('bert-base-cased')
labels_dict = {LABEL1:-1,LABEL2:1}

class CongressHearings(Dataset):

    def __init__(self, df, isPredict = False):

        if isPredict:
            self.labels = [int(label) for label in df[LABEL]]
        else:
            self.labels = [labels_dict[label] for label in df[LABEL]]
        
        self.texts = [tokenizer(str(text), padding='max_length', max_length = 512, truncation=True, return_tensors="pt") for text in df['text_without_stopwords']]
        

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

    def __getitem__(self, idx):
        batch_texts = self.get_batch_texts(idx)
        batch_y = self.get_batch_labels(idx)
        return batch_texts, batch_y
    
#MODEL CLASS
class BertClassifier(nn.Module):

    def __init__(self, dropout=0.5):

        super(BertClassifier, self).__init__()

        self.bert = BertModel.from_pretrained('bert-base-cased')
        self.dropout = nn.Dropout(dropout)
        self.linear = nn.Linear(768, 2)
        # self.softmax = nn.Softmax(dim=1)
        self.relu = nn.LeakyReLU()

    def forward(self, input_id, mask):

        _, pooled_output = self.bert(input_ids= input_id, attention_mask=mask,return_dict=False)
        dropout_output = self.dropout(pooled_output)
        linear_output = self.linear(dropout_output)
        # final_layer = self.softmax(linear_output)
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

def train(model, train, val, learning_rate, epochs, batch_size, folds):

    # criterion = nn.CrossEntropyLoss()
    criterion = nn.HingeEmbeddingLoss()
    optimizer = Adam(model.parameters(), lr= learning_rate)

    train_classes = [label for _, label in train_data]
    count = Counter(i.item() for i in train_classes)
    write_and_print(f'Total number of samples in train subset: {len(train_data)}\
      \nNumber of {LABEL1_VALUE} samples: {count[0]}, {count[0]/len(train_classes)*100: .3f}%\
      \nNumber of {LABEL2_VALUE} samples: {count[1]}, {count[1]/len(train_classes)*100: .3f}%\n', LOG_PATH)
    
    if not CROSS_VALIDATION:

        val_classes = [label for _, label in val]
        count = Counter(i.item() for i in val_classes)
        write_and_print(f'Total number of samples in validation subset: {len(val_classes)}\
        \nNumber of {LABEL1_VALUE} samples: {count[0]}, {count[0]/len(val_classes)*100: .3f}%\
        \nNumber of {LABEL2_VALUE} samples: {count[1]}, {count[1]/len(val_classes)*100: .3f}%', LOG_PATH)

        if use_cuda:
            model = model.cuda()
            criterion = criterion.cuda()
        train_dataloader = DataLoader(train, batch_size= batch_size)
        val_dataloader = DataLoader(val, batch_size=batch_size)
        for epoch_num in range(epochs):
            write_and_print(f'------------------------------------------------------------------------------\
            \nStarting Epoch {epoch_num+EPOCH_OFFSET} at: {datetime.datetime.now()}\n', LOG_PATH)
            total_acc_train, total_loss_train = trainer(model, train_dataloader, criterion, optimizer, epoch_num+EPOCH_OFFSET)
            total_acc_val, total_loss_val = validator(model, val_dataloader, criterion, optimizer)
            write_and_print(
                    f'Epoch {epoch_num + EPOCH_OFFSET} Result: | Train Loss: {total_loss_train / len(train_dataloader.sampler): .3f} \
                    | Train Accuracy: {total_acc_train / len(train_dataloader.sampler): .3f} \
                    | Val Loss: {total_loss_val / len(val_dataloader.sampler): .3f} \
                    | Val Accuracy: {total_acc_val / len(val_dataloader.sampler): .3f}', LOG_PATH)
            torch.save(model.state_dict(), SAVE_MODEL_PATH + str(epoch_num+EPOCH_OFFSET) +'.pth')

    else:
        splits=KFold(n_splits=folds,shuffle=True,random_state=42)
        for fold, (train_idx,val_idx) in enumerate(splits.split(np.arange(len(train)))):
            write_and_print(f'\n----------------------------\nFold{fold + 1}\n----------------------------', LOG_PATH)
            train_sampler = SubsetRandomSampler(train_idx)
            test_sampler = SubsetRandomSampler(val_idx)
            train_dataloader = DataLoader(train, batch_size=batch_size, sampler=train_sampler)
            val_dataloader = DataLoader(train, batch_size=batch_size, sampler=test_sampler)

            if use_cuda:
                model = model.cuda()
                criterion = criterion.cuda()

            for epoch_num in range(epochs):
                write_and_print(f'Starting Epoch {epoch_num+1} at: {datetime.datetime.now()}\n', LOG_PATH) 
                total_acc_train, total_loss_train = trainer(model, train_dataloader, criterion, optimizer)
                total_acc_val, total_loss_val = validator(model, val_dataloader, criterion, optimizer)
                            
                write_and_print(
                    f'Epochs {epoch_num + EPOCH_OFFSET} result: Train Loss: {total_loss_train / len(train_dataloader.sampler): .3f} \
                    | Train Accuracy: {total_acc_train / len(train_dataloader.sampler): .3f} \
                    | Val Loss: {total_loss_val / len(val_dataloader.sampler): .3f} \
                    | Val Accuracy: {total_acc_val / len(val_dataloader.sampler): .3f}', LOG_PATH)

def evaluate(model, test):
    test_dataloader = DataLoader(test, batch_size=1)

    y_pred = torch.tensor([])
    y_true = torch.tensor([])

    use_cuda = torch.cuda.is_available()
    device = torch.device("cuda" if use_cuda else "cpu")
    y_pred = y_pred.to(device)
    y_true = y_true.to(device)

    if use_cuda:

        model = model.cuda()

    total_acc_test = 0
    with torch.no_grad():

        for test_input, test_label in tqdm(test_dataloader, desc='Testing the model:'):

            test_label = test_label.to(device)
            mask = test_input['attention_mask'].to(device)
            input_id = test_input['input_ids'].squeeze(1).to(device)

            output = model(input_id, mask)
            y_pred = torch.cat((y_pred,output.argmax(dim=1)),0) # Save Prediction
            y_true = torch.cat((y_true,test_label),0) # Save Truth
            acc = (output.argmax(dim=1) == test_label).sum().item()
            total_acc_test += acc

        write_and_print(f'predicted size, target size: {y_pred.size()},{y_true.size()}', LOG_PATH)
        metric = BinaryStatScores().to(device)
        write_and_print(f'[tp, fp, tn, fn, sup] : {metric(y_pred, y_true)}', LOG_PATH)
    
    write_and_print(f'Test Accuracy: {total_acc_test / len(test): .3f}', LOG_PATH)

model = BertClassifier()
if LOAD_MODEL:
    write_and_print('The model is being loaded from a previously saved checkpoint', LOG_PATH)
    model.load_state_dict(torch.load(LOAD_MODEL_PATH))
else:
    write_and_print('Starting with a fresh model', LOG_PATH)


if LOAD_DATASETS:
    write_and_print('\n\nLoading the Dataset', LOG_PATH)
    train_data = torch.load(LOAD_TRAINSET_PATH)
    test_data = torch.load(LOAD_TESTSET_PATH)
    val = torch.load(LOAD_VALSET_PATH)
else:
    #Create the Dataset instance
    write_and_print('\n\nCreating the Dataset', LOG_PATH)
    data = CongressHearings(train_df)
    #Split the dataset
    train_data, val, test_data = random_split(dataset=data, lengths=SPLIT_LENGTHS)
    torch.save(train_data, LOAD_TRAINSET_PATH)
    torch.save(test_data, LOAD_TESTSET_PATH)
    torch.save(val, LOAD_VALSET_PATH)

if TRAIN:
    write_and_print(f'\n\nBeginning the training at: {datetime.datetime.now()}', LOG_PATH)
    train(model, train_data,val, LR, EPOCHS, batch_size=BATCH_SIZE, folds=NFOLDS)

if TEST:
    write_and_print(f'\n\nBeginning Testing at: {datetime.datetime.now()}', LOG_PATH)
    evaluate(model, test_data)