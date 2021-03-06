from .. import tfdata, preprocess_spotify_features, split_dataset, Path, save_tfdataset, load_tfdataset, save_encoders
from sklearn.preprocessing import MinMaxScaler
from imblearn.under_sampling import RandomUnderSampler
from third_party.scipy.util import print_description
from numpy import array as nparray, unique as npunique
from collections import Counter
from pickle import dump as pkldump, load as pklload

from .fetch import DataFetcher

class DataPreprocessor(DataFetcher):
    
    def __init__(self, h_name, ds_name, source="billboard.json"):
        self.handler_name = h_name
        self.dataset_name = ds_name
        # Path to the sql file for mysql fetch
        self.resource_path = Path(Path.cwd(), "data", "handlers", "billboard", "resources")
        self.resource_path = self.resource_path.joinpath(source)
        
        # Dataset saving path
        self.save_folder = Path(Path.cwd(), "data", "handlers", "billboard", "datasets", ds_name)

        save_name = ds_name+"_dataset.json"

        self.save_path = self.save_folder.joinpath(save_name)
        super()

    def check_unique(self, features):
        uniques, indexes, counts = npunique(features, return_index=True, return_counts=True, axis=0)
        duplicate_indexes = [i for i, dupli in enumerate(features) if i not in indexes]
        #print(len(duplicate_indexes))
        #print(uniques.shape, indexes)
        #print(features.shape)
        return (uniques, duplicate_indexes, indexes)
 
    def balance_ds(self, features, labels):
        #print(list(reversed(Counter(labels).most_common())))
        sampler = RandomUnderSampler()
        return sampler.fit_resample(features, labels)

    def preprocess_features(self, features):
        if not hasattr(self, 'feature_scaler'):
            self.feature_scaler = MinMaxScaler()
            self.feature_scaler.fit(features)
        
        return self.feature_scaler.transform(features)
    
    def preprocess(self, dataset, scale=True, balance=True, new_split=False):
        processed_path = self.save_folder.joinpath('p_data.pkl')
        save_path = self.save_folder.joinpath("processed")
        if not save_path.exists() or new_split:
            
            # Take features and popularities from the sample
            features = []
            labels = []
            for d in dataset:
                # Drop duration feature
                feat = d['features']
                # Take release year from date and add it to the features
                date = d['release_date']
                if '-' in date:
                    split = date.split('-')
                    if len(split) == 3:
                        y, m, da = split
                    elif len(split) == 2:
                        y, m = split
                    else:
                        print("Not possible", date)

                elif len(date) == 4:
                    y = date
                else:
                    print(date)
                    exit()

                # Use only the decade
                y = y[2:]
            
                feat.append(y)
                features.append(feat)

                if 'labels' in d.keys():
                    label = d['labels']
                else:
                    label = 0

                labels.append(int(label))
            
            features = nparray(features, dtype="float32")
            features, duplicate_indexes, selected_indexes = self.check_unique(features)
            # Drop duplicates from labels
            if len(duplicate_indexes) > 1:
                labels = [l for i, l in enumerate(labels) if i in selected_indexes]
        
                duplicate_instances = []
                for i, d in enumerate(dataset):
                    if i in duplicate_indexes:
                        duplicate_instances.append(d)
            else:
                print("No duplicates ", duplicate_indexes)
                #print([d['name'] for d in duplicate_instances])
        
            # Cast to float32
            features = nparray(features, dtype="float32")

            # Description
            #print_description(features)
            #print_description(labels)
            
            # Split dataset
            datasets = split_dataset(features, labels, 0.33, True, 0.15)

            # Store split
            pkldump(datasets, processed_path.open('wb'))

            processed_datasets = []
            if scale:
                # Apply scaling
                for dataset in datasets:
                    # Convert to list for changes
                    processed_datasets.append([self.preprocess_features(dataset[0]), dataset[1]])
            else:
                for dataset in datasets:
                    processed_datasets.append([dataset[0], dataset[1]])

            if balance:
                # Balance out the dataset
                # Done by taking a random sample from each dataset label subset
                # the samples are equal sized = dataset is balanced
                for i, dataset in enumerate(processed_datasets):
                    # Convert to list for changes
                    f, l = self.balance_ds(dataset[0], dataset[1])
                    processed_datasets[i] = [f, l]
        
            datasets = processed_datasets
            # Wrap to tf dataset
            train = tfdata.Dataset.from_tensor_slices((datasets[0][0], datasets[0][1]))
            test = tfdata.Dataset.from_tensor_slices((datasets[2][0], datasets[2][1]))
            validate = tfdata.Dataset.from_tensor_slices((datasets[1][0], datasets[1][1]))
            
            datasets = {
                    "train": train,
                    "validate": validate,
                    "test": test
                    }

            encoder = [{
                    "Input": "All",
                    "Encoder": self.feature_scaler
                    }]
            save_tfdataset(save_path, datasets)
            save_encoders(save_path, encoder)
        else:
            datasets = load_tfdataset(save_path)
            train = datasets['train']
            validate = datasets['validate']
            test = datasets['test']

        return (train, validate, test)
